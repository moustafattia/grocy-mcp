"""Tests for battery helpers."""

from unittest.mock import AsyncMock

from grocy_mcp.core.batteries import (
    batteries_due_data,
    batteries_overdue_data,
    battery_cycle_history_data,
)


async def test_batteries_due_data():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Remote battery", "used_in": "TV remote"},
    ]
    client.get_batteries.return_value = [
        {
            "battery_id": 1,
            "last_tracked_time": "2026-04-01 10:00:00",
            "next_estimated_charge_time": "2999-12-31 23:59:59",
        }
    ]

    result = await batteries_due_data(client, days=7)

    assert result == []


async def test_batteries_overdue_data():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Remote battery", "used_in": "TV remote"},
    ]
    client.get_batteries.return_value = [
        {
            "battery_id": 1,
            "last_tracked_time": "2026-04-01 10:00:00",
            "next_estimated_charge_time": "2000-01-01 00:00:00",
        }
    ]

    result = await batteries_overdue_data(client)

    assert len(result) == 1
    assert result[0]["name"] == "Remote battery"


async def test_battery_cycle_history_data_filters_and_sorts():
    client = AsyncMock()
    client.get_objects.side_effect = [
        [{"id": 1, "name": "Remote battery"}],
        [
            {"id": 3, "battery_id": 1, "tracked_time": "2026-04-02 10:00:00"},
            {"id": 2, "battery_id": 1, "tracked_time": "2026-04-01 10:00:00"},
            {"id": 9, "battery_id": 2, "tracked_time": "2026-04-03 10:00:00"},
        ],
    ]

    result = await battery_cycle_history_data(client, "Remote battery")

    assert [cycle["id"] for cycle in result] == [3, 2]
