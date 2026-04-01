"""Typer CLI application for Grocy MCP."""

from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

import typer

from grocy_mcp.client import GrocyClient
from grocy_mcp.config import load_config
from grocy_mcp.core.batteries import (
    batteries_due_data,
    batteries_list_data,
    batteries_list,
    batteries_due,
    batteries_overdue_data,
    batteries_overdue,
    battery_details_data,
    battery_charge,
    battery_create,
    battery_cycle_history_data,
    battery_cycle_history,
    battery_details,
    battery_undo_cycle,
    battery_update,
)
from grocy_mcp.core.calendar import (
    calendar_ical_export,
    calendar_sharing_link,
    calendar_summary,
    calendar_summary_data,
)
from grocy_mcp.core.chores import (
    chore_create,
    chore_execute,
    chore_undo,
    chores_list,
    chores_overdue,
)
from grocy_mcp.core.utils import parse_datetime
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
from grocy_mcp.core.equipment import (
    equipment_create,
    equipment_details,
    equipment_details_data,
    equipment_list,
    equipment_list_data,
    equipment_update,
)
from grocy_mcp.core.files import (
    file_delete,
    file_download_data,
    file_upload,
    file_upload_data,
    print_battery_label,
    print_chore_label,
    print_product_label,
    print_recipe_label,
    print_shopping_list_thermal,
    print_stock_entry_label,
)
from grocy_mcp.core.locations import location_create, locations_list
from grocy_mcp.core.meal_plan import (
    meal_plan_add,
    meal_plan_list,
    meal_plan_remove,
    meal_plan_shopping,
    meal_plan_summary,
    meal_plan_summary_data,
)
from grocy_mcp.core.reference_data import (
    describe_entity,
    describe_entity_data,
    discover_entity_fields,
    discover_entity_fields_data,
    entity_create_view,
    entity_details_view,
    entity_update_view,
    list_entity_records,
    list_entity_view,
    search_entity_candidates,
    search_entity_candidates_data,
)
from grocy_mcp.core.resolve import resolve_product, resolve_recipe
from grocy_mcp.core.stock_journal import stock_journal
from grocy_mcp.core.system import entity_list, entity_manage, system_info
from grocy_mcp.core.tasks import task_complete, task_create, task_delete, task_undo, tasks_list
from grocy_mcp.core.workflows import (
    workflow_match_products_preview,
    workflow_match_products_preview_data,
    workflow_shopping_reconcile_apply,
    workflow_shopping_reconcile_apply_data,
    workflow_shopping_reconcile_preview,
    workflow_shopping_reconcile_preview_data,
    workflow_stock_intake_apply,
    workflow_stock_intake_apply_data,
    workflow_stock_intake_preview,
    workflow_stock_intake_preview_data,
)
from grocy_mcp.exceptions import GrocyError

app = typer.Typer(help="Grocy CLI — manage stock, shopping lists, recipes and chores.")
stock_app = typer.Typer(help="Stock management commands.")
shopping_app = typer.Typer(help="Shopping list commands.")
recipes_app = typer.Typer(help="Recipe commands.")
chores_app = typer.Typer(help="Chore commands.")
locations_app = typer.Typer(help="Storage location commands.")
tasks_app = typer.Typer(help="Task management commands.")
meal_plan_app = typer.Typer(help="Meal plan commands.")
catalog_app = typer.Typer(help="First-class catalog and metadata commands.")
batteries_app = typer.Typer(help="Battery management and lifecycle commands.")
equipment_app = typer.Typer(help="Equipment commands.")
calendar_app = typer.Typer(help="Calendar-oriented read models and iCal helpers.")
files_app = typer.Typer(help="Grocy file-group commands.")
print_app = typer.Typer(help="Print and label commands.")
discover_app = typer.Typer(help="Search and entity-discovery helpers.")
system_app = typer.Typer(help="System information commands.")
entity_app = typer.Typer(help="Generic entity management commands.")
workflow_app = typer.Typer(help="Workflow-oriented preview/apply commands.")

