"""First-class metadata and discovery helpers built on top of Grocy entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from grocy_mcp.client import GrocyClient
from grocy_mcp.exceptions import GrocyValidationError

EXPOSED_ENTITIES = {
    "products",
    "chores",
    "product_barcodes",
    "batteries",
    "locations",
    "quantity_units",
    "quantity_unit_conversions",
    "shopping_list",
    "shopping_lists",
    "shopping_locations",
    "recipes",
    "recipes_pos",
    "recipes_nestings",
    "tasks",
    "task_categories",
    "product_groups",
    "equipment",
    "userfields",
    "userentities",
    "userobjects",
    "meal_plan",
    "stock_log",
    "stock",
    "stock_current_locations",
    "chores_log",
    "meal_plan_sections",
    "products_last_purchased",
    "products_average_price",
    "quantity_unit_conversions_resolved",
    "recipes_pos_resolved",
    "battery_charge_cycles",
    "product_barcodes_view",
    "permission_hierarchy",
}

READ_ONLY_ENTITIES = {
    "stock_log",
    "stock",
    "stock_current_locations",
    "chores_log",
    "products_last_purchased",
    "products_average_price",
    "quantity_unit_conversions_resolved",
    "recipes_pos_resolved",
    "battery_charge_cycles",
    "product_barcodes_view",
    "permission_hierarchy",
}

NON_DELETABLE_ENTITIES = {
    "stock_log",
    "stock",
    "stock_current_locations",
    "chores_log",
    "products_last_purchased",
    "products_average_price",
    "quantity_unit_conversions_resolved",
    "recipes_pos_resolved",
    "battery_charge_cycles",
    "product_barcodes_view",
    "permission_hierarchy",
}


@dataclass(frozen=True)
class EntitySpec:
    entity: str
    title: str
    singular: str
    name_fields: tuple[str, ...] = ("name",)
    summary_fields: tuple[str, ...] = ()
    description: str = ""
    read_only: bool = False


ENTITY_SPECS: dict[str, EntitySpec] = {
    "products": EntitySpec(
        entity="products",
        title="Products",
        singular="product",
        summary_fields=("description", "location_id"),
        description="Grocy stock products.",
    ),
    "recipes": EntitySpec(
        entity="recipes",
        title="Recipes",
        singular="recipe",
        summary_fields=("description",),
        description="Grocy recipes.",
    ),
    "chores": EntitySpec(
        entity="chores",
        title="Chores",
        singular="chore",
        summary_fields=("description", "period_type", "period_days"),
        description="Grocy chores.",
    ),
    "locations": EntitySpec(
        entity="locations",
        title="Locations",
        singular="location",
        summary_fields=("description", "is_freezer"),
        description="Grocy stock locations.",
    ),
    "tasks": EntitySpec(
        entity="tasks",
        title="Tasks",
        singular="task",
        summary_fields=("due_date", "category_id", "assigned_to_user_id"),
        description="Grocy task items.",
    ),
    "shopping_lists": EntitySpec(
        entity="shopping_lists",
        title="Shopping lists",
        singular="shopping list",
        summary_fields=("description",),
        description="Named Grocy shopping lists.",
    ),
    "shopping_locations": EntitySpec(
        entity="shopping_locations",
        title="Shopping locations",
        singular="shopping location",
        summary_fields=("description",),
        description="Stores or places where items are purchased.",
    ),
    "quantity_units": EntitySpec(
        entity="quantity_units",
        title="Quantity units",
        singular="quantity unit",
        summary_fields=("name_plural", "description"),
        description="Units used for stock, recipes, and shopping amounts.",
    ),
    "quantity_unit_conversions": EntitySpec(
        entity="quantity_unit_conversions",
        title="Quantity unit conversions",
        singular="quantity unit conversion",
        name_fields=("from_qu_id", "to_qu_id"),
        summary_fields=("factor", "product_id"),
        description="Raw conversion rules between quantity units.",
    ),
    "product_groups": EntitySpec(
        entity="product_groups",
        title="Product groups",
        singular="product group",
        summary_fields=("description",),
        description="High-level product grouping metadata.",
    ),
    "task_categories": EntitySpec(
        entity="task_categories",
        title="Task categories",
        singular="task category",
        summary_fields=("description",),
        description="Categories used to organize tasks.",
    ),
    "meal_plan_sections": EntitySpec(
        entity="meal_plan_sections",
        title="Meal plan sections",
        singular="meal plan section",
        summary_fields=("sort_number",),
        description="Sections used to group meal-plan entries.",
    ),
    "equipment": EntitySpec(
        entity="equipment",
        title="Equipment",
        singular="equipment item",
        summary_fields=("description", "location_id", "battery_id"),
        description="Household equipment and appliances tracked in Grocy.",
    ),
    "products_last_purchased": EntitySpec(
        entity="products_last_purchased",
        title="Products last purchased",
        singular="product purchase snapshot",
        name_fields=("product_name", "name"),
        summary_fields=("product_id", "last_purchased", "price"),
        description="Read-only view of the last-purchased timestamps and prices.",
        read_only=True,
    ),
    "products_average_price": EntitySpec(
        entity="products_average_price",
        title="Products average price",
        singular="product average price row",
        name_fields=("product_name", "name"),
        summary_fields=("product_id", "avg_price", "amount"),
        description="Read-only view of product average pricing.",
        read_only=True,
    ),
}


def _require_entity(entity: str) -> EntitySpec:
    if entity not in ENTITY_SPECS:
        raise GrocyValidationError(f"Unsupported entity helper '{entity}'.")
    return ENTITY_SPECS[entity]


def _normalize_query(value: str) -> str:
    return " ".join(value.casefold().split())


def _display_name(item: dict[str, Any], spec: EntitySpec) -> str:
    for field in spec.name_fields:
        value = item.get(field)
        if value not in (None, ""):
            return str(value)

    for field in ("name", "product_name", "recipe_name", "chore_name", "description", "used_in"):
        value = item.get(field)
        if value not in (None, ""):
            return str(value)

    if "id" in item:
        return f"{spec.singular.title()} {item['id']}"
    return str(item)


def _summary_parts(item: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    parts: list[str] = []
    for field in fields:
        value = item.get(field)
        if value not in (None, "", []):
            parts.append(f"{field}={value}")
    return parts


def _row_matches(item: dict[str, Any], query: str) -> bool:
    normalized_query = _normalize_query(query)
    for value in item.values():
        if isinstance(value, dict):
            if _row_matches(value, query):
                return True
            continue
        if isinstance(value, list):
            if any(
                _row_matches(v, query)
                if isinstance(v, dict)
                else normalized_query in _normalize_query(str(v))
                for v in value
            ):
                return True
            continue
        if value is not None and normalized_query in _normalize_query(str(value)):
            return True
    return False


def _format_details(item: dict[str, Any]) -> str:
    ordered_fields = ["id", "name", "description"]
    seen = set(ordered_fields)
    lines: list[str] = []
    for field in ordered_fields + [field for field in item if field not in seen]:
        if field not in item:
            continue
        value = item[field]
        if value in (None, "", [], {}):
            continue
        lines.append(f"  {field}: {value}")
    return "\n".join(lines)


async def list_entity_records(
    client: GrocyClient,
    entity: str,
    query: str | None = None,
) -> list[dict]:
    _require_entity(entity)
    items = await client.get_objects(entity)
    if query:
        items = [item for item in items if _row_matches(item, query)]
    return items


async def list_entity_view(client: GrocyClient, entity: str, query: str | None = None) -> str:
    spec = _require_entity(entity)
    items = await list_entity_records(client, entity, query)
    if not items:
        suffix = f" matching '{query}'" if query else ""
        return f"No {spec.title.lower()}{suffix} found."

    lines = [f"{spec.title} ({len(items)} item(s)):"]
    for item in items:
        name = _display_name(item, spec)
        parts = _summary_parts(item, spec.summary_fields)
        suffix = f" — {', '.join(parts)}" if parts else ""
        lines.append(f"  [{item.get('id', '?')}] {name}{suffix}")
    return "\n".join(lines)


async def entity_details_view(client: GrocyClient, entity: str, obj_id: int) -> str:
    spec = _require_entity(entity)
    item = await client.get_object(entity, obj_id)
    return f"{spec.singular.title()} details:\n{_format_details(item)}"


async def entity_create_view(client: GrocyClient, entity: str, data: dict) -> str:
    spec = _require_entity(entity)
    if spec.read_only or entity in READ_ONLY_ENTITIES:
        raise GrocyValidationError(f"{spec.title} are read-only and cannot be created.")
    created_id = await client.create_object(entity, data)
    return f"Created {spec.singular} with ID {created_id}."


async def entity_update_view(client: GrocyClient, entity: str, obj_id: int, data: dict) -> str:
    spec = _require_entity(entity)
    if spec.read_only or entity in READ_ONLY_ENTITIES:
        raise GrocyValidationError(f"{spec.title} are read-only and cannot be updated.")
    await client.update_object(entity, obj_id, data)
    return f"Updated {spec.singular} {obj_id}."


async def search_entity_candidates_data(
    client: GrocyClient,
    entity: str,
    query: str,
    limit: int = 10,
) -> list[dict]:
    spec = _require_entity(entity)
    items = await list_entity_records(client, entity, query)
    candidates = []
    for item in items[:limit]:
        candidates.append(
            {
                "id": item.get("id"),
                "label": _display_name(item, spec),
                "summary": _summary_parts(item, spec.summary_fields),
            }
        )
    return candidates


async def search_entity_candidates(
    client: GrocyClient, entity: str, query: str, limit: int = 10
) -> str:
    spec = _require_entity(entity)
    candidates = await search_entity_candidates_data(client, entity, query, limit)
    if not candidates:
        return f"No {spec.title.lower()} found matching '{query}'."
    lines = [f"{spec.title} matching '{query}':"]
    for candidate in candidates:
        suffix = f" — {', '.join(candidate['summary'])}" if candidate["summary"] else ""
        lines.append(f"  [{candidate['id']}] {candidate['label']}{suffix}")
    return "\n".join(lines)


async def describe_entity_data(client: GrocyClient, entity: str) -> dict:
    if entity not in EXPOSED_ENTITIES:
        raise GrocyValidationError(f"Unknown Grocy entity '{entity}'.")

    sample_items = await client.get_objects(entity)
    sample_fields: list[str] = []
    for item in sample_items[:10]:
        for key in item.keys():
            if key not in sample_fields:
                sample_fields.append(key)

    spec = ENTITY_SPECS.get(entity)
    return {
        "entity": entity,
        "title": spec.title if spec else entity.replace("_", " ").title(),
        "description": spec.description if spec else "Generic Grocy entity.",
        "supports_create": entity not in READ_ONLY_ENTITIES,
        "supports_update": entity not in READ_ONLY_ENTITIES,
        "supports_delete": entity not in NON_DELETABLE_ENTITIES,
        "sample_fields": sample_fields,
        "preferred_name_fields": list(spec.name_fields) if spec else ["name"],
    }


async def describe_entity(client: GrocyClient, entity: str) -> str:
    data = await describe_entity_data(client, entity)
    lines = [f"Entity: {data['entity']}"]
    lines.append(f"  Title: {data['title']}")
    lines.append(f"  Description: {data['description']}")
    lines.append(
        "  Operations: "
        f"create={data['supports_create']}, update={data['supports_update']}, delete={data['supports_delete']}"
    )
    fields = ", ".join(data["sample_fields"]) if data["sample_fields"] else "none discovered"
    lines.append(f"  Sample fields: {fields}")
    return "\n".join(lines)


async def discover_entity_fields_data(client: GrocyClient, entity: str) -> dict:
    data = await describe_entity_data(client, entity)
    return {
        "entity": entity,
        "fields": data["sample_fields"],
        "preferred_name_fields": data["preferred_name_fields"],
    }


async def discover_entity_fields(client: GrocyClient, entity: str) -> str:
    data = await discover_entity_fields_data(client, entity)
    field_list = ", ".join(data["fields"]) if data["fields"] else "none discovered"
    preferred = ", ".join(data["preferred_name_fields"])
    return f"Fields for {entity}: {field_list}\nPreferred label fields: {preferred}"
