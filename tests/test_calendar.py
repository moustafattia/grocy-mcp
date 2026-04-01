"""Tests for calendar-oriented read models."""

from unittest.mock import AsyncMock

from grocy_mcp.core.calendar import calendar_summary_data


async def test_calendar_summary_data_filters_by_window():
    client = AsyncMock()
    client.get_tasks.return_value = [
        {"id": 1, "name": "Buy milk", "due_date": "2026-04-05"},
        {"id": 2, "name": "Far future", "due_date": "2026-05-01"},
    ]
    client.get_chores.return_value = [
        {
            "chore_id": 3,
            "chore_name": "Vacuum",
            "next_estimated_execution_time": "2026-04-06 10:00:00",
        },
        {
            "chore_id": 4,
            "chore_name": "Dust",
            "next_estimated_execution_time": "2026-05-03 10:00:00",
        },
    ]
    client.get_batteries.return_value = [
        {"battery_id": 9, "next_estimated_charge_time": "2026-04-06 11:00:00"},
        {"battery_id": 10, "next_estimated_charge_time": "2026-05-06 11:00:00"},
    ]
    client.get_objects.side_effect = [
        [
            {"id": 11, "day": "2026-04-05", "recipe_id": 1},
            {"id": 12, "day": "2026-05-06", "recipe_id": 2},
        ],
        [{"id": 1, "name": "Pancakes"}, {"id": 2, "name": "Soup"}],
    ]

    result = await calendar_summary_data(client, "2026-04-05", "2026-04-07")

    assert [task["id"] for task in result["tasks"]] == [1]
    assert [chore["chore_id"] for chore in result["chores"]] == [3]
    assert [battery["battery_id"] for battery in result["batteries"]] == [9]
    assert [entry["id"] for entry in result["meal_plan"]] == [11]
    assert result["meal_plan"][0]["recipe_name"] == "Pancakes"
