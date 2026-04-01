"""Typer CLI application for Grocy MCP."""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import typer

from grocy_mcp.client import GrocyClient
from grocy_mcp.config import load_config
from grocy_mcp.core.chores import chore_create, chore_execute, chore_undo, chores_list, chores_overdue
from grocy_mcp.core.recipes import (
    recipe_add_to_shopping,
    recipe_consume,
    recipe_create,
    recipe_details,
    recipe_fulfillment,
    recipes_list,
)
from grocy_mcp.core.shopping import (
    shopping_list_add,
    shopping_list_add_missing,
    shopping_list_clear,
    shopping_list_remove,
    shopping_list_update,
    shopping_list_view,
)
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
from grocy_mcp.core.system import entity_list, entity_manage, system_info
from grocy_mcp.exceptions import GrocyError

app = typer.Typer(help="Grocy CLI — manage stock, shopping lists, recipes and chores.")
stock_app = typer.Typer(help="Stock management commands.")
shopping_app = typer.Typer(help="Shopping list commands.")
recipes_app = typer.Typer(help="Recipe commands.")
chores_app = typer.Typer(help="Chore commands.")
system_app = typer.Typer(help="System information commands.")
entity_app = typer.Typer(help="Generic entity management commands.")

app.add_typer(stock_app, name="stock")
app.add_typer(shopping_app, name="shopping")
app.add_typer(recipes_app, name="recipes")
app.add_typer(chores_app, name="chores")
app.add_typer(system_app, name="system")
app.add_typer(entity_app, name="entity")


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _exec(coro) -> None:
    """Run the coroutine, print the result, and catch GrocyError."""
    try:
        result = _run(coro)
        typer.echo(result)
    except GrocyError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def _client() -> GrocyClient:
    """Create a GrocyClient from the current configuration."""
    config = load_config()
    return GrocyClient(config.url, config.api_key)


@app.callback()
def main_callback() -> None:
    """Grocy CLI — control your Grocy instance from the command line."""


# -------------------------------------------------------------------- Stock

@stock_app.command("overview")
def cmd_stock_overview() -> None:
    """Show all products currently in stock."""
    async def _inner():
        async with _client() as client:
            return await stock_overview(client)
    _exec(_inner())


@stock_app.command("expiring")
def cmd_stock_expiring() -> None:
    """Show expiring, expired, and missing products."""
    async def _inner():
        async with _client() as client:
            return await stock_expiring(client)
    _exec(_inner())


@stock_app.command("info")
def cmd_stock_product_info(product: str = typer.Argument(..., help="Product name or ID.")) -> None:
    """Show detailed stock information for a product."""
    async def _inner():
        async with _client() as client:
            return await stock_product_info(client, product)
    _exec(_inner())


@stock_app.command("add")
def cmd_stock_add(
    product: str = typer.Argument(..., help="Product name or ID."),
    amount: float = typer.Argument(..., help="Quantity to add."),
) -> None:
    """Add stock for a product."""
    async def _inner():
        async with _client() as client:
            return await stock_add(client, product, amount)
    _exec(_inner())


@stock_app.command("consume")
def cmd_stock_consume(
    product: str = typer.Argument(..., help="Product name or ID."),
    amount: float = typer.Argument(..., help="Quantity to consume."),
) -> None:
    """Consume stock for a product."""
    async def _inner():
        async with _client() as client:
            return await stock_consume(client, product, amount)
    _exec(_inner())


@stock_app.command("transfer")
def cmd_stock_transfer(
    product: str = typer.Argument(..., help="Product name or ID."),
    amount: float = typer.Argument(..., help="Quantity to transfer."),
    to_location: str = typer.Argument(..., help="Destination location name or ID."),
) -> None:
    """Transfer stock to a different location."""
    async def _inner():
        async with _client() as client:
            return await stock_transfer(client, product, amount, to_location)
    _exec(_inner())


@stock_app.command("inventory")
def cmd_stock_inventory(
    product: str = typer.Argument(..., help="Product name or ID."),
    new_amount: float = typer.Argument(..., help="New total stock quantity."),
) -> None:
    """Set stock amount for a product via inventory adjustment."""
    async def _inner():
        async with _client() as client:
            return await stock_inventory(client, product, new_amount)
    _exec(_inner())


