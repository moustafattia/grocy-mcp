"""Tests for the recipes core module."""

from unittest.mock import AsyncMock, patch

import pytest

from grocy_mcp.core.recipes import (
    recipe_add_ingredient,
    recipe_add_to_shopping,
    recipe_consume,
    recipe_consume_preview,
    recipe_create,
    recipe_create_by_name,
    recipe_details,
    recipe_fulfillment,
    recipe_remove_ingredient,
    recipe_update,
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


async def test_recipe_create_with_description(mock_client):
    result = await recipe_create(mock_client, "Soup", description="Hot soup")
    mock_client.create_object.assert_called_once_with(
        "recipes", {"name": "Soup", "description": "Hot soup"}
    )
    assert "'Soup'" in result


async def test_recipe_create_no_ingredients(mock_client):
    result = await recipe_create(mock_client, "Empty Recipe")
    mock_client.create_object.assert_called_once_with("recipes", {"name": "Empty Recipe"})
    assert "0 ingredient(s)" in result


async def test_recipe_create_multiple_ingredients(mock_client):
    ingredients = [
        {"product_id": 1, "amount": 2.0},
        {"product_id": 2, "amount": 1.0},
        {"product_id": 3, "amount": 0.5},
    ]
    result = await recipe_create(mock_client, "Big Meal", ingredients=ingredients)
    assert "3 ingredient(s)" in result
    assert mock_client.create_object.call_count == 4  # 1 recipe + 3 ingredients


async def test_recipes_list_empty(mock_client):
    mock_client.get_recipes.return_value = []
    result = await recipes_list(mock_client)
    assert result == "No recipes found."


async def test_recipe_fulfillment_cannot_fulfill(mock_client):
    mock_client.get_recipe_fulfillment.return_value = {
        "recipe_id": 1,
        "recipe_name": "Pancakes",
        "need_fulfillment": True,
        "missing_products_count": 3,
    }
    with patch("grocy_mcp.core.recipes.resolve_recipe", return_value=1):
        result = await recipe_fulfillment(mock_client, "Pancakes")
        assert "cannot be fulfilled" in result
        assert "3 missing" in result


async def test_recipe_create_by_name(mock_client):
    mock_client.create_object.return_value = 10
    ingredients = [{"product": "Flour", "amount": 2}, {"product": "Egg", "amount": 3}]
    with patch("grocy_mcp.core.recipes.resolve_product", side_effect=[1, 2]):
        result = await recipe_create_by_name(mock_client, "Cake", ingredients=ingredients)
    assert "2 ingredient(s)" in result
    mock_client.create_object.assert_any_call("recipes", {"name": "Cake"})
    mock_client.create_object.assert_any_call(
        "recipes_pos", {"recipe_id": 10, "product_id": 1, "amount": 2}
    )
    mock_client.create_object.assert_any_call(
        "recipes_pos", {"recipe_id": 10, "product_id": 2, "amount": 3}
    )


async def test_recipe_update(mock_client):
    with patch("grocy_mcp.core.recipes.resolve_recipe", return_value=1):
        result = await recipe_update(mock_client, "Pancakes", name="Super Pancakes")
    mock_client.update_object.assert_called_once_with("recipes", 1, {"name": "Super Pancakes"})
    assert "updated" in result.lower()


async def test_recipe_update_no_fields(mock_client):
    with patch("grocy_mcp.core.recipes.resolve_recipe", return_value=1):
        result = await recipe_update(mock_client, "Pancakes")
    assert "No fields" in result


async def test_recipe_add_ingredient(mock_client):
    mock_client.create_object.return_value = 20
    with (
        patch("grocy_mcp.core.recipes.resolve_recipe", return_value=1),
        patch("grocy_mcp.core.recipes.resolve_product", return_value=5),
    ):
        result = await recipe_add_ingredient(mock_client, "Pancakes", "Flour", 2.0)
    mock_client.create_object.assert_called_once_with(
        "recipes_pos", {"recipe_id": 1, "product_id": 5, "amount": 2.0}
    )
    assert "'Flour'" in result
    assert "'Pancakes'" in result


async def test_recipe_remove_ingredient(mock_client):
    result = await recipe_remove_ingredient(mock_client, 42)
    mock_client.delete_object.assert_called_once_with("recipes_pos", 42)
    assert "42" in result


async def test_recipe_consume_preview(mock_client):
    mock_client.get_objects.side_effect = [
        # recipes_pos
        [
            {"recipe_id": 1, "product_id": 1, "amount": 2},
            {"recipe_id": 1, "product_id": 2, "amount": 1},
        ],
        # products
        [{"id": 1, "name": "Flour"}, {"id": 2, "name": "Egg"}],
    ]
    mock_client.get_stock.return_value = [
        {"product_id": 1, "amount": 5},
        {"product_id": 2, "amount": 0},
    ]
    with patch("grocy_mcp.core.recipes.resolve_recipe", return_value=1):
        result = await recipe_consume_preview(mock_client, "Pancakes")
    assert "Flour" in result
    assert "OK" in result
    assert "SHORT" in result
    assert "Preview" in result