app.add_typer(stock_app, name="stock")
app.add_typer(shopping_app, name="shopping")
app.add_typer(recipes_app, name="recipes")
app.add_typer(chores_app, name="chores")
app.add_typer(locations_app, name="locations")
app.add_typer(tasks_app, name="tasks")
app.add_typer(meal_plan_app, name="meal-plan")
app.add_typer(catalog_app, name="catalog")
app.add_typer(batteries_app, name="batteries")
app.add_typer(equipment_app, name="equipment")
app.add_typer(calendar_app, name="calendar")
app.add_typer(files_app, name="files")
app.add_typer(print_app, name="print")
app.add_typer(discover_app, name="discover")
app.add_typer(system_app, name="system")
app.add_typer(entity_app, name="entity")
app.add_typer(workflow_app, name="workflow")

# Global state set by the app callback.
_cli_url: str | None = None
_cli_api_key: str | None = None
_output_json: bool = False

_CATALOG_ENTITY_ALIASES = {
    "shopping-lists": "shopping_lists",
    "shopping_locations": "shopping_locations",
    "shopping-locations": "shopping_locations",
    "quantity-units": "quantity_units",
    "quantity_units": "quantity_units",
    "quantity-conversions": "quantity_unit_conversions",
    "quantity_unit_conversions": "quantity_unit_conversions",
    "product-groups": "product_groups",
    "product_groups": "product_groups",
    "task-categories": "task_categories",
    "task_categories": "task_categories",
    "meal-plan-sections": "meal_plan_sections",
    "meal_plan_sections": "meal_plan_sections",
    "products-last-purchased": "products_last_purchased",
    "products_last_purchased": "products_last_purchased",
    "products-average-price": "products_average_price",
    "products_average_price": "products_average_price",
}


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


def _catalog_entity(value: str) -> str:
    """Normalize a catalog domain alias into a Grocy entity name."""
    key = value.strip().lower()
    entity = _CATALOG_ENTITY_ALIASES.get(key)
    if entity is None:
        supported = ", ".join(sorted(_CATALOG_ENTITY_ALIASES))
        typer.echo(f"Error: unsupported catalog domain '{value}'. Supported: {supported}", err=True)
        raise typer.Exit(2)
    return entity


def _read_file_base64(path: str) -> str:
    """Read a local file and return base64 content."""
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def _write_downloaded_file(output: str, content_base64: str) -> None:
    """Write a base64 payload to disk."""
    Path(output).write_bytes(base64.b64decode(content_base64.encode("ascii")))


async def _stock_search_json(client: GrocyClient, query: str) -> list[dict]:
    """Return stock search matches as raw JSON-friendly product objects."""
    products = await client.get_objects("products")
    query_lower = query.lower()
    matches = [p for p in products if query_lower in p.get("name", "").lower()]

    barcodes = await client.get_objects("product_barcodes")
    barcode_ids = {b["product_id"] for b in barcodes if query_lower in b.get("barcode", "").lower()}
    for product in products:
        if product["id"] in barcode_ids and product not in matches:
            matches.append(product)

    return matches


async def _recipe_details_json(client: GrocyClient, recipe: str) -> dict:
    """Return recipe details plus ingredient positions for JSON output."""
    recipe_id = await resolve_recipe(client, recipe)
    recipe_data = await client.get_recipe(recipe_id)
    positions = await client.get_objects("recipes_pos")
    recipe_data["ingredients"] = [p for p in positions if p.get("recipe_id") == recipe_id]
    return recipe_data


async def _chores_overdue_json(client: GrocyClient) -> list[dict]:
    """Return only overdue chores for JSON output."""
    chores = await client.get_chores()
    now = datetime.now(tz=timezone.utc)
    return [
        entry
        for entry in chores
        if (next_exec := parse_datetime(entry.get("next_estimated_execution_time")))
        and next_exec < now
    ]


async def _stock_journal_json(client: GrocyClient, product: str | None = None) -> list[dict]:
    """Return stock journal entries sorted newest-first, optionally filtered by product."""
    entries = await client.get_objects("stock_log")
    if product is not None:
        product_id = await resolve_product(client, product)
        entries = [e for e in entries if e.get("product_id") == product_id]

    entries.sort(key=lambda e: e.get("row_created_timestamp", ""), reverse=True)
    return entries[:50]


async def _tasks_list_json(client: GrocyClient, show_done: bool) -> list[dict]:
    """Return raw task objects while preserving the CLI's done-filter semantics."""
    return await client.get_objects("tasks") if show_done else await client.get_tasks()


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
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await _stock_search_json(client, query)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await stock_search(client, query)

    _exec(_inner())


