"""Calendar-oriented read models for Grocy planning surfaces."""

from __future__ import annotations

from datetime import date, datetime, timezone

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.chores import _parse_datetime


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for candidate in (value[:10], value):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def _in_date_range(day: date | None, start_date: str | None, end_date: str | None) -> bool:
    if day is None:
        return False
    if start_date and day < date.fromisoformat(start_date):
        return False
    if end_date and day > date.fromisoformat(end_date):
        return False
    return True


async def calendar_summary_data(
    client: GrocyClient,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return a combined planning summary across chores, batteries, tasks, and meal plan."""
    now = datetime.now(tz=timezone.utc)
    open_tasks = await client.get_tasks()
    chores = await client.get_chores()
    batteries = await client.get_batteries()
    meal_plan_entries = await client.get_objects("meal_plan")
    recipes = await client.get_objects("recipes")

    recipe_map = {recipe["id"]: recipe.get("name", f"Recipe {recipe['id']}") for recipe in recipes}

    filtered_tasks = []
    for task in open_tasks:
        due_date = _parse_date(task.get("due_date"))
        if start_date or end_date:
            if due_date is None or not _in_date_range(due_date, start_date, end_date):
                continue
        filtered_tasks.append(task)

    chore_rows = []
    for row in chores:
        next_exec = _parse_datetime(row.get("next_estimated_execution_time"))
        if start_date or end_date:
            if next_exec is None or not _in_date_range(next_exec.date(), start_date, end_date):
                continue
        chore_rows.append(row)

    battery_rows = []
    for row in batteries:
        next_charge = _parse_datetime(row.get("next_estimated_charge_time"))
        if start_date or end_date:
            if next_charge is None or not _in_date_range(next_charge.date(), start_date, end_date):
                continue
        battery_rows.append(row)

    meal_rows = []
    for row in meal_plan_entries:
        day = _parse_date(row.get("day"))
        if start_date or end_date:
            if day is None or not _in_date_range(day, start_date, end_date):
                continue
        meal_rows.append(
            {
                **row,
                "recipe_name": recipe_map.get(row.get("recipe_id")),
            }
        )

    return {
        "window": {"from": start_date, "to": end_date},
        "generated_at": now.isoformat(),
        "tasks": filtered_tasks,
        "chores": chore_rows,
        "batteries": battery_rows,
        "meal_plan": meal_rows,
    }


async def calendar_summary(
    client: GrocyClient,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Return a human-readable planning summary."""
    data = await calendar_summary_data(client, start_date, end_date)
    lines = ["Calendar summary:"]
    if start_date or end_date:
        lines.append(f"  window: {start_date or 'open'} -> {end_date or 'open'}")
    lines.append(f"  open tasks: {len(data['tasks'])}")
    lines.append(f"  chores in window: {len(data['chores'])}")
    lines.append(f"  batteries in window: {len(data['batteries'])}")
    lines.append(f"  meal plan entries: {len(data['meal_plan'])}")

    if data["tasks"]:
        lines.append("Tasks:")
        for task in data["tasks"][:5]:
            assignee = (task.get("assigned_to_user") or {}).get("display_name")
            suffix = f" — assigned to {assignee}" if assignee else ""
            lines.append(
                f"  [{task.get('id')}] {task.get('name')} — due {task.get('due_date')}{suffix}"
            )

    if data["chores"]:
        lines.append("Chores:")
        for chore in data["chores"][:5]:
            chore_name = chore.get("chore_name") or (chore.get("chore") or {}).get("name")
            assignee = (chore.get("next_execution_assigned_user") or {}).get("display_name")
            suffix = f" — assigned to {assignee}" if assignee else ""
            lines.append(
                f"  [{chore.get('chore_id')}] {chore_name} — next {chore.get('next_estimated_execution_time')}{suffix}"
            )

    if data["batteries"]:
        lines.append("Batteries:")
        for battery in data["batteries"][:5]:
            lines.append(
                f"  [{battery.get('battery_id')}] next charge {battery.get('next_estimated_charge_time')}"
            )

    if data["meal_plan"]:
        lines.append("Meal plan:")
        for entry in sorted(data["meal_plan"], key=lambda row: row.get("day", ""))[:5]:
            label = entry.get("recipe_name") or entry.get("note") or "entry"
            lines.append(f"  [{entry.get('id')}] {entry.get('day')} — {label}")

    return "\n".join(lines)


async def calendar_ical_export(client: GrocyClient) -> str:
    """Return the raw iCal export."""
    return await client.get_calendar_ical()


async def calendar_sharing_link(client: GrocyClient) -> str:
    """Return the public iCal sharing link."""
    data = await client.get_calendar_sharing_link()
    return f"Calendar sharing link: {data.get('url', 'unavailable')}"
