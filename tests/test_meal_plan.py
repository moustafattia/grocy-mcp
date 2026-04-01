"""Tests for the meal plan core module."""

from unittest.mock import AsyncMock, patch

from grocy_mcp.core.meal_plan import (
    meal_plan_add,
    meal_plan_list,
    meal_plan_remove,
    meal_plan_shopping,
)


async def test_meal_plan_list():
    client = AsyncMock()
    client.get_objects.side_effect = [
        # meal_plan
        [
            {"id": 1, "day": "2026-04-05", "recipe_id": 1, "type": "recipe", "note": ""},
            {"id": 2, "day": "2026-04-06", "recipe_id": None, "type": "note", "note": "Eat out"},
        ],
        # recipes
        [{"id": 1, "name": "Pancakes"}],
    ]
    result = await meal_plan_list(client)
    assert "2026-04-05" in result
    assert "Pancakes" in result
    assert "Eat out" in result
    assert "[1]" in result
    assert "[2]" in result


async def test_meal_plan_list_empty():
    client = AsyncMock()
    client.get_objects.return_value = []
    result = await meal_plan_list(client)
    assert result == "No meal plan entries found."


async def test_meal_plan_add_recipe():
    client = AsyncMock()
    client.create_object.return_value = 10
    with patch("grocy_mcp.core.meal_plan.resolve_recipe", return_value=5):
        result = await meal_plan_add(client, "2026-04-07", recipe="Pancakes")
    client.create_object.assert_called_once_with(
        "meal_plan", {"day": "2026-04-07", "recipe_id": 5, "type": "recipe"}
    )
    assert "2026-04-07" in result
    assert "'Pancakes'" in result


async def test_meal_plan_add_note():
    client = AsyncMock()
    client.create_object.return_value = 11
    result = await meal_plan_add(client, "2026-04-08", note="Leftovers")
    client.create_object.assert_called_once_with(
        "meal_plan", {"day": "2026-04-08", "type": "note", "note": "Leftovers"}
    )
    assert "2026-04-08" in result
    assert "'Leftovers'" in result


async def test_meal_plan_remove():
    client = AsyncMock()
    result = await meal_plan_remove(client, 3)
    client.delete_object.assert_called_once_with("meal_plan", 3)
    assert "3" in result
    assert "removed" in result.lower()


async def test_meal_plan_shopping():
    client = AsyncMock()
    client.get_objects.side_effect = [
        # meal_plan entries
        [
            {"id": 1, "day": "2026-04-05", "recipe_id": 1, "type": "recipe"},
            {"id": 2, "day": "2026-04-06", "recipe_id": 2, "type": "recipe"},
            {"id": 3, "day": "2026-04-06", "recipe_id": None, "type": "note"},
        ],
        # recipes
        [{"id": 1, "name": "Pancakes"}, {"id": 2, "name": "Omelette"}],
    ]
    client.add_recipe_to_shopping_list.return_value = None
    result = await meal_plan_shopping(client)
    assert client.add_recipe_to_shopping_list.call_count == 2
    assert "Pancakes" in result
    assert "Omelette" in result
    assert "2 recipe(s)" in result


async def test_meal_plan_shopping_date_filter():
    client = AsyncMock()
    client.get_objects.side_effect = [
        [
            {"id": 1, "day": "2026-04-05", "recipe_id": 1, "type": "recipe"},
            {"id": 2, "day": "2026-04-10", "recipe_id": 2, "type": "recipe"},
        ],
        [{"id": 1, "name": "Pancakes"}, {"id": 2, "name": "Omelette"}],
    ]
    client.add_recipe_to_shopping_list.return_value = None
    result = await meal_plan_shopping(client, start_date="2026-04-06", end_date="2026-04-12")
    # Only recipe 2 should be included (day 2026-04-10 is in range)
    assert client.add_recipe_to_shopping_list.call_count == 1
    assert "1 recipe(s)" in result


async def test_meal_plan_shopping_no_recipes():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "day": "2026-04-05", "recipe_id": None, "type": "note", "note": "Eat out"},
    ]
    result = await meal_plan_shopping(client)
    assert "No recipes found" in result
