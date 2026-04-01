"""Workflow-oriented preview/apply helpers for chat and vision driven clients."""

from __future__ import annotations

from collections import defaultdict
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from grocy_mcp.client import GrocyClient
from grocy_mcp.exceptions import GrocyValidationError
from grocy_mcp.workflow_models import (
    WorkflowApplyItem,
    WorkflowMatchPreviewItem,
    WorkflowNormalizedInputItem,
    WorkflowPreviewCandidate,
    WorkflowShoppingReconcileApplyAction,
    WorkflowShoppingReconcilePreviewAction,
    WorkflowShoppingReconcilePreviewItem,
)

T = TypeVar("T", bound=BaseModel)


def _normalize_text(value: str) -> str:
    """Normalize text for exact-match comparisons."""
    return " ".join(value.casefold().split())


def _validation_message(label: str, error: ValidationError) -> str:
    """Convert a Pydantic validation error into a compact user-facing message."""
    details = []
    for item in error.errors(include_url=False):
        loc = ".".join(str(part) for part in item["loc"])
        details.append(f"{loc}: {item['msg']}")
    joined = "; ".join(details)
    return f"Invalid {label}: {joined}"


def _parse_model_list(items: list[dict] | object, model_cls: type[T], label: str) -> list[T]:
    """Validate a JSON array payload into a list of typed models."""
    if not isinstance(items, list):
        raise GrocyValidationError(f"Invalid {label}: expected a JSON array")

    parsed: list[T] = []
    for index, item in enumerate(items):
        try:
            parsed.append(model_cls.model_validate(item))
        except ValidationError as error:
            raise GrocyValidationError(_validation_message(f"{label}[{index}]", error)) from error
    return parsed


def _dedupe_products(products: list[dict]) -> list[dict]:
    """Return unique products by ID while preserving order."""
    seen_ids: set[int] = set()
    unique: list[dict] = []
    for product in products:
        product_id = int(product["id"])
        if product_id in seen_ids:
            continue
        seen_ids.add(product_id)
        unique.append(product)
    return unique


def _candidate_payload(products: list[dict]) -> list[dict]:
    """Return preview candidate payloads for a list of product objects."""
    return [
        WorkflowPreviewCandidate(
            product_id=int(product["id"]), name=product.get("name", "?")
        ).model_dump()
        for product in products
    ]


async def _product_catalog(
    client: GrocyClient,
) -> tuple[list[dict], dict[str, list[dict]], dict[str, list[dict]]]:
    """Load product records plus exact barcode/name indexes."""
    products = await client.get_objects("products")
    product_by_id = {int(product["id"]): product for product in products}

    barcode_map: dict[str, list[dict]] = defaultdict(list)
    for barcode in await client.get_objects("product_barcodes"):
        code = barcode.get("barcode")
        product = product_by_id.get(int(barcode.get("product_id", 0)))
        if code and product is not None:
            barcode_map[code].append(product)

    normalized_name_map: dict[str, list[dict]] = defaultdict(list)
    for product in products:
        normalized_name_map[_normalize_text(product.get("name", ""))].append(product)

    return products, barcode_map, normalized_name_map


async def workflow_match_products_preview_data(
    client: GrocyClient, items: list[dict] | object
) -> list[dict]:
    """Preview product matches for normalized external items."""
    parsed_items = _parse_model_list(items, WorkflowNormalizedInputItem, "items")
    products, barcode_map, normalized_name_map = await _product_catalog(client)

    preview_items: list[dict] = []
    for index, item in enumerate(parsed_items):
        matched_products: list[dict] = []

        if item.barcode:
            matched_products = _dedupe_products(barcode_map.get(item.barcode, []))

        if not matched_products:
            exact_name_matches = _dedupe_products(
                normalized_name_map.get(_normalize_text(item.label), [])
            )
            if exact_name_matches:
                matched_products = exact_name_matches

        if not matched_products:
            substring_matches = [
                product
                for product in products
                if _normalize_text(item.label) in _normalize_text(product.get("name", ""))
            ]
            matched_products = _dedupe_products(substring_matches)

        status = "unmatched"
        matched_product_id: int | None = None
        matched_product_name: str | None = None
        if len(matched_products) == 1:
            status = "matched"
            matched_product_id = int(matched_products[0]["id"])
            matched_product_name = matched_products[0].get("name", "?")
        elif len(matched_products) > 1:
            status = "ambiguous"

        preview_items.append(
            WorkflowMatchPreviewItem(
                input_index=index,
                label=item.label,
                status=status,
                matched_product_id=matched_product_id,
                matched_product_name=matched_product_name,
                candidates=[
                    WorkflowPreviewCandidate(
                        product_id=int(product["id"]), name=product.get("name", "?")
                    )
                    for product in matched_products
                ],
                suggested_amount=item.quantity,
                unit_text=item.unit_text,
            ).model_dump(exclude_none=True)
        )

    return preview_items