@stock_app.command("barcode", rich_help_panel="View")
def cmd_stock_barcode_lookup(
    barcode: str = typer.Argument(..., help="Barcode to look up."),
) -> None:
    """Look up stock information by barcode."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_stock_by_barcode(barcode)

        _exec_json(_inner())
        return

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
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await _recipe_details_json(client, recipe)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await recipe_details(client, recipe)

    _exec(_inner())


@recipes_app.command("fulfillment")
def cmd_recipe_fulfillment(recipe: str = typer.Argument(..., help="Recipe name or ID.")) -> None:
    """Check if a recipe can be fulfilled with current stock."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                recipe_id = await resolve_recipe(client, recipe)
                return await client.get_recipe_fulfillment(recipe_id)

        _exec_json(_inner())
        return

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
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await _chores_overdue_json(client)

        _exec_json(_inner())
        return

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
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await _stock_journal_json(client, product)

        _exec_json(_inner())
        return

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
                return await _tasks_list_json(client, show_done)

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


@tasks_app.command("undo")
def cmd_task_undo(
    task_id: int = typer.Argument(..., help="Task ID to mark as not done."),
) -> None:
    """Mark a task as not done again."""

    async def _inner():
        async with _client() as client:
            return await task_undo(client, task_id)

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


@meal_plan_app.command("summary")
def cmd_meal_plan_summary(
    start_date: str | None = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)."),
    end_date: str | None = typer.Option(None, "--to", help="End date (YYYY-MM-DD)."),
    section_id: int | None = typer.Option(
        None, "--section-id", help="Optional meal-plan section ID."
    ),
) -> None:
    """Summarize meal-plan entries across a date range, optionally filtered by section."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await meal_plan_summary_data(client, start_date, end_date, section_id)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await meal_plan_summary(client, start_date, end_date, section_id)

    _exec(_inner())


# ------------------------------------------------------------------- Catalog


@catalog_app.command("list")
def cmd_catalog_list(
    domain: str = typer.Argument(
        ..., help="Catalog domain, e.g. shopping-lists or quantity-units."
    ),
    query: str | None = typer.Argument(None, help="Optional query filter."),
) -> None:
    """List supported catalog and metadata entities."""
    entity = _catalog_entity(domain)
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await list_entity_records(client, entity, query)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await list_entity_view(client, entity, query)

    _exec(_inner())


@catalog_app.command("details")
def cmd_catalog_details(
    domain: str = typer.Argument(..., help="Catalog domain."),
    obj_id: int = typer.Argument(..., help="Object ID."),
) -> None:
    """Show details for a supported catalog entity record."""
    entity = _catalog_entity(domain)
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_object(entity, obj_id)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await entity_details_view(client, entity, obj_id)

    _exec(_inner())


@catalog_app.command("create")
def cmd_catalog_create(
    domain: str = typer.Argument(..., help="Writable catalog domain."),
    data: str = typer.Argument(..., help="JSON object for the new record."),
) -> None:
    """Create a supported catalog entity record."""
    entity = _catalog_entity(domain)
    parsed = _parse_json(data, "data")

    async def _inner():
        async with _client() as client:
            return await entity_create_view(client, entity, parsed)

    _exec(_inner())


@catalog_app.command("update")
def cmd_catalog_update(
    domain: str = typer.Argument(..., help="Writable catalog domain."),
    obj_id: int = typer.Argument(..., help="Object ID."),
    data: str = typer.Argument(..., help="JSON object with updated fields."),
) -> None:
    """Update a supported catalog entity record."""
    entity = _catalog_entity(domain)
    parsed = _parse_json(data, "data")

    async def _inner():
        async with _client() as client:
            return await entity_update_view(client, entity, obj_id, parsed)

    _exec(_inner())


# ----------------------------------------------------------------- Batteries


@batteries_app.command("list")
def cmd_batteries_list() -> None:
    """List batteries with next estimated charge time."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await batteries_list_data(client)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await batteries_list(client)

    _exec(_inner())


@batteries_app.command("details")
def cmd_battery_details(battery: str = typer.Argument(..., help="Battery name or ID.")) -> None:
    """Show detailed battery information."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await battery_details_data(client, battery)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await battery_details(client, battery)

    _exec(_inner())


@batteries_app.command("due")
def cmd_batteries_due(
    days: int = typer.Option(7, "--days", help="Include batteries due within this many days."),
) -> None:
    """Show batteries that are due soon."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await batteries_due_data(client, days)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await batteries_due(client, days)

    _exec(_inner())


