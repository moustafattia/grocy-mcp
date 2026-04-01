"""Tests for name-to-ID resolution."""

from unittest.mock import AsyncMock

import pytest

from grocy_mcp.core.resolve import resolve_entity
from grocy_mcp.exceptions import GrocyResolveError


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Milk"},
        {"id": 2, "name": "Milk 2%"},
        {"id": 3, "name": "Almond Milk"},
        {"id": 4, "name": "Bread"},
    ]
    return client


async def test_resolve_by_numeric_id(mock_client):
    result = await resolve_entity(mock_client, "products", "4")
    assert result == 4
    mock_client.get_objects.assert_not_called()


async def test_resolve_exact_match(mock_client):
    result = await resolve_entity(mock_client, "products", "Milk")
    assert result == 1


async def test_resolve_exact_match_case_insensitive(mock_client):
    result = await resolve_entity(mock_client, "products", "milk")
    assert result == 1


async def test_resolve_single_substring_match(mock_client):
    result = await resolve_entity(mock_client, "products", "Bread")
    assert result == 4


async def test_resolve_ambiguous_without_exact(mock_client):
    with pytest.raises(GrocyResolveError, match="Multiple"):
        await resolve_entity(mock_client, "products", "ilk")


async def test_resolve_zero_matches(mock_client):
    with pytest.raises(GrocyResolveError, match="No .* found"):
        await resolve_entity(mock_client, "products", "Cheese")


async def test_resolve_exact_match_wins_over_substring(mock_client):
    """When 'Milk' is searched, exact match (id=1) wins over substring 'Milk 2%' (id=2)."""
    result = await resolve_entity(mock_client, "products", "Milk")
    assert result == 1


async def test_resolve_with_custom_name_field():
    """Resolution should work with a non-default name field."""
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "display_name": "Morning routine"},
        {"id": 2, "display_name": "Evening routine"},
    ]
    result = await resolve_entity(client, "routines", "morning", name_field="display_name")
    assert result == 1


async def test_resolve_empty_entity_list():
    """Empty entity list should raise with helpful message."""
    client = AsyncMock()
    client.get_objects.return_value = []
    with pytest.raises(GrocyResolveError, match="No .* found"):
        await resolve_entity(client, "products", "anything")


async def test_resolve_numeric_zero():
    """'0' is a valid numeric ID and should be returned as int."""
    client = AsyncMock()
    # isdigit() returns True for "0"
    result = await resolve_entity(client, "products", "0")
    assert result == 0
    client.get_objects.assert_not_called()


async def test_resolve_ambiguous_error_lists_candidates(mock_client):
    """Ambiguous matches should list candidate names in error."""
    with pytest.raises(GrocyResolveError) as exc_info:
        await resolve_entity(mock_client, "products", "ilk")
    msg = str(exc_info.value)
    assert "Milk" in msg
    assert "Milk 2%" in msg
    assert "Almond Milk" in msg


async def test_resolve_product_wrapper():
    """resolve_product should delegate to resolve_entity for products."""
    from grocy_mcp.core.resolve import resolve_product

    client = AsyncMock()
    client.get_objects.return_value = [{"id": 42, "name": "Eggs"}]
    result = await resolve_product(client, "Eggs")
    assert result == 42
    client.get_objects.assert_called_once_with("products")


async def test_resolve_location_wrapper():
    """resolve_location should delegate to resolve_entity for locations."""
    from grocy_mcp.core.resolve import resolve_location

    client = AsyncMock()
    client.get_objects.return_value = [{"id": 3, "name": "Pantry"}]
    result = await resolve_location(client, "Pantry")
    assert result == 3
    client.get_objects.assert_called_once_with("locations")