async def workflow_match_products_preview(client: GrocyClient, items: list[dict] | object) -> str:
    """Return a human-readable product matching preview."""
    preview_items = await workflow_match_products_preview_data(client, items)
    lines = ["Workflow product match preview:"]
    for item in preview_items:
        amount = item["suggested_amount"]
        unit_suffix = f" {item['unit_text']}" if item.get("unit_text") else ""
        if item["status"] == "matched":
            lines.append(
                f"  [{item['input_index']}] {item['label']}: matched to "
                f"{item['matched_product_name']} (ID {item['matched_product_id']}) - {amount}{unit_suffix}"
            )
        elif item["status"] == "ambiguous":
            candidates = ", ".join(
                f"{candidate['name']} (ID {candidate['product_id']})"
                for candidate in item.get("candidates", [])
            )
            lines.append(f"  [{item['input_index']}] {item['label']}: ambiguous - {candidates}")
        else:
            lines.append(f"  [{item['input_index']}] {item['label']}: unmatched")
    return "\n".join(lines)


async def workflow_stock_intake_preview_data(
    client: GrocyClient, items: list[dict] | object
) -> list[dict]:
    """Return a stock-intake preview using the batch product matching contract."""
    return await workflow_match_products_preview_data(client, items)


async def workflow_stock_intake_preview(client: GrocyClient, items: list[dict] | object) -> str:
    """Return a human-readable stock-intake preview."""
    preview_items = await workflow_stock_intake_preview_data(client, items)
    lines = ["Workflow stock intake preview:"]
    for item in preview_items:
        amount = item["suggested_amount"]
        if item["status"] == "matched":
            lines.append(
                f"  [{item['input_index']}] {item['label']}: add {amount} to "
                f"{item['matched_product_name']} (ID {item['matched_product_id']})"
            )
        elif item["status"] == "ambiguous":
            candidates = ", ".join(
                f"{candidate['name']} (ID {candidate['product_id']})"
                for candidate in item.get("candidates", [])
            )
            lines.append(
                f"  [{item['input_index']}] {item['label']}: confirm product match - {candidates}"
            )
        else:
            lines.append(f"  [{item['input_index']}] {item['label']}: no Grocy product match")
    return "\n".join(lines)


async def workflow_stock_intake_apply_data(client: GrocyClient, items: list[dict] | object) -> dict:
    """Apply confirmed stock additions using explicit product IDs."""
    parsed_items = _parse_model_list(items, WorkflowApplyItem, "items")

    for item in parsed_items:
        await client.add_stock(item.product_id, item.amount)

    return {
        "applied_count": len(parsed_items),
        "applied_items": [item.model_dump(exclude_none=True) for item in parsed_items],
    }


async def workflow_stock_intake_apply(client: GrocyClient, items: list[dict] | object) -> str:
    """Return a human-readable summary for confirmed stock additions."""
    result = await workflow_stock_intake_apply_data(client, items)
    lines = [f"Workflow stock intake applied for {result['applied_count']} item(s)."]
    for item in result["applied_items"]:
        note_suffix = f" ({item['note']})" if item.get("note") else ""
        lines.append(f"  Product ID {item['product_id']}: added {item['amount']}{note_suffix}")
    return "\n".join(lines)


