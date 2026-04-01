"""Tests for the recipes core module."""

from unittest.mock import AsyncMock, patch

import pytest

from grocy_mcp.core.recipes import (
    recipe_add_to_shopping,
    recipe_consume,
    recipe_create,
    recipe_details,
    recipe_fulfillment,
    recipes_list,
)


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_recipes.return_value = [
        {"id": 1, "name": "Pancakes", "description": "Fluffy pancakes"},
        {"id": 2, "name": "Omelette", "description": "Quick omelette"},
    ]
    client.get_recipe.return_value = {"id": 1, "name": "Pancakes", "description": "Fluffy pancakes"}
    client.get_recipe_fulfillment.return_value = {
        "recipe_id": 1,
        "recipe_name": "Pancakes",
        "need_fulfillment": False,
        "missing_products_count": 0,
    }
    client.get_objects.return_value = []
    client.create_object.return_value = 10
    client.consume_recipe.return_value = None
    client.add_recipe_to_shopping_list.return_value = None
    return client


async def test_recipes_list(mock_client):
    result = await recipes_list(mock_client)
    assert "Pancakes" in result
    assert "Omelette" in result


async def test_recipe_details(mock_client):
    with patch("grocy_mcp.core.recipes.resolve_recipe", return_value=1):
        result = await recipe_details(mock_client, "Pancakes")
        mock_client.get_recipe.assert_called_once_with(1)
        assert "Pancakes" in result


async def test_recipe_fulfillment(mock_client):
    with patch("grocy_mcp.core.recipes.resolve_recipe", return_value=1):
        result = await recipe_fulfillment(mock_client, "Pancakes")
        mock_client.get_recipe_fulfillment.assert_called_once_with(1)
        assert "Pancakes" in result or "fulfillment" in result.lower() or "1" in result


async def test_recipe_consume(mock_client):
    with patch("grocy_mcp.core.recipes.resolve_recipe", return_value=1):
        result = await recipe_consume(mock_client, "Pancakes")
        mock_client.consume_recipe.assert_called_once_with(1)
        assert result


async def test_recipe_add_to_shopping(mock_client):
    with patch("grocy_mcp.core.recipes.resolve_recipe", return_value=1):
        result = await recipe_add_to_shopping(mock_client, "Pancakes")
        mock_client.add_recipe_to_shopping_list.assert_called_once_with(1)
        assert result


async def test_recipe_create(mock_client):
    ingredients = [{"product_id": 1, "amount": 2.0}]
    result = await recipe_create(mock_client, "New Recipe", ingredients=ingredients)
    # Should create the recipe object
    mock_client.create_object.assert_any_call("recipes", {"name": "New Recipe"})
    # Should create each ingredient position
    mock_client.create_object.assert_any_call(
        "recipes_pos", {"recipe_id": 10, "product_id": 1, "amount": 2.0}
    )
    assert result