@batteries_app.command("overdue")
def cmd_batteries_overdue() -> None:
    """Show batteries that are already overdue."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await batteries_overdue_data(client)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await batteries_overdue(client)

    _exec(_inner())


@batteries_app.command("charge")
def cmd_battery_charge(
    battery: str = typer.Argument(..., help="Battery name or ID."),
    tracked_time: str | None = typer.Option(None, "--tracked-time", help="Optional tracked time."),
) -> None:
    """Track a battery charge cycle."""

    async def _inner():
        async with _client() as client:
            return await battery_charge(client, battery, tracked_time)

    _exec(_inner())


@batteries_app.command("history")
def cmd_battery_history(battery: str = typer.Argument(..., help="Battery name or ID.")) -> None:
    """Show charge-cycle history for a battery."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await battery_cycle_history_data(client, battery)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await battery_cycle_history(client, battery)

    _exec(_inner())


@batteries_app.command("undo-cycle")
def cmd_battery_undo_cycle(
    cycle_id: int = typer.Argument(..., help="Battery charge-cycle ID."),
) -> None:
    """Undo a battery charge cycle."""

    async def _inner():
        async with _client() as client:
            return await battery_undo_cycle(client, cycle_id)

    _exec(_inner())


@batteries_app.command("create")
def cmd_battery_create(
    name: str = typer.Argument(..., help="Battery name."),
    used_in: str = typer.Option("", "--used-in", help="What this battery is used in."),
    charge_interval_days: int = typer.Option(0, "--interval-days", help="Charge interval in days."),
    description: str = typer.Option("", "--description", "-d", help="Optional description."),
) -> None:
    """Create a new battery."""

    async def _inner():
        async with _client() as client:
            return await battery_create(client, name, used_in, charge_interval_days, description)

    _exec(_inner())


@batteries_app.command("update")
def cmd_battery_update(
    battery: str = typer.Argument(..., help="Battery name or ID."),
    name: str | None = typer.Option(None, "--name", help="New battery name."),
    used_in: str | None = typer.Option(None, "--used-in", help="Updated usage text."),
    charge_interval_days: int | None = typer.Option(
        None, "--interval-days", help="Updated interval."
    ),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Updated description."
    ),
) -> None:
    """Update a battery."""

    async def _inner():
        async with _client() as client:
            return await battery_update(
                client, battery, name, used_in, charge_interval_days, description
            )

    _exec(_inner())


# ----------------------------------------------------------------- Equipment


@equipment_app.command("list")
def cmd_equipment_list() -> None:
    """List equipment with linked battery visibility where available."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await equipment_list_data(client)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await equipment_list(client)

    _exec(_inner())


@equipment_app.command("details")
def cmd_equipment_details(
    equipment: str = typer.Argument(..., help="Equipment name or ID."),
) -> None:
    """Show detailed equipment information."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await equipment_details_data(client, equipment)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await equipment_details(client, equipment)

    _exec(_inner())


@equipment_app.command("create")
def cmd_equipment_create(
    name: str = typer.Argument(..., help="Equipment name."),
    description: str = typer.Option("", "--description", "-d", help="Optional description."),
    battery_id: int | None = typer.Option(None, "--battery-id", help="Linked battery ID."),
) -> None:
    """Create a new equipment item."""

    async def _inner():
        async with _client() as client:
            return await equipment_create(client, name, description, battery_id)

    _exec(_inner())


@equipment_app.command("update")
def cmd_equipment_update(
    equipment: str = typer.Argument(..., help="Equipment name or ID."),
    name: str | None = typer.Option(None, "--name", help="Updated name."),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Updated description."
    ),
    battery_id: int | None = typer.Option(None, "--battery-id", help="Updated linked battery ID."),
) -> None:
    """Update an equipment item."""

    async def _inner():
        async with _client() as client:
            return await equipment_update(client, equipment, name, description, battery_id)

    _exec(_inner())


# ------------------------------------------------------------------ Calendar


@calendar_app.command("summary")
def cmd_calendar_summary(
    start_date: str | None = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)."),
    end_date: str | None = typer.Option(None, "--to", help="End date (YYYY-MM-DD)."),
) -> None:
    """Summarize chores, batteries, tasks, and meal-plan entries in one read-only view."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await calendar_summary_data(client, start_date, end_date)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await calendar_summary(client, start_date, end_date)

    _exec(_inner())


@calendar_app.command("ical")
def cmd_calendar_ical() -> None:
    """Return the raw iCal export for Grocy."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return {"content": await calendar_ical_export(client)}

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await calendar_ical_export(client)

    _exec(_inner())


