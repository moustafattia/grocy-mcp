"""Typer CLI application for Grocy MCP."""

from __future__ import annotations

import asyncio
import json

import typer

from grocy_mcp.client import GrocyClient
from grocy_mcp.config import load_config
from grocy_mcp.core.chores import (
    chore_create,
    chore_execute,
    chore_undo,
    chores_list,
    chores_overdue,
)
from grocy_mcp.core.recipes import (
    recipe_add_ingredient,
    recipe_add_to_shopping,
    recipe_consume,
    recipe_consume_preview,
    recipe_create,
    recipe_details,
    recipe_fulfillment,
    recipe_remove_ingredient,
    recipe_update,
    recipes_list,
)
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
from grocy_mcp.core.locations import location_create, locations_list
from grocy_mcp.core.meal_plan import (
    meal_plan_add,
    meal_plan_list,
    meal_plan_remove,
    meal_plan_shopping,
)
from grocy_mcp.core.stock_journal import stock_journal
from grocy_mcp.core.system import entity_list, entity_manage, system_info
from grocy_mcp.core.tasks import task_complete, task_create, task_delete, tasks_list
from grocy_mcp.exceptions import GrocyError

app = typer.Typer(help="Grocy CLI — manage stock, shopping lists, recipes and chores.")
stock_app = typer.Typer(help="Stock management commands.")
shopping_app = typer.Typer(help="Shopping list commands.")
recipes_app = typer.Typer(help="Recipe commands.")
chores_app = typer.Typer(help="Chore commands.")
locations_app = typer.Typer(help="Storage location commands.")
tasks_app = typer.Typer(help="Task management commands.")
meal_plan_app = typer.Typer(help="Meal plan commands.")
system_app = typer.Typer(help="System information commands.")
entity_app = typer.Typer(help="Generic entity management commands.")

app.add_typer(stock_app, name="stock")
app.add_typer(shopping_app, name="shopping")
app.add_typer(recipes_app, name="recipes")
app.add_typer(chores_app, name="chores")
app.add_typer(locations_app, name="locations")
app.add_typer(tasks_app, name="tasks")
app.add_typer(meal_plan_app, name="meal-plan")
app.add_typer(system_app, name="system")
app.add_typer(entity_app, name="entity")

# Global state set by the app callback.
_cli_url: str | None = None
_cli_api_key: str | None = None
_output_json: bool = False


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _exec(coro) -> None:
    """Run the coroutine, print the result, and catch GrocyError."""
    try:
        result = _run(coro)
        typer.echo(result)
    except GrocyError as e:
        if _output_json:
            typer.echo(json.dumps({"error": str(e)}))
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def _exec_json(coro) -> None:
    """Run the coroutine and print the result as a JSON string."""
    try:
        result = _run(coro)
        typer.echo(json.dumps(result, default=str))
    except GrocyError as e:
        typer.echo(json.dumps({"error": str(e)}))
        raise typer.Exit(1)


def _client() -> GrocyClient:
    """Create a GrocyClient from the current configuration."""
    config = load_config(url=_cli_url, api_key=_cli_api_key)
    return GrocyClient(config.url, config.api_key)


def _parse_json(value: str, label: str) -> dict | list:
    """Parse a JSON string with a clear error on failure."""
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: invalid JSON for {label}: {e}", err=True)
        raise typer.Exit(2) from e


@app.callback()
def main_callback(
    url: str | None = typer.Option(None, "--url", envvar="GROCY_URL", help="Grocy instance URL."),
    api_key: str | None = typer.Option(
        None, "--api-key", envvar="GROCY_API_KEY", help="Grocy API key."
    ),
    output_json: bool = typer.Option(
        False, "--json", help="Output raw JSON instead of formatted text."
    ),
) -> None:
    """Grocy CLI — control your Grocy instance from the command line."""
    global _cli_url, _cli_api_key, _output_json  # noqa: PLW0603
    _cli_url = url
    _cli_api_key = api_key
    _output_json = output_json


# -------------------------------------------------------------------- Stock


