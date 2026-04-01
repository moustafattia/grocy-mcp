"""Core meal plan management functions for Grocy."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_recipe


def _meal_plan_section_id(entry: dict) -> int | None:
    for field in ("meal_plan_section_id", "section_id"):
        value = entry.get(field)
        if value is not None:
            return int(value)
    return None


async def meal_plan_list(client: GrocyClient) -> str:
    """Return a formatted list of meal plan entries."""
    entries = await client.get_objects("meal_plan")
    if not entries:
        return "No meal plan entries found."

    recipes = await client.get_objects("recipes")
    sections = await client.get_objects("meal_plan_sections")
    recipe_map = {recipe["id"]: recipe.get("name", f"Recipe {recipe['id']}") for recipe in recipes}
    section_map = {
        section["id"]: section.get("name", f"Section {section['id']}") for section in sections
    }

    entries.sort(key=lambda entry: entry.get("day", ""))

    lines = ["Meal plan:"]
    for entry in entries:
        day = entry.get("day", "?")
        recipe_id = entry.get("recipe_id")
        recipe_name = recipe_map.get(recipe_id, "")
        meal_type = entry.get("type", "")
        note = entry.get("note", "")
        section_name = section_map.get(_meal_plan_section_id(entry))

        parts = [f"  [{entry['id']}] {day}"]
        if meal_type:
            parts.append(f"({meal_type})")
        if recipe_name:
            parts.append(f"— {recipe_name}")
        if section_name:
            parts.append(f"[{section_name}]")
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
    """Add missing ingredients for all planned recipes to the shopping list."""
    entries = await client.get_objects("meal_plan")
    if not entries:
        return "No meal plan entries found."

    if start_date:
        entries = [entry for entry in entries if entry.get("day", "") >= start_date]
    if end_date:
        entries = [entry for entry in entries if entry.get("day", "") <= end_date]

    recipe_ids = {entry["recipe_id"] for entry in entries if entry.get("recipe_id")}
    if not recipe_ids:
        return "No recipes found in the selected meal plan entries."

    recipes = await client.get_objects("recipes")
    recipe_map = {recipe["id"]: recipe.get("name", f"Recipe {recipe['id']}") for recipe in recipes}

    added = []
    for recipe_id in sorted(recipe_ids):
        await client.add_recipe_to_shopping_list(recipe_id)
        added.append(recipe_map.get(recipe_id, f"Recipe {recipe_id}"))

    lines = [f"Added missing ingredients for {len(added)} recipe(s) to shopping list:"]
    for name in added:
        lines.append(f"  — {name}")

    return "\n".join(lines)


async def meal_plan_summary_data(
    client: GrocyClient,
    start_date: str | None = None,
    end_date: str | None = None,
    section_id: int | None = None,
) -> dict:
    """Return a structured meal-plan summary with recipe and section names."""
    entries = await client.get_objects("meal_plan")
    recipes = await client.get_objects("recipes")
    sections = await client.get_objects("meal_plan_sections")

    if start_date:
        entries = [entry for entry in entries if entry.get("day", "") >= start_date]
    if end_date:
        entries = [entry for entry in entries if entry.get("day", "") <= end_date]
    if section_id is not None:
        entries = [entry for entry in entries if _meal_plan_section_id(entry) == section_id]

    recipe_map = {recipe["id"]: recipe.get("name", f"Recipe {recipe['id']}") for recipe in recipes}
    section_map = {
        section["id"]: section.get("name", f"Section {section['id']}") for section in sections
    }

    result_entries = []
    for entry in sorted(entries, key=lambda item: (item.get("day", ""), item.get("id", 0))):
        current_section_id = _meal_plan_section_id(entry)
        result_entries.append(
            {
                **entry,
                "recipe_name": recipe_map.get(entry.get("recipe_id")),
                "section_name": section_map.get(current_section_id),
            }
        )

    return {
        "window": {"from": start_date, "to": end_date},
        "section_id": section_id,
        "entries": result_entries,
    }


async def meal_plan_summary(
    client: GrocyClient,
    start_date: str | None = None,
    end_date: str | None = None,
    section_id: int | None = None,
) -> str:
    """Return a human-readable meal-plan summary."""
    data = await meal_plan_summary_data(client, start_date, end_date, section_id)
    entries = data["entries"]
    if not entries:
        return "No meal plan entries found for the selected window."

    lines = ["Meal plan summary:"]
    if start_date or end_date:
        lines.append(f"  window: {start_date or 'open'} -> {end_date or 'open'}")
    if section_id is not None:
        lines.append(f"  section_id: {section_id}")
    for entry in entries:
        label = entry.get("recipe_name") or entry.get("note") or entry.get("type") or "entry"
        section_name = entry.get("section_name")
        section_suffix = f" [{section_name}]" if section_name else ""
        lines.append(f"  [{entry.get('id')}] {entry.get('day')} — {label}{section_suffix}")
    return "\n".join(lines)
