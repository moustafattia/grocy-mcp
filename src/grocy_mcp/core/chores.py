"""Core chore management functions for Grocy."""

from __future__ import annotations

from datetime import datetime, timezone

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_chore
from grocy_mcp.core.utils import parse_datetime


async def chores_list(client: GrocyClient) -> str:
    """Return a formatted list of all chores."""
    chores = await client.get_chores()
    if not chores:
        return "No chores found."

    lines = ["Chores:"]
    for entry in chores:
        chore_data = entry.get("chore") or {}
        name = chore_data.get("name", f"Chore {entry.get('chore_id')}")
        next_exec = entry.get("next_estimated_execution_time", "unknown")
        lines.append(f"  [{entry.get('chore_id')}] {name} — next: {next_exec}")

    return "\n".join(lines)


async def chores_overdue(client: GrocyClient) -> str:
    """Return chores that are overdue (next execution time is in the past)."""
    chores = await client.get_chores()
    now = datetime.now(tz=timezone.utc)

    overdue = []
    for entry in chores:
        next_exec_str = entry.get("next_estimated_execution_time")
        next_exec = parse_datetime(next_exec_str)
        if next_exec and next_exec < now:
            chore_data = entry.get("chore") or {}
            name = chore_data.get("name", f"Chore {entry.get('chore_id')}")
            overdue.append((name, next_exec_str))

    if not overdue:
        return "No overdue chores."

    lines = ["Overdue chores:"]
    for name, next_exec in overdue:
        lines.append(f"  {name} — was due: {next_exec}")

    return "\n".join(lines)


async def chore_execute(client: GrocyClient, chore: str, done_by: int | None = None) -> str:
    """Execute (mark as done) a chore."""
    chore_id = await resolve_chore(client, chore)
    await client.execute_chore(chore_id, done_by)
    return f"Chore '{chore}' executed."


async def chore_undo(client: GrocyClient, chore: str) -> str:
    """Undo the most recent execution of a chore."""
    chore_id = await resolve_chore(client, chore)
    executions = await client.get_chore_executions(chore_id)

    if not executions:
        return f"No executions found for chore '{chore}'."

    # Find the most recent execution by id (highest id = most recent)
    most_recent = max(executions, key=lambda e: e.get("id", 0))
    await client.undo_chore_execution(most_recent["id"])
    return f"Undone most recent execution (ID {most_recent['id']}) of chore '{chore}'."


async def chore_create(client: GrocyClient, name: str, **kwargs) -> str:
    """Create a new chore."""
    chore_data = {"name": name, **kwargs}
    chore_id = await client.create_object("chores", chore_data)
    return f"Chore '{name}' created (ID {chore_id})."
