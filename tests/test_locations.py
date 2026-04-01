"""Tests for the locations core module."""

from unittest.mock import AsyncMock

from grocy_mcp.core.locations import location_create, locations_list


async def test_locations_list():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Fridge", "is_freezer": 0, "description": ""},
        {"id": 2, "name": "Freezer", "is_freezer": 1, "description": "Garage freezer"},
    ]
    result = await locations_list(client)
    assert "Fridge" in result
    assert "Freezer" in result
    assert "(freezer)" in result
    assert "Garage freezer" in result
    assert "[1]" in result
    assert "[2]" in result


async def test_locations_list_empty():
    client = AsyncMock()
    client.get_objects.return_value = []
    result = await locations_list(client)
    assert result == "No locations found."


async def test_location_create():
    client = AsyncMock()
    client.create_object.return_value = 5
    result = await location_create(client, "Pantry")
    client.create_object.assert_called_once_with("locations", {"name": "Pantry"})
    assert "'Pantry'" in result
    assert "5" in result


async def test_location_create_freezer_with_description():
    client = AsyncMock()
    client.create_object.return_value = 6
    result = await location_create(client, "Deep Freeze", is_freezer=True, description="Basement")
    client.create_object.assert_called_once_with(
        "locations", {"name": "Deep Freeze", "is_freezer": 1, "description": "Basement"}
    )
    assert "'Deep Freeze'" in result