@stock_app.command("open")
def cmd_stock_open(
    product: str = typer.Argument(..., help="Product name or ID."),
    amount: float = typer.Argument(1.0, help="Quantity to mark as opened."),
) -> None:
    """Mark stock as opened for a product."""
    async def _inner():
        async with _client() as client:
            return await stock_open(client, product, amount)
    _exec(_inner())


@stock_app.command("search")
def cmd_stock_search(query: str = typer.Argument(..., help="Search query.")) -> None:
    """Search for products by name or barcode."""
    async def _inner():
        async with _client() as client:
            return await stock_search(client, query)
    _exec(_inner())


@stock_app.command("barcode")
def cmd_stock_barcode_lookup(barcode: str = typer.Argument(..., help="Barcode to look up.")) -> None:
    """Look up stock information by barcode."""
    async def _inner():
        async with _client() as client:
            return await stock_barcode_lookup(client, barcode)
    _exec(_inner())


# ------------------------------------------------------------------ Shopping

@shopping_app.command("view")
def cmd_shopping_view(
    list_id: int = typer.Option(1, "--list-id", help="Shopping list ID."),
) -> None:
    """View the shopping list."""
    async def _inner():
        async with _client() as client:
            return await shopping_list_view(client, list_id)
    _exec(_inner())


@shopping_app.command("add")
def cmd_shopping_add(
    product: str = typer.Argument(..., help="Product name or ID."),
    amount: float = typer.Option(1.0, "--amount", help="Quantity to add."),
    list_id: int = typer.Option(1, "--list-id", help="Shopping list ID."),
    note: Optional[str] = typer.Option(None, "--note", help="Optional note."),
) -> None:
    """Add a product to the shopping list."""
    async def _inner():
        async with _client() as client:
            return await shopping_list_add(client, product, amount, list_id, note)
    _exec(_inner())


@shopping_app.command("update")
def cmd_shopping_update(
    item_id: int = typer.Argument(..., help="Shopping list item ID."),
    data: str = typer.Argument(..., help='JSON string of fields to update (e.g. \'{"amount": 3}\').'),
) -> None:
    """Update a shopping list item."""
    async def _inner():
        async with _client() as client:
            return await shopping_list_update(client, item_id, json.loads(data))
    _exec(_inner())


@shopping_app.command("remove")
def cmd_shopping_remove(
    item_id: int = typer.Argument(..., help="Shopping list item ID to remove."),
) -> None:
    """Remove an item from the shopping list."""
    async def _inner():
        async with _client() as client:
            return await shopping_list_remove(client, item_id)
    _exec(_inner())


@shopping_app.command("clear")
def cmd_shopping_clear(
    list_id: int = typer.Option(1, "--list-id", help="Shopping list ID to clear."),
) -> None:
    """Clear all items from the shopping list."""
    async def _inner():
        async with _client() as client:
            return await shopping_list_clear(client, list_id)
    _exec(_inner())


@shopping_app.command("add-missing")
def cmd_shopping_add_missing(
    list_id: int = typer.Option(1, "--list-id", help="Shopping list ID."),
) -> None:
    """Add all below-minimum-stock products to the shopping list."""
    async def _inner():
        async with _client() as client:
            return await shopping_list_add_missing(client, list_id)
    _exec(_inner())


# ------------------------------------------------------------------- Recipes

@recipes_app.command("list")
def cmd_recipes_list() -> None:
    """List all recipes."""
    async def _inner():
        async with _client() as client:
            return await recipes_list(client)
    _exec(_inner())


@recipes_app.command("details")
def cmd_recipe_details(recipe: str = typer.Argument(..., help="Recipe name or ID.")) -> None:
    """Show details and ingredients for a recipe."""
    async def _inner():
        async with _client() as client:
            return await recipe_details(client, recipe)
    _exec(_inner())


