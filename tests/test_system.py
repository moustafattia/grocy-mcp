"""Tests for the system core module."""

from unittest.mock import AsyncMock

import pytest

from grocy_mcp.core.system import entity_list, entity_manage, system_info


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_system_info.return_value = {
        "grocy_version": {"Version": "3.3.2"},
        "php_version": "8.1.0",
        "sqlite_version": "3.39.0",
    }
    client.get_objects.return_value = [
        {"id": 1, "name": "Item A"},
        {"id": 2, "name": "Item B"},
    ]
    client.create_object.return_value = 42
    client.update_object.return_value = None
    client.delete_object.return_value = None
    return client


async def test_system_info(mock_client):
    result = await system_info(mock_client)
    assert "3.3.2" in result


async def test_entity_list(mock_client):
    result = await entity_list(mock_client, "products")
    assert "Item A" in result
    assert "Item B" in result
    mock_client.get_objects.assert_called_once_with("products")


async def test_entity_list_empty(mock_client):
    mock_client.get_objects.return_value = []
    result = await entity_list(mock_client, "products")
    assert "no" in result.lower() or "empty" in result.lower() or "0" in result


async def test_entity_manage_create(mock_client):
    result = await entity_manage(mock_client, "products", "create", data={"name": "Cheese"})
    mock_client.create_object.assert_called_once_with("products", {"name": "Cheese"})
    assert "42" in result or "created" in result.lower()


async def test_entity_manage_update(mock_client):
    result = await entity_manage(mock_client, "products", "update", obj_id=1, data={"name": "New"})
    mock_client.update_object.assert_called_once_with("products", 1, {"name": "New"})
    assert result


async def test_entity_manage_delete(mock_client):
    result = await entity_manage(mock_client, "products", "delete", obj_id=1)
    mock_client.delete_object.assert_called_once_with("products", 1)
    assert result


async def test_entity_manage_unknown_action(mock_client):
    result = await entity_manage(mock_client, "products", "explode")
    assert "unknown" in result.lower() or "invalid" in result.lower()
