"""State capture and assertion helpers for Grocy-backed testbed runs."""

from __future__ import annotations

from collections import defaultdict

from grocy_mcp.client import GrocyClient
from testbed.models import ExpectedOutcome


async def capture_state(client: GrocyClient, shopping_list_names: list[str] | None = None) -> dict:
    products = await client.get_objects("products")
    product_names = {
        int(item["id"]): item.get("name", f"Product {item['id']}") for item in products
    }

    shopping_lists = await client.get_objects("shopping_lists")
    list_names = {
        int(item["id"]): item.get("name", f"List {item['id']}") for item in shopping_lists
    }
    if shopping_list_names is not None:
        requested_names = {name.casefold() for name in shopping_list_names}
        list_names = {
            list_id: name
            for list_id, name in list_names.items()
            if name.casefold() in requested_names
        }

    stock_rows = await client.get_stock()
    stock_by_name: dict[str, float] = defaultdict(float)
    for row in stock_rows:
        product_id = row.get("product_id")
        if product_id is None:
            continue
        stock_by_name[product_names.get(int(product_id), str(product_id))] += float(
            row.get("amount", 0)
        )

    shopping_snapshot: dict[str, dict[str, float]] = {}
    for list_id, list_name in list_names.items():
        items = await client.get_shopping_list(list_id)
        totals: dict[str, float] = defaultdict(float)
        for item in items:
            product_id = item.get("product_id")
            if product_id is None:
                continue
            totals[product_names.get(int(product_id), str(product_id))] += float(
                item.get("amount", 0)
            )
        shopping_snapshot[list_name] = dict(sorted(totals.items()))

    return {
        "stock": dict(sorted(stock_by_name.items())),
        "shopping_lists": shopping_snapshot,
    }


def compare_states(before: dict, after: dict) -> dict[str, bool]:
    return {
        "stock_changed": before.get("stock") != after.get("stock"),
        "shopping_changed": before.get("shopping_lists") != after.get("shopping_lists"),
    }


def assert_expected_outcome(
    before: dict,
    after: dict,
    expected: ExpectedOutcome,
) -> list[dict]:
    assertions: list[dict] = []

    actual_mutations = compare_states(before, after)
    for field, expected_value in expected.mutations.model_dump().items():
        actual_value = actual_mutations[field]
        assertions.append(
            {
                "name": f"mutation:{field}",
                "passed": actual_value == expected_value,
                "expected": expected_value,
                "actual": actual_value,
            }
        )

    stock_snapshot = after.get("stock", {})
    for item in expected.stock:
        actual_amount = float(stock_snapshot.get(item.product, 0))
        assertions.append(
            {
                "name": f"stock:{item.product}",
                "passed": actual_amount == float(item.amount),
                "expected": item.amount,
                "actual": actual_amount,
            }
        )

    shopping_snapshot = after.get("shopping_lists", {})
    for shopping_list in expected.shopping_lists:
        list_snapshot = shopping_snapshot.get(shopping_list.list_name, {})
        for item in shopping_list.items:
            actual_amount = float(list_snapshot.get(item.product, 0))
            assertions.append(
                {
                    "name": f"shopping:{shopping_list.list_name}:{item.product}",
                    "passed": actual_amount == float(item.amount),
                    "expected": item.amount,
                    "actual": actual_amount,
                }
            )
        for product_name in shopping_list.absent:
            assertions.append(
                {
                    "name": f"shopping_absent:{shopping_list.list_name}:{product_name}",
                    "passed": product_name not in list_snapshot,
                    "expected": "absent",
                    "actual": list_snapshot.get(product_name),
                }
            )

    return assertions