@stock_app.command("overview", rich_help_panel="View")
def cmd_stock_overview() -> None:
    """Show all products currently in stock."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_stock()

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await stock_overview(client)

        _exec(_inner())


@stock_app.command("expiring", rich_help_panel="View")
def cmd_stock_expiring() -> None:
    """Show expiring, expired, and missing products."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_volatile_stock()

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await stock_expiring(client)

        _exec(_inner())


@stock_app.command("info", rich_help_panel="View")
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


@stock_app.command("search", rich_help_panel="View")
def cmd_stock_search(query: str = typer.Argument(..., help="Search query.")) -> None:
    """Search for products by name or barcode."""

    async def _inner():
        async with _client() as client:
            return await stock_search(client, query)

    _exec(_inner())


@stock_app.command("barcode", rich_help_panel="View")
def cmd_stock_barcode_lookup(
    barcode: str = typer.Argument(..., help="Barcode to look up."),
) -> None:
    """Look up stock information by barcode."""

    async def _inner():
        async with _client() as client:
            return await stock_barcode_lookup(client, barcode)

    _exec(_inner())


# ------------------------------------------------------------------ Shopping


@shopping_app.command("view")
def cmd_shopping_view(
    list_id: int = typer.Option(1, "--list-id", "-l", help="Shopping list ID."),
) -> None:
    """View the shopping list."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_shopping_list(list_id)

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await shopping_list_view(client, list_id)

        _exec(_inner())


@shopping_app.command("add")
def cmd_shopping_add(
    product: str = typer.Argument(..., help="Product name or ID."),
    amount: float = typer.Option(1.0, "--amount", "-a", help="Quantity to add."),
    list_id: int = typer.Option(1, "--list-id", "-l", help="Shopping list ID."),
    note: str | None = typer.Option(None, "--note", "-n", help="Optional note."),
) -> None:
    """Add a product to the shopping list."""

    async def _inner():
        async with _client() as client:
            return await shopping_list_add(client, product, amount, list_id, note)

    _exec(_inner())


@shopping_app.command("update")
def cmd_shopping_update(
    item_id: int = typer.Argument(..., help="Shopping list item ID."),
    data: str = typer.Argument(..., help="JSON fields to update, e.g. '{\"amount\": 3}'."),
) -> None:
    """Update a shopping list item."""
    parsed = _parse_json(data, "--data")

    async def _inner():
        async with _client() as client:
            return await shopping_list_update(client, item_id, parsed)

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
    list_id: int = typer.Option(1, "--list-id", "-l", help="Shopping list ID to clear."),
) -> None:
    """Clear all items from the shopping list."""

    async def _inner():
        async with _client() as client:
            return await shopping_list_clear(client, list_id)

    _exec(_inner())


@shopping_app.command("add-missing")
def cmd_shopping_add_missing(
    list_id: int = typer.Option(1, "--list-id", "-l", help="Shopping list ID."),
) -> None:
    """Add all below-minimum-stock products to the shopping list."""

    async def _inner():
        async with _client() as client:
            return await shopping_list_add_missing(client, list_id)

    _exec(_inner())


@shopping_app.command("set-amount")
def cmd_shopping_set_amount(
    item_id: int = typer.Argument(..., help="Shopping list item ID."),
    amount: float = typer.Argument(..., help="New quantity."),
) -> None:
    """Set the quantity for a shopping list item."""

    async def _inner():
        async with _client() as client:
            return await shopping_list_set_amount(client, item_id, amount)

    _exec(_inner())


@shopping_app.command("set-note")
def cmd_shopping_set_note(
    item_id: int = typer.Argument(..., help="Shopping list item ID."),
    note: str = typer.Argument(..., help="New note text."),
) -> None:
    """Set or update the note on a shopping list item."""

    async def _inner():
        async with _client() as client:
            return await shopping_list_set_note(client, item_id, note)

    _exec(_inner())


# ------------------------------------------------------------------- Recipes


@recipes_app.command("list")
def cmd_recipes_list() -> None:
    """List all recipes."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_recipes()

        _exec_json(_inner())
    else:

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
def cmd_recipe_add_to_shopping(
    recipe: str = typer.Argument(..., help="Recipe name or ID."),
) -> None:
    """Add missing recipe ingredients to the shopping list."""

    async def _inner():
        async with _client() as client:
            return await recipe_add_to_shopping(client, recipe)

    _exec(_inner())