@recipes_app.command("fulfillment")
def cmd_recipe_fulfillment(recipe: str = typer.Argument(..., help="Recipe name or ID.")) -> None:
    """Check if a recipe can be fulfilled with current stock."""
    async def _inner():
        async with _client() as client:
            return await recipe_fulfillment(client, recipe)
    _exec(_inner())


@recipes_app.command("consume")
def cmd_recipe_consume(recipe: str = typer.Argument(..., help="Recipe name or ID.")) -> None:
    """Consume stock for all ingredients of a recipe."""
    async def _inner():
        async with _client() as client:
            return await recipe_consume(client, recipe)
    _exec(_inner())


@recipes_app.command("add-to-shopping")
def cmd_recipe_add_to_shopping(recipe: str = typer.Argument(..., help="Recipe name or ID.")) -> None:
    """Add missing recipe ingredients to the shopping list."""
    async def _inner():
        async with _client() as client:
            return await recipe_add_to_shopping(client, recipe)
    _exec(_inner())


@recipes_app.command("create")
def cmd_recipe_create(
    name: str = typer.Argument(..., help="Recipe name."),
    description: str = typer.Option("", "--description", help="Recipe description."),
    ingredients: str = typer.Option(
        "[]", "--ingredients", help='JSON list of ingredients (e.g. \'[{"product_id": 1, "amount": 2}]\').'
    ),
) -> None:
    """Create a new recipe."""
    parsed = json.loads(ingredients)

    async def _inner():
        async with _client() as client:
            return await recipe_create(client, name, description, parsed or None)
    _exec(_inner())


# -------------------------------------------------------------------- Chores

@chores_app.command("list")
def cmd_chores_list() -> None:
    """List all chores."""
    async def _inner():
        async with _client() as client:
            return await chores_list(client)
    _exec(_inner())


@chores_app.command("overdue")
def cmd_chores_overdue() -> None:
    """Show overdue chores."""
    async def _inner():
        async with _client() as client:
            return await chores_overdue(client)
    _exec(_inner())


@chores_app.command("execute")
def cmd_chore_execute(
    chore: str = typer.Argument(..., help="Chore name or ID."),
    done_by: Optional[int] = typer.Option(None, "--done-by", help="User ID who completed the chore."),
) -> None:
    """Mark a chore as done."""
    async def _inner():
        async with _client() as client:
            return await chore_execute(client, chore, done_by)
    _exec(_inner())


@chores_app.command("undo")
def cmd_chore_undo(chore: str = typer.Argument(..., help="Chore name or ID.")) -> None:
    """Undo the most recent execution of a chore."""
    async def _inner():
        async with _client() as client:
            return await chore_undo(client, chore)
    _exec(_inner())


@chores_app.command("create")
def cmd_chore_create(name: str = typer.Argument(..., help="Chore name.")) -> None:
    """Create a new chore."""
    async def _inner():
        async with _client() as client:
            return await chore_create(client, name)
    _exec(_inner())


# -------------------------------------------------------------------- System

@system_app.command("info")
def cmd_system_info() -> None:
    """Show Grocy system information."""
    async def _inner():
        async with _client() as client:
            return await system_info(client)
    _exec(_inner())


# ------------------------------------------------------------------- Entity

@entity_app.command("list")
def cmd_entity_list(entity: str = typer.Argument(..., help="Entity type (e.g. 'products').")) -> None:
    """List all objects of a Grocy entity type."""
    async def _inner():
        async with _client() as client:
            return await entity_list(client, entity)
    _exec(_inner())


@entity_app.command("manage")
def cmd_entity_manage(
    entity: str = typer.Argument(..., help="Entity type (e.g. 'products')."),
    action: str = typer.Argument(..., help="Action: create, update, or delete."),
    obj_id: Optional[int] = typer.Option(None, "--id", help="Object ID (required for update/delete)."),
    data: str = typer.Option("{}", "--data", help='JSON string of fields (e.g. \'{"name": "Pantry"}\').'),
) -> None:
    """Create, update, or delete a Grocy entity object."""
    parsed = json.loads(data)

    async def _inner():
        async with _client() as client:
            return await entity_manage(client, entity, action, obj_id, parsed or None)
    _exec(_inner())


def main() -> None:
    """Entry point for the grocy CLI."""
    app()
