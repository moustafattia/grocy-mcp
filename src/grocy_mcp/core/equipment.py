"""First-class equipment helpers for Grocy."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.reference_data import _format_details
from grocy_mcp.core.resolve import resolve_entity
from grocy_mcp.exceptions import GrocyError


def _equipment_battery_id(item: dict) -> int | None:
    for field in ("battery_id", "related_battery_id", "equipment_battery_id"):
        value = item.get(field)
        if value:
            return int(value)
    return None


async def equipment_list(client: GrocyClient) -> str:
    """Return a formatted list of equipment items."""
    items = await equipment_list_data(client)
    if not items:
        return "No equipment found."

    lines = [f"Equipment ({len(items)} item(s)):"]
    for item in items:
        parts = []
        if item.get("description"):
            parts.append(item["description"])
        if item.get("linked_battery_name"):
            parts.append(f"battery={item['linked_battery_name']}")
        suffix = f" — {', '.join(parts)}" if parts else ""
        lines.append(f"  [{item.get('id', '?')}] {item.get('name', '?')}{suffix}")
    return "\n".join(lines)


async def equipment_list_data(client: GrocyClient) -> list[dict]:
    """Return equipment items enriched with linked battery names."""
    items = await client.get_objects("equipment")
    batteries = await client.get_objects("batteries")
    battery_map = {
        battery["id"]: battery.get("name", f"Battery {battery['id']}") for battery in batteries
    }

    rows = []
    for item in items:
        battery_id = _equipment_battery_id(item)
        rows.append(
            {
                **item,
                "linked_battery_name": battery_map.get(battery_id)
                if battery_id is not None
                else None,
            }
        )
    return rows


async def equipment_details(client: GrocyClient, equipment: str) -> str:
    """Return detailed equipment information."""
    item = await equipment_details_data(client, equipment)
    lines = [f"Equipment details for '{item.get('name', equipment)}':", _format_details(item)]
    return "\n".join(lines)


async def equipment_details_data(client: GrocyClient, equipment: str) -> dict:
    """Return detailed equipment information as structured data."""
    equipment_id = await resolve_entity(client, "equipment", equipment)
    item = await client.get_object("equipment", equipment_id)
    battery_id = _equipment_battery_id(item)
    if battery_id is not None:
        try:
            battery = await client.get_object("batteries", battery_id)
            item["linked_battery_name"] = battery.get("name", battery_id)
        except GrocyError:
            item["linked_battery_id"] = battery_id
    return item


async def equipment_create(
    client: GrocyClient,
    name: str,
    description: str = "",
    battery_id: int | None = None,
) -> str:
    """Create an equipment item."""
    data: dict[str, object] = {"name": name}
    if description:
        data["description"] = description
    if battery_id is not None:
        data["battery_id"] = battery_id
    equipment_id = await client.create_object("equipment", data)
    return f"Equipment '{name}' created (ID {equipment_id})."


async def equipment_update(
    client: GrocyClient,
    equipment: str,
    name: str | None = None,
    description: str | None = None,
    battery_id: int | None = None,
) -> str:
    """Update an equipment item."""
    equipment_id = await resolve_entity(client, "equipment", equipment)
    data: dict[str, object] = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if battery_id is not None:
        data["battery_id"] = battery_id
    await client.update_object("equipment", equipment_id, data)
    return f"Equipment '{equipment}' updated."