async def workflow_shopping_reconcile_preview_data(
    client: GrocyClient, items: list[dict] | object, list_id: int = 1
) -> list[dict]:
    """Preview shopping-list removals and amount adjustments after a purchase."""
    parsed_items = _parse_model_list(items, WorkflowApplyItem, "items")
    shopping_items = await client.get_shopping_list(list_id)

    state_by_product: dict[int, list[dict]] = defaultdict(list)
    for item in shopping_items:
        product_id = item.get("product_id")
        if product_id is None:
            continue
        state_by_product[int(product_id)].append(
            {
                "shopping_item_id": int(item["id"]),
                "remaining_amount": float(item.get("amount", 0)),
            }
        )

    preview_items: list[dict] = []
    for index, item in enumerate(parsed_items):
        remaining_purchase = item.amount
        actions: list[WorkflowShoppingReconcilePreviewAction] = []
        for state in state_by_product.get(item.product_id, []):
            if remaining_purchase <= 0:
                break
            previous_amount = float(state["remaining_amount"])
            if previous_amount <= 0:
                continue

            if remaining_purchase >= previous_amount:
                actions.append(
                    WorkflowShoppingReconcilePreviewAction(
                        shopping_item_id=state["shopping_item_id"],
                        action="remove",
                        previous_amount=previous_amount,
                    )
                )
                remaining_purchase -= previous_amount
                state["remaining_amount"] = 0
            else:
                new_amount = previous_amount - remaining_purchase
                actions.append(
                    WorkflowShoppingReconcilePreviewAction(
                        shopping_item_id=state["shopping_item_id"],
                        action="set_amount",
                        previous_amount=previous_amount,
                        new_amount=new_amount,
                    )
                )
                state["remaining_amount"] = new_amount
                remaining_purchase = 0

        status = "unmatched"
        if actions and remaining_purchase == 0:
            status = "matched"
        elif actions:
            status = "partial"

        preview_items.append(
            WorkflowShoppingReconcilePreviewItem(
                input_index=index,
                product_id=item.product_id,
                purchased_amount=item.amount,
                status=status,
                actions=actions,
                unapplied_amount=remaining_purchase,
            ).model_dump(exclude_none=True)
        )

    return preview_items


async def workflow_shopping_reconcile_preview(
    client: GrocyClient, items: list[dict] | object, list_id: int = 1
) -> str:
    """Return a human-readable shopping reconciliation preview."""
    preview_items = await workflow_shopping_reconcile_preview_data(client, items, list_id)
    lines = [f"Workflow shopping reconcile preview for list #{list_id}:"]
    for item in preview_items:
        if item["status"] == "unmatched":
            lines.append(
                f"  [{item['input_index']}] Product ID {item['product_id']}: no shopping-list match"
            )
            continue

        status_suffix = (
            f" (unapplied amount {item['unapplied_amount']})" if item["unapplied_amount"] else ""
        )
        lines.append(
            f"  [{item['input_index']}] Product ID {item['product_id']}: {item['status']}{status_suffix}"
        )
        for action in item["actions"]:
            if action["action"] == "remove":
                lines.append(f"    - remove shopping item {action['shopping_item_id']}")
            else:
                lines.append(
                    f"    - set shopping item {action['shopping_item_id']} amount to {action['new_amount']}"
                )
    return "\n".join(lines)


async def workflow_shopping_reconcile_apply_data(
    client: GrocyClient, actions: list[dict] | object
) -> dict:
    """Apply explicit shopping-list reconciliation actions."""
    parsed_actions = _parse_model_list(actions, WorkflowShoppingReconcileApplyAction, "actions")

    for action in parsed_actions:
        if action.action == "remove":
            await client.remove_shopping_list_item(action.shopping_item_id)
        else:
            await client.update_shopping_list_item(
                action.shopping_item_id, {"amount": action.new_amount}
            )

    return {
        "applied_count": len(parsed_actions),
        "applied_actions": [action.model_dump(exclude_none=True) for action in parsed_actions],
    }


async def workflow_shopping_reconcile_apply(
    client: GrocyClient, actions: list[dict] | object
) -> str:
    """Return a human-readable shopping reconciliation apply summary."""
    result = await workflow_shopping_reconcile_apply_data(client, actions)
    lines = [f"Workflow shopping reconciliation applied for {result['applied_count']} action(s)."]
    for action in result["applied_actions"]:
        if action["action"] == "remove":
            lines.append(f"  Shopping item {action['shopping_item_id']}: removed")
        else:
            lines.append(
                f"  Shopping item {action['shopping_item_id']}: amount set to {action['new_amount']}"
            )
    return "\n".join(lines)