@recipes_app.command("create")
def cmd_recipe_create(
    name: str = typer.Argument(..., help="Recipe name."),
    description: str = typer.Option("", "--description", "-d", help="Recipe description."),
    ingredients: str = typer.Option(
        "[]",
        "--ingredients",
        "-i",
        help='JSON list of ingredients, e.g. \'[{"product_id": 1, "amount": 2}]\'.',
    ),
) -> None:
    """Create a new recipe."""
    parsed = _parse_json(ingredients, "--ingredients")

    async def _inner():
        async with _client() as client:
            return await recipe_create(client, name, description, parsed or None)

    _exec(_inner())


@recipes_app.command("update")
def cmd_recipe_update(
    recipe: str = typer.Argument(..., help="Recipe name or ID."),
    name: str | None = typer.Option(None, "--name", help="New name."),
    description: str | None = typer.Option(None, "--description", "-d", help="New description."),
) -> None:
    """Update a recipe's name or description."""

    async def _inner():
        async with _client() as client:
            return await recipe_update(client, recipe, name, description)

    _exec(_inner())


@recipes_app.command("add-ingredient")
def cmd_recipe_add_ingredient(
    recipe: str = typer.Argument(..., help="Recipe name or ID."),
    product: str = typer.Argument(..., help="Product name."),
    amount: float = typer.Option(1.0, "--amount", "-a", help="Quantity."),
) -> None:
    """Add an ingredient to an existing recipe by product name."""

    async def _inner():
        async with _client() as client:
            return await recipe_add_ingredient(client, recipe, product, amount)

    _exec(_inner())


@recipes_app.command("remove-ingredient")
def cmd_recipe_remove_ingredient(
    position_id: int = typer.Argument(..., help="Recipe ingredient position ID."),
) -> None:
    """Remove an ingredient from a recipe."""

    async def _inner():
        async with _client() as client:
            return await recipe_remove_ingredient(client, position_id)

    _exec(_inner())


@recipes_app.command("preview")
def cmd_recipe_consume_preview(
    recipe: str = typer.Argument(..., help="Recipe name or ID."),
) -> None:
    """Preview what stock would be consumed without actually consuming."""

    async def _inner():
        async with _client() as client:
            return await recipe_consume_preview(client, recipe)

    _exec(_inner())


# -------------------------------------------------------------------- Chores


@chores_app.command("list")
def cmd_chores_list() -> None:
    """List all chores."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_chores()

        _exec_json(_inner())
    else:

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
    done_by: int | None = typer.Option(None, "--done-by", help="User ID who completed the chore."),
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


# ----------------------------------------------------------------- Locations


@locations_app.command("list")
def cmd_locations_list() -> None:
    """List all storage locations."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_objects("locations")

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await locations_list(client)

        _exec(_inner())


@locations_app.command("create")
def cmd_location_create(
    name: str = typer.Argument(..., help="Location name."),
    freezer: bool = typer.Option(False, "--freezer", help="Mark as a freezer location."),
    description: str = typer.Option("", "--description", "-d", help="Optional description."),
) -> None:
    """Create a new storage location."""

    async def _inner():
        async with _client() as client:
            return await location_create(client, name, freezer, description)

    _exec(_inner())


# ------------------------------------------------------------- Stock Journal


@stock_app.command("journal", rich_help_panel="View")
def cmd_stock_journal(
    product: str | None = typer.Argument(None, help="Optional product name or ID to filter by."),
) -> None:
    """View recent stock transaction history."""

    async def _inner():
        async with _client() as client:
            return await stock_journal(client, product)

    _exec(_inner())


# -------------------------------------------------------------------- Tasks


