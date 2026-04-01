"""Core location management functions for Grocy."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient


async def locations_list(client: GrocyClient) -> str:
    """Return a formatted list of all storage locations."""
    locations = await client.get_objects("locations")
    if not locations:
        return "No locations found."

    lines = ["Locations:"]
    for loc in locations:
        freezer = " (freezer)" if loc.get("is_freezer") else ""
        desc = loc.get("description", "")
        desc_str = f" — {desc}" if desc else ""
        lines.append(f"  [{loc['id']}] {loc.get('name', '?')}{freezer}{desc_str}")

    return "\n".join(lines)


async def location_create(
    client: GrocyClient,
    name: str,
    is_freezer: bool = False,
    description: str = "",
) -> str:
    """Create a new storage location."""
    data: dict = {"name": name}
    if is_freezer:
        data["is_freezer"] = 1
    if description:
        data["description"] = description

    loc_id = await client.create_object("locations", data)
    return f"Location '{name}' created (ID {loc_id})."
