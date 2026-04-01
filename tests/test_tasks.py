"""Tests for the tasks core module."""

from unittest.mock import AsyncMock

from grocy_mcp.core.tasks import task_complete, task_create, task_delete, tasks_list


async def test_tasks_list():
    client = AsyncMock()
    client.get_objects.return_value = [
        {
            "id": 1,
            "name": "Buy groceries",
            "done": 0,
            "due_date": "2026-04-05",
            "category_id": None,
        },
        {"id": 2, "name": "Call dentist", "done": 0, "due_date": None, "category_id": 3},
    ]
    result = await tasks_list(client)
    assert "Buy groceries" in result
    assert "Call dentist" in result
    assert "due: 2026-04-05" in result
    assert "[cat:3]" in result


async def test_tasks_list_hides_done():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Done task", "done": 1},
        {"id": 2, "name": "Open task", "done": 0},
    ]
    result = await tasks_list(client)
    assert "Open task" in result
    assert "Done task" not in result


async def test_tasks_list_show_done():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Done task", "done": 1},
        {"id": 2, "name": "Open task", "done": 0},
    ]
    result = await tasks_list(client, show_done=True)
    assert "Done task" in result
    assert "Open task" in result
    assert "(done)" in result


async def test_tasks_list_empty():
    client = AsyncMock()
    client.get_objects.return_value = []
    result = await tasks_list(client)
    assert result == "No tasks found."


async def test_task_create():
    client = AsyncMock()
    client.create_object.return_value = 10
    result = await task_create(client, "Buy milk")
    client.create_object.assert_called_once_with("tasks", {"name": "Buy milk"})
    assert "'Buy milk'" in result
    assert "10" in result


async def test_task_create_with_all_options():
    client = AsyncMock()
    client.create_object.return_value = 11
    result = await task_create(
        client, "Fix door", due_date="2026-04-10", assigned_to_user_id=2, description="Squeaky"
    )
    client.create_object.assert_called_once_with(
        "tasks",
        {
            "name": "Fix door",
            "due_date": "2026-04-10",
            "assigned_to_user_id": 2,
            "description": "Squeaky",
        },
    )
    assert "'Fix door'" in result


async def test_task_complete():
    client = AsyncMock()
    result = await task_complete(client, 5)
    client.update_object.assert_called_once_with("tasks", 5, {"done": 1})
    assert "5" in result
    assert "done" in result


async def test_task_delete():
    client = AsyncMock()
    result = await task_delete(client, 7)
    client.delete_object.assert_called_once_with("tasks", 7)
    assert "7" in result
    assert "deleted" in result.lower()