@tasks_app.command("list")
def cmd_tasks_list(
    show_done: bool = typer.Option(False, "--done", help="Include completed tasks."),
) -> None:
    """List tasks."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_objects("tasks")

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await tasks_list(client, show_done)

        _exec(_inner())


@tasks_app.command("create")
def cmd_task_create(
    name: str = typer.Argument(..., help="Task name."),
    due_date: str | None = typer.Option(None, "--due", help="Due date (YYYY-MM-DD)."),
    assigned_to: int | None = typer.Option(None, "--assign", help="User ID to assign to."),
    description: str = typer.Option("", "--description", "-d", help="Task description."),
) -> None:
    """Create a new task."""

    async def _inner():
        async with _client() as client:
            return await task_create(client, name, due_date, assigned_to, description)

    _exec(_inner())


@tasks_app.command("complete")
def cmd_task_complete(
    task_id: int = typer.Argument(..., help="Task ID to complete."),
) -> None:
    """Mark a task as done."""

    async def _inner():
        async with _client() as client:
            return await task_complete(client, task_id)

    _exec(_inner())


@tasks_app.command("delete")
def cmd_task_delete(
    task_id: int = typer.Argument(..., help="Task ID to delete."),
) -> None:
    """Delete a task."""

    async def _inner():
        async with _client() as client:
            return await task_delete(client, task_id)

    _exec(_inner())


# --------------------------------------------------------------- Meal Plan


@meal_plan_app.command("list")
def cmd_meal_plan_list() -> None:
    """List all meal plan entries."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_objects("meal_plan")

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await meal_plan_list(client)

        _exec(_inner())


@meal_plan_app.command("add")
def cmd_meal_plan_add(
    day: str = typer.Argument(..., help="Date (YYYY-MM-DD)."),
    recipe: str | None = typer.Option(None, "--recipe", "-r", help="Recipe name or ID."),
    note: str = typer.Option("", "--note", "-n", help="Free-text note."),
    meal_type: str = typer.Option("", "--type", help="Meal type (e.g. recipe, note)."),
) -> None:
    """Add an entry to the meal plan."""

    async def _inner():
        async with _client() as client:
            return await meal_plan_add(client, day, recipe, note, meal_type)

    _exec(_inner())


@meal_plan_app.command("remove")
def cmd_meal_plan_remove(
    entry_id: int = typer.Argument(..., help="Meal plan entry ID."),
) -> None:
    """Remove a meal plan entry."""

    async def _inner():
        async with _client() as client:
            return await meal_plan_remove(client, entry_id)

    _exec(_inner())


@meal_plan_app.command("shopping")
def cmd_meal_plan_shopping(
    start_date: str | None = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)."),
    end_date: str | None = typer.Option(None, "--to", help="End date (YYYY-MM-DD)."),
) -> None:
    """Add missing ingredients for all planned recipes to the shopping list."""

    async def _inner():
        async with _client() as client:
            return await meal_plan_shopping(client, start_date, end_date)

    _exec(_inner())


# -------------------------------------------------------------------- System


@system_app.command("info")
def cmd_system_info() -> None:
    """Show Grocy system information."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_system_info()

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await system_info(client)

        _exec(_inner())


# ------------------------------------------------------------------- Entity


@entity_app.command("list")
def cmd_entity_list(
    entity: str = typer.Argument(..., help="Entity type (e.g. 'products')."),
) -> None:
    """List all objects of a Grocy entity type."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_objects(entity)

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await entity_list(client, entity)

        _exec(_inner())


@entity_app.command("manage")
def cmd_entity_manage(
    entity: str = typer.Argument(..., help="Entity type (e.g. 'products')."),
    action: str = typer.Argument(..., help="Action: create, update, or delete."),
    obj_id: int | None = typer.Option(None, "--id", help="Object ID (required for update/delete)."),
    data: str = typer.Option("{}", "--data", help='JSON fields, e.g. \'{"name": "Pantry"}\'.'),
) -> None:
    """Create, update, or delete a Grocy entity object."""
    parsed = _parse_json(data, "--data")

    async def _inner():
        async with _client() as client:
            return await entity_manage(client, entity, action, obj_id, parsed or None)

    _exec(_inner())


def main() -> None:
    """Entry point for the grocy CLI."""
    app()
