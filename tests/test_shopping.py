"""Tests for the shopping list core module."""

from unittest.mock import AsyncMock, patch

import pytest

from grocy_mcp.core.shopping import (
    shopping_list_add,
    shopping_list_add_missing,
    shopping_list_clear,
    shopping_list_remove,
    shopping_list_set_amount,
    shopping_list_set_note,
    shopping_list_update,
    shopping_list_view,
)


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_shopping_list.return_value = [
        {"id": 1, "product_id": 1, "amount": 2, "shopping_list_id": 1, "note": None},
        {"id": 2, "product_id": 2, "amount": 1, "shopping_list_id": 1, "note": "fresh"},
    ]
    client.get_objects.return_value = [
        {"id": 1, "name": "Milk"},
        {"id": 2, "name": "Bread"},
    ]
    client.add_shopping_list_item.return_value = 3
    client.update_shopping_list_item.return_value = None
    client.remove_shopping_list_item.return_value = None
    client.clear_shopping_list.return_value = None
    client.add_missing_products_to_shopping_list.return_value = None
    return client


async def test_shopping_list_view(mock_client):
    result = await shopping_list_view(mock_client)
    assert "Milk" in result
    assert "Bread" in result
    assert "2" in result


async def test_shopping_list_add(mock_client):
    with patch("grocy_mcp.core.shopping.resolve_product", return_value=1):
        result = await shopping_list_add(mock_client, "Milk", 2.0, list_id=3, note="organic")
        mock_client.add_shopping_list_item.assert_called_once_with(1, 2.0, 3, "organic")
        assert result


async def test_shopping_list_update(mock_client):
    result = await shopping_list_update(mock_client, 1, {"amount": 5})
    mock_client.update_shopping_list_item.assert_called_once_with(1, {"amount": 5})
    assert result


async def test_shopping_list_remove(mock_client):
    result = await shopping_list_remove(mock_client, 1)
    mock_client.remove_shopping_list_item.assert_called_once_with(1)
    assert result


async def test_shopping_list_clear(mock_client):
    result = await shopping_list_clear(mock_client)
    mock_client.clear_shopping_list.assert_called_once()
    assert result


async def test_shopping_list_add_missing(mock_client):
    result = await shopping_list_add_missing(mock_client)
    mock_client.add_missing_products_to_shopping_list.assert_called_once()
    assert result


async def test_shopping_list_view_empty(mock_client):
    mock_client.get_shopping_list.return_value = []
    result = await shopping_list_view(mock_client)
    assert result == "No shopping list items found."


async def test_shopping_list_view_with_list_id(mock_client):
    result = await shopping_list_view(mock_client, list_id=5)
    mock_client.get_shopping_list.assert_called_once_with(5)
    assert "Shopping list #5:" in result


async def test_shopping_list_view_shows_note(mock_client):
    result = await shopping_list_view(mock_client)
    assert "(fresh)" in result


async def test_shopping_list_view_format(mock_client):
    result = await shopping_list_view(mock_client)
    # Uses em-dash separator
    assert "[1] Milk" in result
    assert "—" in result


async def test_shopping_list_add_default_params(mock_client):
    with patch("grocy_mcp.core.shopping.resolve_product", return_value=1):
        result = await shopping_list_add(mock_client, "Milk")
        mock_client.add_shopping_list_item.assert_called_once_with(1, 1.0, 1, None)
        assert "'Milk'" in result


async def test_shopping_list_clear_with_list_id(mock_client):
    result = await shopping_list_clear(mock_client, list_id=3)
    mock_client.clear_shopping_list.assert_called_once_with(3)
    assert "#3" in result


async def test_shopping_list_add_missing_with_list_id(mock_client):
    result = await shopping_list_add_missing(mock_client, list_id=2)
    mock_client.add_missing_products_to_shopping_list.assert_called_once_with(2)
    assert "#2" in result


async def test_shopping_list_set_amount(mock_client):
    result = await shopping_list_set_amount(mock_client, 5, 3.0)
    mock_client.update_shopping_list_item.assert_called_once_with(5, {"amount": 3.0})
    assert "5" in result
    assert "3.0" in result


async def test_shopping_list_set_note(mock_client):
    result = await shopping_list_set_note(mock_client, 5, "organic")
    mock_client.update_shopping_list_item.assert_called_once_with(5, {"note": "organic"})
    assert "5" in result
    assert "'organic'" in result