@calendar_app.command("sharing-link")
def cmd_calendar_sharing_link() -> None:
    """Show the public iCal sharing link."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await client.get_calendar_sharing_link()

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await calendar_sharing_link(client)

    _exec(_inner())


# --------------------------------------------------------------------- Files


@files_app.command("download")
def cmd_files_download(
    group: str = typer.Argument(..., help="Grocy file group."),
    file_name: str = typer.Argument(..., help="Plain file name as shown by Grocy."),
    output: str | None = typer.Option(None, "--output", "-o", help="Optional output path."),
    picture: bool = typer.Option(False, "--picture", help="Force serve as picture."),
    width: int | None = typer.Option(None, "--width", help="Best-fit width for picture downloads."),
    height: int | None = typer.Option(
        None, "--height", help="Best-fit height for picture downloads."
    ),
) -> None:
    """Download a file from a Grocy file group."""
    try:

        async def _inner():
            async with _client() as client:
                return await file_download_data(client, group, file_name, picture, width, height)

        data = _run(_inner())
        if output:
            _write_downloaded_file(output, data["content_base64"])
        if _output_json:
            typer.echo(json.dumps(data))
        elif output:
            typer.echo(f"Downloaded file '{file_name}' from group '{group}' to {output}.")
        else:
            typer.echo(
                f"Downloaded file '{file_name}' from group '{group}' "
                f"({data.get('content_type') or 'application/octet-stream'})."
            )
    except GrocyError as e:
        if _output_json:
            typer.echo(json.dumps({"error": str(e)}))
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@files_app.command("upload")
def cmd_files_upload(
    group: str = typer.Argument(..., help="Grocy file group."),
    file_name: str = typer.Argument(..., help="File name to store in Grocy."),
    path: str = typer.Argument(..., help="Local file path to upload."),
) -> None:
    """Upload a file into a Grocy file group."""
    content_base64 = _read_file_base64(path)
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await file_upload_data(client, group, file_name, content_base64)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await file_upload(client, group, file_name, content_base64)

    _exec(_inner())


@files_app.command("delete")
def cmd_files_delete(
    group: str = typer.Argument(..., help="Grocy file group."),
    file_name: str = typer.Argument(..., help="Plain file name."),
) -> None:
    """Delete a file from a Grocy file group."""

    async def _inner():
        async with _client() as client:
            return await file_delete(client, group, file_name)

    _exec(_inner())


# --------------------------------------------------------------------- Print


@print_app.command("stock-entry-label")
def cmd_print_stock_entry_label(
    entry_id: int = typer.Argument(..., help="Stock entry ID."),
) -> None:
    """Trigger printing of a stock-entry label."""

    async def _inner():
        async with _client() as client:
            return await print_stock_entry_label(client, entry_id)

    _exec(_inner())


@print_app.command("product-label")
def cmd_print_product_label(
    product: str = typer.Argument(..., help="Product name or ID."),
) -> None:
    """Trigger printing of a product label."""

    async def _inner():
        async with _client() as client:
            return await print_product_label(client, product)

    _exec(_inner())


@print_app.command("recipe-label")
def cmd_print_recipe_label(
    recipe: str = typer.Argument(..., help="Recipe name or ID."),
) -> None:
    """Trigger printing of a recipe label."""

    async def _inner():
        async with _client() as client:
            return await print_recipe_label(client, recipe)

    _exec(_inner())


@print_app.command("chore-label")
def cmd_print_chore_label(
    chore: str = typer.Argument(..., help="Chore name or ID."),
) -> None:
    """Trigger printing of a chore label."""

    async def _inner():
        async with _client() as client:
            return await print_chore_label(client, chore)

    _exec(_inner())


@print_app.command("battery-label")
def cmd_print_battery_label(
    battery: str = typer.Argument(..., help="Battery name or ID."),
) -> None:
    """Trigger printing of a battery label."""

    async def _inner():
        async with _client() as client:
            return await print_battery_label(client, battery)

    _exec(_inner())


@print_app.command("shopping-list-thermal")
def cmd_print_shopping_list_thermal() -> None:
    """Trigger thermal printing of the shopping list."""

    async def _inner():
        async with _client() as client:
            return await print_shopping_list_thermal(client)

    _exec(_inner())


# ------------------------------------------------------------------ Discover


@discover_app.command("search")
def cmd_discover_search(
    domain: str = typer.Argument(..., help="One of products, recipes, chores, locations, tasks."),
    query: str = typer.Argument(..., help="Search query."),
    limit: int = typer.Option(10, "--limit", help="Maximum candidates to return."),
) -> None:
    """Search one of the high-value Grocy domains for candidate matches."""
    entity = domain.strip().lower()
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await search_entity_candidates_data(client, entity, query, limit)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await search_entity_candidates(client, entity, query, limit)

    _exec(_inner())


@discover_app.command("describe-entity")
def cmd_discover_describe_entity(
    entity: str = typer.Argument(..., help="Grocy entity name."),
) -> None:
    """Describe a Grocy entity and its discovered fields."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await describe_entity_data(client, entity)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await describe_entity(client, entity)

    _exec(_inner())


