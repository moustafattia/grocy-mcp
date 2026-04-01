"""Tests for the stock core module."""

from unittest.mock import AsyncMock, patch

import pytest

from grocy_mcp.core.stock import (
    stock_add,
    stock_barcode_lookup,
    stock_consume,
    stock_expiring,
    stock_inventory,
    stock_open,
    stock_overview,
    stock_product_info,
    stock_search,
    stock_transfer,
)


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_stock.return_value = [
        {"product_id": 1, "amount": 3, "product": {"id": 1, "name": "Milk", "location_id": 1}}
    ]
    client.get_volatile_stock.return_value = {
        "expiring_products": [{"product_id": 1, "amount": 3, "product": {"id": 1, "name": "Milk"}}],
        "expired_products": [],
        "missing_products": [],
    }
    client.get_objects.return_value = [
        {"id": 1, "name": "Milk"},
        {"id": 2, "name": "Bread"},
    ]
    client.add_stock.return_value = [{"id": 10}]
    client.consume_stock.return_value = [{"id": 10}]
    return client


async def test_stock_overview(mock_client):
    result = await stock_overview(mock_client)
    assert "Milk" in result
    assert "3" in result


async def test_stock_expiring(mock_client):
    result = await stock_expiring(mock_client)
    assert "Milk" in result


async def test_stock_add(mock_client):
    with patch("grocy_mcp.core.stock.resolve_product", return_value=1) as mock_resolve:
        result = await stock_add(mock_client, "Milk", 2.0)
        mock_resolve.assert_called_once_with(mock_client, "Milk")
        mock_client.add_stock.assert_called_once_with(1, 2.0)
        assert "added" in result.lower() or "milk" in result.lower()


async def test_stock_consume(mock_client):
    with patch("grocy_mcp.core.stock.resolve_product", return_value=1):
        result = await stock_consume(mock_client, "Milk", 1.0)
        mock_client.consume_stock.assert_called_once_with(1, 1.0)
        assert result


async def test_stock_search(mock_client):
    result = await stock_search(mock_client, "Milk")
    assert "Milk" in result


async def test_stock_product_info(mock_client):
    mock_client.get_stock_product.return_value = {
        "product": {"id": 1, "name": "Milk"},
        "stock_amount": 3,
        "next_best_before_date": "2026-04-01",
    }
    with patch("grocy_mcp.core.stock.resolve_product", return_value=1):
        result = await stock_product_info(mock_client, "Milk")
        mock_client.get_stock_product.assert_called_once_with(1)
        assert "Milk" in result


async def test_stock_transfer(mock_client):
    mock_client.transfer_stock.return_value = [{"id": 10}]
    with (
        patch("grocy_mcp.core.stock.resolve_product", return_value=1),
        patch("grocy_mcp.core.stock.resolve_location", return_value=2),
    ):
        result = await stock_transfer(mock_client, "Milk", 1.0, "Fridge")
        mock_client.transfer_stock.assert_called_once_with(1, 1.0, 2)
        assert result


async def test_stock_inventory(mock_client):
    mock_client.inventory_stock.return_value = [{"id": 10}]
    with patch("grocy_mcp.core.stock.resolve_product", return_value=1):
        result = await stock_inventory(mock_client, "Milk", 5.0)
        mock_client.inventory_stock.assert_called_once_with(1, 5.0)
        assert result


async def test_stock_open(mock_client):
    mock_client.open_stock.return_value = [{"id": 10}]
    with patch("grocy_mcp.core.stock.resolve_product", return_value=1):
        result = await stock_open(mock_client, "Milk", 1.0)
        mock_client.open_stock.assert_called_once_with(1, 1.0)
        assert result


async def test_stock_barcode_lookup(mock_client):
    mock_client.get_stock_by_barcode.return_value = {
        "product": {"id": 1, "name": "Milk"},
        "stock_amount": 3,
    }
    result = await stock_barcode_lookup(mock_client, "1234567890")
    mock_client.get_stock_by_barcode.assert_called_once_with("1234567890")
    assert "Milk" in result


async def test_stock_overview_empty(mock_client):
    mock_client.get_stock.return_value = []
    result = await stock_overview(mock_client)
    assert result == "No stock found."


async def test_stock_overview_format(mock_client):
    result = await stock_overview(mock_client)
    assert "Current stock:" in result
    assert "[1] Milk" in result


async def test_stock_expiring_empty(mock_client):
    mock_client.get_volatile_stock.return_value = {
        "expiring_products": [],
        "expired_products": [],
        "missing_products": [],
    }
    result = await stock_expiring(mock_client)
    assert "No expiring, expired, or missing products found." in result


async def test_stock_add_quotes_name(mock_client):
    with patch("grocy_mcp.core.stock.resolve_product", return_value=1):
        result = await stock_add(mock_client, "Milk", 2.0)
        assert "'Milk'" in result


async def test_stock_consume_quotes_name(mock_client):
    with patch("grocy_mcp.core.stock.resolve_product", return_value=1):
        result = await stock_consume(mock_client, "Milk", 1.0)
        assert "'Milk'" in result


async def test_stock_transfer_quotes_names(mock_client):
    mock_client.transfer_stock.return_value = [{"id": 10}]
    with (
        patch("grocy_mcp.core.stock.resolve_product", return_value=1),
        patch("grocy_mcp.core.stock.resolve_location", return_value=2),
    ):
        result = await stock_transfer(mock_client, "Eggs", 3.0, "Fridge")
        assert "'Eggs'" in result
        assert "'Fridge'" in result


async def test_stock_inventory_quotes_name(mock_client):
    mock_client.inventory_stock.return_value = [{"id": 10}]
    with patch("grocy_mcp.core.stock.resolve_product", return_value=1):
        result = await stock_inventory(mock_client, "Milk", 5.0)
        assert "'Milk'" in result


async def test_stock_open_quotes_name(mock_client):
    mock_client.open_stock.return_value = [{"id": 10}]
    with patch("grocy_mcp.core.stock.resolve_product", return_value=1):
        result = await stock_open(mock_client, "Milk", 1.0)
        assert "'Milk'" in result


async def test_stock_search_uses_bracket_ids(mock_client):
    mock_client.get_objects.side_effect = [
        [{"id": 1, "name": "Milk"}, {"id": 2, "name": "Bread"}],
        [],
    ]
    result = await stock_search(mock_client, "Milk")
    assert "[1] Milk" in result


async def test_stock_search_no_results(mock_client):
    mock_client.get_objects.side_effect = [
        [{"id": 1, "name": "Milk"}],
        [],
    ]
    result = await stock_search(mock_client, "Cheese")
    assert "No products found matching 'Cheese'." in result
