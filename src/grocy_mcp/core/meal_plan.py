"""Core meal plan management functions for Grocy."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_recipe


async def meal_plan_list(client: GrocyClient) -> str:
    """Return a formatted list of meal plan entries."""
    entries = await client.get_objects("meal_plan")
    if not entries:
        return "No meal plan entries found."

    # Build recipe name map
    recipes = await client.get_objects("recipes")
    recipe_map = {r["id"]: r.get("name", f"Recipe {r['id']}") for r in recipes}

    # Sort by day
    entries.sort(key=lambda e: e.get("day", ""))

    lines = ["Meal plan:"]
    for entry in entries:
        day = entry.get("day", "?")
        recipe_id = entry.get("recipe_id")
        recipe_name = recipe_map.get(recipe_id, "")
        meal_type = entry.get("type", "")
        note = entry.get("note", "")

        parts = [f"  [{entry['id']}] {day}"]
        if meal_type:
            parts.append(f"({meal_type})")
        if recipe_name:
            parts.append(f"— {recipe_name}")
        if note:
            parts.append(f"— {note}")

        lines.append(" ".join(parts))

    return "\n".join(lines)


async def meal_plan_add(
    client: GrocyClient,
    day: str,
    recipe: str | None = None,
    note: str = "",
    meal_type: str = "",
) -> str:
    """Add an entry to the meal plan."""
    data: dict = {"day": day}

    if recipe is not None:
        recipe_id = await resolve_recipe(client, recipe)
        data["recipe_id"] = recipe_id
        data["type"] = meal_type or "recipe"
    else:
        data["type"] = meal_type or "note"

    if note:
        data["note"] = note

    entry_id = await client.create_object("meal_plan", data)
    label = f"recipe '{recipe}'" if recipe else f"note '{note}'"
    return f"Meal plan entry added for {day}: {label} (ID {entry_id})."


async def meal_plan_remove(client: GrocyClient, entry_id: int) -> str:
    """Remove a meal plan entry."""
    await client.delete_object("meal_plan", entry_id)
    return f"Meal plan entry {entry_id} removed."


async def meal_plan_shopping(
    client: GrocyClient,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Add missing ingredients for all planned recipes to the shopping list.

    Optionally filter by date range (YYYY-MM-DD). For each recipe in the meal
    plan, calls Grocy's add-not-fulfilled endpoint to add only what's missing.
    """
    entries = await client.get_objects("meal_plan")
    if not entries:
        return "No meal plan entries found."

    # Filter by date range
    if start_date:
        entries = [e for e in entries if e.get("day", "") >= start_date]
    if end_date:
        entries = [e for e in entries if e.get("day", "") <= end_date]

    # Collect unique recipe IDs
    recipe_ids = {e["recipe_id"] for e in entries if e.get("recipe_id")}
    if not recipe_ids:
        return "No recipes found in the selected meal plan entries."

    # Build recipe name map
    recipes = await client.get_objects("recipes")
    recipe_map = {r["id"]: r.get("name", f"Recipe {r['id']}") for r in recipes}

    added = []
    for rid in sorted(recipe_ids):
        await client.add_recipe_to_shopping_list(rid)
        added.append(recipe_map.get(rid, f"Recipe {rid}"))

    lines = [f"Added missing ingredients for {len(added)} recipe(s) to shopping list:"]
    for name in added:
        lines.append(f"  — {name}")

    return "\n".join(lines)