@discover_app.command("fields")
def cmd_discover_fields(
    entity: str = typer.Argument(..., help="Grocy entity name."),
) -> None:
    """List discovered fields for a Grocy entity."""
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await discover_entity_fields_data(client, entity)

        _exec_json(_inner())
        return

    async def _inner():
        async with _client() as client:
            return await discover_entity_fields(client, entity)

    _exec(_inner())


# ------------------------------------------------------------------ Workflow


@workflow_app.command("match-products-preview")
def cmd_workflow_match_products_preview(
    items: str = typer.Argument(
        ...,
        help="JSON array of normalized input items, e.g. "
        '\'[{"label": "whole milk", "quantity": 2, "barcode": "123"}]\'',
    ),
) -> None:
    """Preview product matches for chat- or vision-produced shopping items."""
    parsed_items = _parse_json(items, "items")
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await workflow_match_products_preview_data(client, parsed_items)

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await workflow_match_products_preview(client, parsed_items)

        _exec(_inner())


@workflow_app.command("stock-intake-preview")
def cmd_workflow_stock_intake_preview(
    items: str = typer.Argument(
        ...,
        help="JSON array of normalized input items before confirming Grocy product IDs.",
    ),
) -> None:
    """Preview how external items would map into Grocy stock additions."""
    parsed_items = _parse_json(items, "items")
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await workflow_stock_intake_preview_data(client, parsed_items)

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await workflow_stock_intake_preview(client, parsed_items)

        _exec(_inner())


@workflow_app.command("stock-intake-apply")
def cmd_workflow_stock_intake_apply(
    items: str = typer.Argument(
        ...,
        help='JSON array of confirmed items, e.g. \'[{"product_id": 12, "amount": 2}]\'',
    ),
) -> None:
    """Apply confirmed stock additions using explicit Grocy product IDs."""
    parsed_items = _parse_json(items, "items")
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await workflow_stock_intake_apply_data(client, parsed_items)

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await workflow_stock_intake_apply(client, parsed_items)

        _exec(_inner())


@workflow_app.command("shopping-reconcile-preview")
def cmd_workflow_shopping_reconcile_preview(
    items: str = typer.Argument(
        ...,
        help='JSON array of confirmed purchased items, e.g. \'[{"product_id": 12, "amount": 2}]\'',
    ),
    list_id: int = typer.Option(1, "--list-id", "-l", help="Shopping list ID."),
) -> None:
    """Preview shopping-list removals and amount reductions after a purchase."""
    parsed_items = _parse_json(items, "items")
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await workflow_shopping_reconcile_preview_data(client, parsed_items, list_id)

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await workflow_shopping_reconcile_preview(client, parsed_items, list_id)

        _exec(_inner())


@workflow_app.command("shopping-reconcile-apply")
def cmd_workflow_shopping_reconcile_apply(
    actions: str = typer.Argument(
        ...,
        help="JSON array of explicit shopping-list actions from the preview output.",
    ),
) -> None:
    """Apply explicit shopping-list reconciliation actions."""
    parsed_actions = _parse_json(actions, "actions")
    if _output_json:

        async def _inner():
            async with _client() as client:
                return await workflow_shopping_reconcile_apply_data(client, parsed_actions)

        _exec_json(_inner())
    else:

        async def _inner():
            async with _client() as client:
                return await workflow_shopping_reconcile_apply(client, parsed_actions)

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
