"""Core task management functions for Grocy."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient


async def tasks_list(client: GrocyClient, show_done: bool = False) -> str:
    """Return a formatted list of tasks."""
    tasks = await client.get_objects("tasks")
    if not show_done:
        tasks = [t for t in tasks if not t.get("done")]

    if not tasks:
        return "No tasks found." if not show_done else "No tasks found (including completed)."

    label = "Tasks:" if not show_done else "Tasks (including completed):"
    lines = [label]
    for t in tasks:
        name = t.get("name", "?")
        done = " (done)" if t.get("done") else ""
        due = t.get("due_date")
        due_str = f" — due: {due}" if due else ""
        category_id = t.get("category_id")
        cat_str = f" [cat:{category_id}]" if category_id else ""
        lines.append(f"  [{t['id']}] {name}{done}{due_str}{cat_str}")

    return "\n".join(lines)


async def task_create(
    client: GrocyClient,
    name: str,
    due_date: str | None = None,
    assigned_to_user_id: int | None = None,
    description: str = "",
) -> str:
    """Create a new task."""
    data: dict = {"name": name}
    if due_date:
        data["due_date"] = due_date
    if assigned_to_user_id is not None:
        data["assigned_to_user_id"] = assigned_to_user_id
    if description:
        data["description"] = description

    task_id = await client.create_object("tasks", data)
    return f"Task '{name}' created (ID {task_id})."


async def task_complete(client: GrocyClient, task_id: int) -> str:
    """Mark a task as done."""
    await client.update_object("tasks", task_id, {"done": 1})
    return f"Task {task_id} marked as done."


async def task_delete(client: GrocyClient, task_id: int) -> str:
    """Delete a task."""
    await client.delete_object("tasks", task_id)
    return f"Task {task_id} deleted."
