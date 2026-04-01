"""Tests for equipment helpers."""

from unittest.mock import AsyncMock

from grocy_mcp.core.equipment import equipment_details_data, equipment_list_data


async def test_equipment_list_data_enriches_battery_name():
    client = AsyncMock()
    client.get_objects.side_effect = [
        [{"id": 1, "name": "Vacuum", "battery_id": 10, "description": "Cordless"}],
        [{"id": 10, "name": "Battery Pack"}],
    ]

    result = await equipment_list_data(client)

    assert result[0]["linked_battery_name"] == "Battery Pack"


async def test_equipment_details_data_enriches_linked_battery_name():
    client = AsyncMock()
    client.get_objects.return_value = [{"id": 1, "name": "Vacuum"}]
    client.get_object.side_effect = [
        {"id": 1, "name": "Vacuum", "battery_id": 10},
        {"id": 10, "name": "Battery Pack"},
    ]

    result = await equipment_details_data(client, "Vacuum")

    assert result["linked_battery_name"] == "Battery Pack"
