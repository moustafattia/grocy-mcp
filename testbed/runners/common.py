"""Shared runner helpers for CLI, MCP, and suite orchestration."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

from grocy_mcp.workflow_models import WorkflowNormalizedInputItem
from testbed.adapters import create_adapter
from testbed.config import TestbedConfig
from testbed.loaders import load_confirmation, load_expected_outcome, load_manifest
from testbed.models import ExpectedOutcome, ScenarioConfirmation, ScenarioManifest
from testbed.utils import read_json, read_text


PROMPT_FILES = {
    "receipt_stock": "receipt_stock.txt",
    "pantry_audit": "pantry_audit.txt",
    "recipe_url_shopping": "recipe_url_shopping.txt",
}


def manifest_path(config: TestbedConfig, scenario_id: str) -> Path:
    return config.scenarios_dir / f"{scenario_id}.json"


def _resolve_path(config: TestbedConfig, path: Path) -> Path:
    return path if path.is_absolute() else config.testbed_dir / path


def load_scenario_bundle(
    config: TestbedConfig, scenario_id: str
) -> tuple[ScenarioManifest, ScenarioConfirmation, ExpectedOutcome]:
    """Load and resolve the manifest, confirmation, and expected outcome for a scenario."""
    manifest = load_manifest(manifest_path(config, scenario_id))
    manifest = manifest.model_copy(
        update={
            "seed_profile": _resolve_path(config, manifest.seed_profile),
            "input_asset": _resolve_path(config, manifest.input_asset),
            "golden_items_path": _resolve_path(config, manifest.golden_items_path),
            "confirmation_path": _resolve_path(config, manifest.confirmation_path),
            "expected_outcome_path": _resolve_path(config, manifest.expected_outcome_path),
        }
    )
    confirmation = load_confirmation(manifest.confirmation_path)
    expected = load_expected_outcome(manifest.expected_outcome_path)
    return manifest, confirmation, expected


def load_prompt_template(config: TestbedConfig, task_type: str) -> str:
    return read_text(config.prompts_dir / PROMPT_FILES[task_type])


def load_normalized_items(
    manifest: ScenarioManifest,
    config: TestbedConfig,
    source: str,
    provider_model: str | None = None,
) -> list[dict]:
    """Load normalized input items from golden fixtures or a provider adapter."""
    if source == "golden":
        payload = read_json(manifest.golden_items_path)
    else:
        adapter = create_adapter(source, config, provider_model)
        payload = adapter.extract(
            manifest.task_type,
            manifest.input_asset,
            manifest.source_metadata,
            load_prompt_template(config, manifest.task_type),
        )
    validated: list[dict] = []
    for item in payload:
        model = WorkflowNormalizedInputItem.model_validate(item)
        validated.append(model.model_dump(exclude_none=True))
    return validated


def product_resolution_map(confirmation: ScenarioConfirmation) -> dict[int, str]:
    return {item.input_index: item.product for item in confirmation.product_resolutions}


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def build_stock_apply_items(
    preview_output: list[dict],
    normalized_items: list[dict],
    confirmation: ScenarioConfirmation,
    products_by_name: dict[str, int],
) -> tuple[list[dict], list[dict]]:
    """Build apply-ready stock items and confirmation actions from a match preview."""
    resolutions = product_resolution_map(confirmation)
    apply_items: list[dict] = []
    confirmation_actions: list[dict] = []
    for preview_item in preview_output:
        index = int(preview_item["input_index"])
        normalized_item = normalized_items[index]
        status = preview_item["status"]
        if status == "matched":
            product_id = int(preview_item["matched_product_id"])
            confirmation_actions.append(
                {
                    "input_index": index,
                    "action": "use_matched",
                    "product_id": product_id,
                    "label": normalized_item["label"],
                }
            )
        else:
            if index not in resolutions:
                raise RuntimeError(
                    f"Scenario requires explicit confirmation for unresolved item index {index}."
                )
            product_name = resolutions[index]
            normalized_name = _normalize_name(product_name)
            if normalized_name not in products_by_name:
                raise RuntimeError(
                    f"Unknown confirmed product '{product_name}' for item index {index}."
                )
            product_id = products_by_name[normalized_name]
            confirmation_actions.append(
                {
                    "input_index": index,
                    "action": "resolve_override",
                    "product": product_name,
                    "product_id": product_id,
                    "label": normalized_item["label"],
                }
            )
        item = {"product_id": product_id, "amount": normalized_item["quantity"]}
        if normalized_item.get("note"):
            item["note"] = normalized_item["note"]
        apply_items.append(item)
    return apply_items, confirmation_actions


def flatten_shopping_actions(preview_output: list[dict]) -> list[dict]:
    """Flatten per-item shopping reconcile actions into a single list."""
    actions: list[dict] = []
    for item in preview_output:
        for action in item.get("actions", []):
            payload = {
                "shopping_item_id": action["shopping_item_id"],
                "action": action["action"],
            }
            if "new_amount" in action:
                payload["new_amount"] = action["new_amount"]
            actions.append(payload)
    return actions


@contextlib.contextmanager
def temporary_env(updates: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in updates}
    os.environ.update(updates)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_cli_json(config: TestbedConfig, args: list[str]) -> dict | list:
    env = {
        **os.environ,
        "GROCY_URL": config.proxy_url,
        "GROCY_API_KEY": config.proxy_api_key,
    }
    result = subprocess.run(
        [config.cli_bin, "--json", *args],
        cwd=config.root_dir,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(result.stdout)


def run_cli_text(config: TestbedConfig, args: list[str]) -> str:
    env = {
        **os.environ,
        "GROCY_URL": config.proxy_url,
        "GROCY_API_KEY": config.proxy_api_key,
    }
    result = subprocess.run(
        [config.cli_bin, *args],
        cwd=config.root_dir,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def source_ready(source: str, config: TestbedConfig) -> bool:
    if source == "golden":
        return True
    if source == "openai":
        return bool(config.openai_api_key and config.openai_model)
    if source == "anthropic":
        return bool(config.anthropic_api_key and config.anthropic_model)
    if source == "openai_compatible":
        return bool(config.openai_compatible_base_url and config.openai_compatible_model)
    return False
