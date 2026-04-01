"""Core recipe management functions for Grocy."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_product, resolve_recipe


async def recipes_list(client: GrocyClient) -> str:
    """Return a formatted list of all recipes."""
    recipes = await client.get_recipes()
    if not recipes:
        return "No recipes found."
    lines = ["Recipes:"]
    for r in recipes:
        desc = r.get("description", "")
        desc_str = f" — {desc}" if desc else ""
        lines.append(f"  [{r['id']}] {r.get('name', '?')}{desc_str}")
    return "\n".join(lines)


async def recipe_details(client: GrocyClient, recipe: str) -> str:
    """Return detailed information about a recipe including ingredients."""
    recipe_id = await resolve_recipe(client, recipe)
    r = await client.get_recipe(recipe_id)
    name = r.get("name", f"Recipe {recipe_id}")
    description = r.get("description", "")

    # Fetch ingredients (recipe positions)
    positions = await client.get_objects("recipes_pos")
    recipe_positions = [p for p in positions if p.get("recipe_id") == recipe_id]

    # Build product name map for ingredients
    products = await client.get_objects("products")
    product_map = {p["id"]: p.get("name", f"Product {p['id']}") for p in products}

    lines = [f"Recipe: {name}"]
    if description:
        lines.append(f"  Description: {description}")

    if recipe_positions:
        lines.append("  Ingredients:")
        for pos in recipe_positions:
            prod_name = product_map.get(pos.get("product_id"), f"Product {pos.get('product_id')}")
            amount = pos.get("amount", "?")
            lines.append(f"    - {prod_name}: {amount}")
    else:
        lines.append("  Ingredients: none listed")

    return "\n".join(lines)


async def recipe_fulfillment(client: GrocyClient, recipe: str) -> str:
    """Check if a recipe can be fulfilled with current stock."""
    recipe_id = await resolve_recipe(client, recipe)
    fulfillment = await client.get_recipe_fulfillment(recipe_id)

    recipe_name = fulfillment.get("recipe_name", f"Recipe {recipe_id}")
    can_fulfill = not fulfillment.get("need_fulfillment", True)
    missing_count = fulfillment.get("missing_products_count", 0)

    status = (
        "can be fulfilled"
        if can_fulfill
        else f"cannot be fulfilled ({missing_count} missing product(s))"
    )
    return f"Recipe '{recipe_name}' fulfillment: {status}."


async def recipe_consume(client: GrocyClient, recipe: str) -> str:
    """Consume stock for all ingredients of a recipe."""
    recipe_id = await resolve_recipe(client, recipe)
    await client.consume_recipe(recipe_id)
    return f"Recipe '{recipe}' consumed — stock updated."


async def recipe_consume_preview(client: GrocyClient, recipe: str) -> str:
    """Preview what stock would be consumed for a recipe without actually consuming."""
    recipe_id = await resolve_recipe(client, recipe)

    # Get recipe ingredients
    positions = await client.get_objects("recipes_pos")
    recipe_positions = [p for p in positions if p.get("recipe_id") == recipe_id]

    if not recipe_positions:
        return f"Recipe '{recipe}' has no ingredients — nothing to consume."

    # Get product names and current stock
    products = await client.get_objects("products")
    product_map = {p["id"]: p.get("name", f"Product {p['id']}") for p in products}

    stock_items = await client.get_stock()
    stock_map = {}
    for s in stock_items:
        stock_map[s.get("product_id")] = s.get("amount", 0)

    lines = [f"Preview — consuming recipe '{recipe}' would deduct:"]
    for pos in recipe_positions:
        pid = pos.get("product_id")
        prod_name = product_map.get(pid, f"Product {pid}")
        needed = pos.get("amount", 0)
        in_stock = stock_map.get(pid, 0)
        status = "OK" if in_stock >= needed else f"SHORT (have {in_stock})"
        lines.append(f"  {prod_name}: {needed} — {status}")

    return "\n".join(lines)


async def recipe_add_to_shopping(client: GrocyClient, recipe: str) -> str:
    """Add missing recipe ingredients to the shopping list."""
    recipe_id = await resolve_recipe(client, recipe)
    await client.add_recipe_to_shopping_list(recipe_id)
    return f"Missing ingredients for recipe '{recipe}' added to shopping list."


async def recipe_create(
    client: GrocyClient,
    name: str,
    description: str = "",
    ingredients: list[dict] | None = None,
) -> str:
    """Create a new recipe with optional ingredients.

    Ingredients are dicts with 'product_id' and 'amount' keys.
    """
    recipe_data: dict = {"name": name}
    if description:
        recipe_data["description"] = description

    recipe_id = await client.create_object("recipes", recipe_data)

    ingredient_count = 0
    if ingredients:
        for ingredient in ingredients:
            pos_data = {"recipe_id": recipe_id, **ingredient}
            await client.create_object("recipes_pos", pos_data)
            ingredient_count += 1

    return f"Recipe '{name}' created (ID {recipe_id}) with {ingredient_count} ingredient(s)."


async def recipe_create_by_name(
    client: GrocyClient,
    name: str,
    description: str = "",
    ingredients: list[dict] | None = None,
) -> str:
    """Create a recipe with ingredients specified by product name.

    Each ingredient dict should have 'product' (name) and 'amount'.
    Product names are resolved to IDs automatically.
    """
    recipe_data: dict = {"name": name}
    if description:
        recipe_data["description"] = description

    recipe_id = await client.create_object("recipes", recipe_data)

    ingredient_count = 0
    failed: list[str] = []
    if ingredients:
        for ingredient in ingredients:
            product_name = ingredient.get("product", "")
            amount = ingredient.get("amount", 1)
            try:
                product_id = await resolve_product(client, product_name)
                pos_data = {"recipe_id": recipe_id, "product_id": product_id, "amount": amount}
                await client.create_object("recipes_pos", pos_data)
                ingredient_count += 1
            except Exception as exc:
                failed.append(f"{product_name} ({exc})")

    result = f"Recipe '{name}' created (ID {recipe_id}) with {ingredient_count} ingredient(s)."
    if failed:
        result += f"\nFailed ingredients: {', '.join(failed)}"
    return result


async def recipe_update(
    client: GrocyClient,
    recipe: str,
    name: str | None = None,
    description: str | None = None,
) -> str:
    """Update a recipe's name or description."""
    recipe_id = await resolve_recipe(client, recipe)
    data: dict = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description

    if not data:
        return "No fields to update."

    await client.update_object("recipes", recipe_id, data)
    return f"Recipe '{recipe}' updated."


async def recipe_add_ingredient(
    client: GrocyClient,
    recipe: str,
    product: str,
    amount: float = 1.0,
) -> str:
    """Add an ingredient to an existing recipe by product name."""
    recipe_id = await resolve_recipe(client, recipe)
    product_id = await resolve_product(client, product)
    pos_data = {"recipe_id": recipe_id, "product_id": product_id, "amount": amount}
    pos_id = await client.create_object("recipes_pos", pos_data)
    return f"Added '{product}' (amount {amount}) to recipe '{recipe}' (position ID {pos_id})."


async def recipe_remove_ingredient(client: GrocyClient, position_id: int) -> str:
    """Remove an ingredient from a recipe by position ID."""
    await client.delete_object("recipes_pos", position_id)
    return f"Recipe ingredient (position {position_id}) removed."
