"""Tests for the chores core module."""

from unittest.mock import AsyncMock, patch
import pytest

from grocy_mcp.core.chores import (
    chore_create,
    chore_execute,
    chore_undo,
    chores_list,
    chores_overdue,
)


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_chores.return_value = [
        {
            "chore_id": 1,
            "chore": {"id": 1, "name": "Vacuum"},
            "next_estimated_execution_time": "2026-01-01 10:00:00",
            "last_tracked_time": "2025-12-01 10:00:00",
        },
        {
            "chore_id": 2,
            "chore": {"id": 2, "name": "Mop floors"},
            "next_estimated_execution_time": "2099-01-01 10:00:00",
            "last_tracked_time": None,
        },
    ]
    client.execute_chore.return_value = None
    client.get_chore_executions.return_value = [
        {"id": 100, "chore_id": 1, "tracked_time": "2026-01-01 10:00:00"},
        {"id": 101, "chore_id": 1, "tracked_time": "2026-02-01 10:00:00"},
    ]
    client.undo_chore_execution.return_value = None
    client.create_object.return_value = 5
    return client


async def test_chores_list(mock_client):
    result = await chores_list(mock_client)
    assert "Vacuum" in result
    assert "Mop floors" in result


async def test_chores_overdue(mock_client):
    result = await chores_overdue(mock_client)
    # Vacuum has a past due date (2026-01-01) which is before today (2026-03-31)
    assert "Vacuum" in result
    # Mop floors has a future date — should NOT appear
    assert "Mop floors" not in result


async def test_chore_execute(mock_client):
    with patch("grocy_mcp.core.chores.resolve_chore", return_value=1):
        result = await chore_execute(mock_client, "Vacuum", done_by=7)
        mock_client.execute_chore.assert_called_once_with(1, 7)
        assert result


async def test_chore_undo(mock_client):
    with patch("grocy_mcp.core.chores.resolve_chore", return_value=1):
        result = await chore_undo(mock_client, "Vacuum")
        mock_client.get_chore_executions.assert_called_once_with(1)
        # Should undo the most recent execution (id=101)
        mock_client.undo_chore_execution.assert_called_once_with(101)
        assert result


async def test_chore_create(mock_client):
    result = await chore_create(mock_client, "Water plants")
    mock_client.create_object.assert_called_once_with("chores", {"name": "Water plants"})
    assert "Water plants" in result
    assert "5" in result
