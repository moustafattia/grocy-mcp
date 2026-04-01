"""Tests for first-class metadata and discovery helpers."""

from unittest.mock import AsyncMock

from grocy_mcp.core.reference_data import (
    describe_entity_data,
    list_entity_records,
    list_entity_view,
    search_entity_candidates_data,
)


async def test_list_entity_view_for_shopping_locations():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Market", "description": "Weekly shop"},
        {"id": 2, "name": "Pharmacy", "description": ""},
    ]

    result = await list_entity_view(client, "shopping_locations")

    assert "Shopping locations" in result
    assert "[1] Market" in result
    assert "description=Weekly shop" in result


async def test_list_entity_records_applies_query_filter():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Pantry"},
        {"id": 2, "name": "Freezer"},
    ]

    result = await list_entity_records(client, "shopping_lists", "pan")

    assert result == [{"id": 1, "name": "Pantry"}]


async def test_search_entity_candidates_data_for_products():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Whole Milk", "description": "Organic"},
        {"id": 2, "name": "Bread", "description": "Sourdough"},
    ]

    result = await search_entity_candidates_data(client, "products", "milk")

    assert result == [{"id": 1, "label": "Whole Milk", "summary": ["description=Organic"]}]


async def test_describe_entity_data_marks_read_only_views():
    client = AsyncMock()
    client.get_objects.return_value = [{"id": 1, "product_id": 3, "avg_price": 1.29}]

    result = await describe_entity_data(client, "products_average_price")

    assert result["supports_create"] is False
    assert result["supports_update"] is False
    assert result["supports_delete"] is False
    assert "avg_price" in result["sample_fields"]
