"""First-class battery views and actions for Grocy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.chores import _parse_datetime
from grocy_mcp.core.resolve import resolve_entity


async def batteries_list(client: GrocyClient) -> str:
    """Return a formatted list of batteries with next estimated charge times."""
    data = await batteries_list_data(client)
    if not data:
        return "No batteries found."

    lines = ["Batteries:"]
    for entry in data:
        suffix = f" — used in: {entry['used_in']}" if entry.get("used_in") else ""
        lines.append(
            f"  [{entry['battery_id']}] {entry['name']} — next charge: "
            f"{entry.get('next_estimated_charge_time', 'unknown')}{suffix}"
        )
    return "\n".join(lines)


async def batteries_list_data(client: GrocyClient) -> list[dict]:
    """Return battery rows enriched with names and usage info."""
    batteries = await client.get_objects("batteries")
    battery_map = {battery["id"]: battery for battery in batteries}
    current = await client.get_batteries()
    rows = []
    for entry in current or [{"battery_id": battery["id"]} for battery in batteries]:
        battery = battery_map.get(entry.get("battery_id"), {})
        rows.append(
            {
                **entry,
                "name": battery.get("name", f"Battery {entry.get('battery_id')}"),
                "used_in": battery.get("used_in"),
                "description": battery.get("description"),
                "charge_interval_days": battery.get("charge_interval_days"),
            }
        )
    return rows


async def battery_details(client: GrocyClient, battery: str) -> str:
    """Return detailed battery information."""
    data = await battery_details_data(client, battery)
    lines = [f"Battery details for '{data.get('name', battery)}':"]
    for field in (
        "id",
        "description",
        "used_in",
        "charge_interval_days",
        "last_charged",
        "charge_cycles_count",
        "next_estimated_charge_time",
    ):
        value = data.get(field)
        if value not in (None, ""):
            lines.append(f"  {field}: {value}")
    return "\n".join(lines)


async def battery_details_data(client: GrocyClient, battery: str) -> dict:
    """Return detailed battery information as structured data."""
    battery_id = await resolve_entity(client, "batteries", battery)
    details = await client.get_battery(battery_id)
    battery_data = details.get("battery") or details.get("chore") or {}
    return {
        **battery_data,
        "last_charged": details.get("last_charged"),
        "charge_cycles_count": details.get("charge_cycles_count"),
        "next_estimated_charge_time": details.get("next_estimated_charge_time"),
    }


async def batteries_due(client: GrocyClient, days: int = 7) -> str:
    """Return batteries that are due within the given number of days."""
    due_items = await batteries_due_data(client, days)

    if not due_items:
        return f"No batteries due within {days} day(s)."

    lines = [f"Batteries due within {days} day(s):"]
    for item in due_items:
        lines.append(f"  {item['name']} — due: {item['next_estimated_charge_time']}")
    return "\n".join(lines)


async def batteries_due_data(client: GrocyClient, days: int = 7) -> list[dict]:
    """Return batteries due within the given number of days as structured data."""
    current = await batteries_list_data(client)
    now = datetime.now(tz=timezone.utc)
    cutoff = now + timedelta(days=days)

    due_items = []
    for entry in current:
        next_charge = _parse_datetime(entry.get("next_estimated_charge_time"))
        if next_charge and now <= next_charge <= cutoff:
            due_items.append({**entry, "next_estimated_charge_time": next_charge.isoformat()})
    return sorted(due_items, key=lambda item: item["next_estimated_charge_time"])


async def batteries_overdue(client: GrocyClient) -> str:
    """Return batteries that are already overdue for charging."""
    overdue_items = await batteries_overdue_data(client)

    if not overdue_items:
        return "No overdue batteries."

    lines = ["Overdue batteries:"]
    for item in overdue_items:
        lines.append(f"  {item['name']} — due: {item['next_estimated_charge_time']}")
    return "\n".join(lines)


async def batteries_overdue_data(client: GrocyClient) -> list[dict]:
    """Return overdue batteries as structured data."""
    current = await batteries_list_data(client)
    now = datetime.now(tz=timezone.utc)

    overdue_items = []
    for entry in current:
        next_charge = _parse_datetime(entry.get("next_estimated_charge_time"))
        if next_charge and next_charge < now:
            overdue_items.append({**entry, "next_estimated_charge_time": next_charge.isoformat()})
    return sorted(overdue_items, key=lambda item: item["next_estimated_charge_time"])


async def battery_charge(client: GrocyClient, battery: str, tracked_time: str | None = None) -> str:
    """Track a battery charge cycle."""
    battery_id = await resolve_entity(client, "batteries", battery)
    await client.charge_battery(battery_id, tracked_time)
    return f"Battery '{battery}' charged."


async def battery_cycle_history(client: GrocyClient, battery: str) -> str:
    """Return the charge-cycle history for a battery."""
    cycles = await battery_cycle_history_data(client, battery)
    if not cycles:
        return f"No charge cycles found for battery '{battery}'."

    lines = [f"Charge cycles for '{battery}':"]
    for cycle in cycles:
        lines.append(
            f"  [{cycle.get('id')}] tracked_time={cycle.get('tracked_time')} "
            f"created={cycle.get('row_created_timestamp')}"
        )
    return "\n".join(lines)


async def battery_cycle_history_data(client: GrocyClient, battery: str) -> list[dict]:
    """Return the charge-cycle history for a battery as structured data."""
    battery_id = await resolve_entity(client, "batteries", battery)
    cycles = await client.get_objects("battery_charge_cycles")
    cycles = [cycle for cycle in cycles if cycle.get("battery_id") == battery_id]
    cycles.sort(key=lambda cycle: cycle.get("tracked_time", ""), reverse=True)
    return cycles


async def battery_undo_cycle(client: GrocyClient, cycle_id: int) -> str:
    """Undo a previously tracked battery charge cycle."""
    await client.undo_battery_charge_cycle(cycle_id)
    return f"Battery charge cycle {cycle_id} undone."


async def battery_create(
    client: GrocyClient,
    name: str,
    used_in: str = "",
    charge_interval_days: int = 0,
    description: str = "",
) -> str:
    """Create a battery object."""
    data: dict[str, object] = {"name": name, "charge_interval_days": charge_interval_days}
    if used_in:
        data["used_in"] = used_in
    if description:
        data["description"] = description
    battery_id = await client.create_object("batteries", data)
    return f"Battery '{name}' created (ID {battery_id})."


async def battery_update(
    client: GrocyClient,
    battery: str,
    name: str | None = None,
    used_in: str | None = None,
    charge_interval_days: int | None = None,
    description: str | None = None,
) -> str:
    """Update a battery object."""
    battery_id = await resolve_entity(client, "batteries", battery)
    data: dict[str, object] = {}
    if name is not None:
        data["name"] = name
    if used_in is not None:
        data["used_in"] = used_in
    if charge_interval_days is not None:
        data["charge_interval_days"] = charge_interval_days
    if description is not None:
        data["description"] = description
    await client.update_object("batteries", battery_id, data)
    return f"Battery '{battery}' updated."
