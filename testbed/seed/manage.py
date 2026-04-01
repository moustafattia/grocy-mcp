"""Demo Grocy environment management for the testbed suite."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import httpx

from testbed.config import TestbedConfig
from testbed.seed.session import GrocySessionClient
from testbed.utils import ensure_dir, read_json

OPTIONAL_GROUPS = {
    "shopping_locations",
    "task_categories",
    "meal_plan_sections",
    "tasks",
    "chores",
    "batteries",
    "equipment",
    "meal_plan",
}


def docker_available() -> bool:
    return shutil.which("docker") is not None


def _compose_command(config: TestbedConfig, *args: str) -> list[str]:
    return ["docker", "compose", "-f", str(config.testbed_dir / "compose.yaml"), *args]


def reset_runtime_dirs(config: TestbedConfig) -> None:
    for child in ("grocy-data", "reports", "logs"):
        path = config.runtime_dir / child
        if path.exists():
            shutil.rmtree(path)
    ensure_dir(config.runtime_dir)


def compose_down(config: TestbedConfig) -> None:
    if not docker_available():
        raise RuntimeError("Docker is required to manage the demo Grocy testbed.")
    subprocess.run(
        _compose_command(config, "down", "--remove-orphans"),
        cwd=config.root_dir,
        check=False,
        capture_output=True,
        text=True,
    )


def compose_up(config: TestbedConfig) -> None:
    if not docker_available():
        raise RuntimeError("Docker is required to manage the demo Grocy testbed.")
    subprocess.run(
        _compose_command(config, "up", "-d"),
        cwd=config.root_dir,
        check=True,
        capture_output=True,
        text=True,
    )


def wait_for_grocy(base_url: str, timeout: int = 120) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(base_url, follow_redirects=False, timeout=10.0)
            if response.status_code in {200, 302, 303}:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(2)
    raise RuntimeError(f"Grocy demo instance did not become ready: {last_error}")


def _create_named_entities(
    session: GrocySessionClient,
    group_name: str,
    entity: str,
    items: list[dict],
) -> tuple[dict[str, int], list[str]]:
    ids: dict[str, int] = {}
    warnings: list[str] = []
    for item in items:
        payload = {key: value for key, value in item.items() if key != "name"}
        name = str(item["name"])
        try:
            ids[name] = session.create_object(entity, {"name": name, **payload})
        except Exception as exc:  # pragma: no cover - depends on live Grocy validation
            if group_name in OPTIONAL_GROUPS:
                warnings.append(f"{group_name}:{name}: {exc}")
            else:
                raise
    return ids, warnings


def bootstrap_demo_household(config: TestbedConfig, seed_profile_path: Path) -> list[str]:
    profile = read_json(seed_profile_path)
    warnings: list[str] = []

    session = GrocySessionClient(
        config.grocy_base_url,
        config.admin_username,
        config.admin_password,
    )
    session.login()

    try:
        ids: dict[str, dict[str, int]] = {}

        for group_name, entity in (
            ("quantity_units", "quantity_units"),
            ("locations", "locations"),
            ("shopping_lists", "shopping_lists"),
            ("shopping_locations", "shopping_locations"),
            ("task_categories", "task_categories"),
            ("meal_plan_sections", "meal_plan_sections"),
            ("batteries", "batteries"),
        ):
            items = profile.get(group_name, [])
            created, group_warnings = _create_named_entities(session, group_name, entity, items)
            ids[group_name] = created
            warnings.extend(group_warnings)

        ids["products"] = {}
        for item in profile.get("products", []):
            payload = {
                "name": item["name"],
                "description": item.get("description", ""),
                "location_id": ids["locations"][item["location"]],
                "qu_id_purchase": ids["quantity_units"][item["purchase_unit"]],
                "qu_id_stock": ids["quantity_units"][item["stock_unit"]],
            }
            if "min_stock_amount" in item:
                payload["min_stock_amount"] = item["min_stock_amount"]
            product_id = session.create_object("products", payload)
            ids["products"][item["name"]] = product_id
            for barcode in item.get("barcodes", []):
                barcode_payload = {"product_id": product_id, "barcode": barcode}
                shopping_location = item.get("shopping_location")
                if shopping_location:
                    barcode_payload["shopping_location_id"] = ids["shopping_locations"][
                        shopping_location
                    ]
                session.create_object("product_barcodes", barcode_payload)
            stock_amount = float(item.get("stock_amount", 0))
            if stock_amount > 0:
                session.add_stock(product_id, stock_amount)

        ids["recipes"] = {}
        for item in profile.get("recipes", []):
            recipe_id = session.create_object(
                "recipes",
                {"name": item["name"], "description": item.get("description", "")},
            )
            ids["recipes"][item["name"]] = recipe_id
            for ingredient in item.get("ingredients", []):
                session.create_object(
                    "recipes_pos",
                    {
                        "recipe_id": recipe_id,
                        "product_id": ids["products"][ingredient["product"]],
                        "amount": ingredient["amount"],
                    },
                )

        for item in profile.get("shopping_items", []):
            session.create_object(
                "shopping_list",
                {
                    "shopping_list_id": ids["shopping_lists"][item["list"]],
                    "product_id": ids["products"][item["product"]],
                    "amount": item.get("amount", 1),
                    "note": item.get("note", ""),
                },
            )

        for item in profile.get("tasks", []):
            payload = {"name": item["name"], "description": item.get("description", "")}
            category = item.get("category")
            if category:
                payload["category_id"] = ids["task_categories"][category]
            try:
                session.create_object("tasks", payload)
            except Exception as exc:  # pragma: no cover - live Grocy validation
                warnings.append(f"tasks:{item['name']}: {exc}")

        for item in profile.get("chores", []):
            payload = {
                "name": item["name"],
                "description": item.get("description", ""),
                "period_type": item.get("period_type", "weekly"),
                "period_days": item.get("period_days", 7),
            }
            try:
                session.create_object("chores", payload)
            except Exception as exc:  # pragma: no cover - live Grocy validation
                warnings.append(f"chores:{item['name']}: {exc}")

        ids["equipment"] = {}
        for item in profile.get("equipment", []):
            payload = {"name": item["name"], "description": item.get("description", "")}
            battery = item.get("battery")
            if battery:
                payload["battery_id"] = ids["batteries"][battery]
            location = item.get("location")
            if location:
                payload["location_id"] = ids["locations"][location]
            try:
                ids["equipment"][item["name"]] = session.create_object("equipment", payload)
            except Exception as exc:  # pragma: no cover - live Grocy validation
                warnings.append(f"equipment:{item['name']}: {exc}")

        for item in profile.get("meal_plan", []):
            payload = {
                "day": item["day"],
                "type": item.get("type", "recipe"),
                "note": item.get("note", ""),
            }
            recipe = item.get("recipe")
            if recipe:
                payload["recipe_id"] = ids["recipes"][recipe]
            section = item.get("section")
            if section:
                payload["meal_plan_section_id"] = ids["meal_plan_sections"][section]
            try:
                session.create_object("meal_plan", payload)
            except Exception as exc:  # pragma: no cover - live Grocy validation
                warnings.append(f"meal_plan:{item.get('day', '?')}: {exc}")

        return warnings
    finally:
        session.close()


def ensure_demo_environment(config: TestbedConfig, seed_profile_path: Path) -> list[str]:
    compose_down(config)
    reset_runtime_dirs(config)
    compose_up(config)
    wait_for_grocy(config.grocy_base_url)
    return bootstrap_demo_household(config, seed_profile_path)
