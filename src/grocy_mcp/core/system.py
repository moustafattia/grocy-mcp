"""Core system information and generic entity management for Grocy."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient


async def system_info(client: GrocyClient) -> str:
    """Return Grocy system information."""
    info = await client.get_system_info()
    grocy_version = info.get("grocy_version", {})
    version = grocy_version.get("Version", "unknown") if isinstance(grocy_version, dict) else str(grocy_version)
    php_version = info.get("php_version", "unknown")
    sqlite_version = info.get("sqlite_version", "unknown")

    return (
        f"Grocy System Info:\n"
        f"  Grocy version: {version}\n"
        f"  PHP version: {php_version}\n"
        f"  SQLite version: {sqlite_version}"
    )


async def entity_list(client: GrocyClient, entity: str) -> str:
    """List all objects of a given entity type."""
    items = await client.get_objects(entity)
    if not items:
        return f"No {entity} found (empty)."

    lines = [f"{entity} ({len(items)} item(s)):"]
    for item in items:
        item_id = item.get("id", "?")
        name = item.get("name", str(item))
        lines.append(f"  [{item_id}] {name}")

    return "\n".join(lines)


async def entity_manage(
    client: GrocyClient,
    entity: str,
    action: str,
    obj_id: int | None = None,
    data: dict | None = None,
) -> str:
    """Perform create, update, or delete on any Grocy entity."""
    match action:
        case "create":
            payload = data or {}
            created_id = await client.create_object(entity, payload)
            return f"Created {entity} object with ID {created_id}."

        case "update":
            if obj_id is None:
                return "Update requires an obj_id."
            payload = data or {}
            await client.update_object(entity, obj_id, payload)
            return f"Updated {entity} object ID {obj_id}."

        case "delete":
            if obj_id is None:
                return "Delete requires an obj_id."
            await client.delete_object(entity, obj_id)
            return f"Deleted {entity} object ID {obj_id}."

        case _:
            return f"Unknown action '{action}'. Valid actions: create, update, delete."
