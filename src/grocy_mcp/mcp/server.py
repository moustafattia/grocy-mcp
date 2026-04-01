"""MCP server exposing Grocy tools via FastMCP."""

from __future__ import annotations

import argparse
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastmcp import FastMCP

from grocy_mcp.client import GrocyClient
from grocy_mcp.config import load_config
from grocy_mcp.exceptions import GrocyValidationError
from grocy_mcp.core.batteries import (
    batteries_due_data,
    batteries_list_data,
    batteries_overdue_data,
    battery_charge,
    battery_create,
    battery_cycle_history_data,
    battery_details_data,
    battery_undo_cycle,
    battery_update,
)
from grocy_mcp.core.calendar import calendar_ical_export, calendar_summary_data
from grocy_mcp.core.chores import (
    chore_create,
    chore_execute,
    chore_undo,
    chores_list,
    chores_overdue,
)
from grocy_mcp.core.equipment import (
    equipment_create,
    equipment_details_data,
    equipment_list_data,
    equipment_update,
)
from grocy_mcp.core.files import (
    file_delete,
    file_download_data,
    file_upload_data,
    print_battery_label,
    print_chore_label,
    print_product_label,
    print_recipe_label,
    print_shopping_list_thermal,
    print_stock_entry_label,
)
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
    meal_plan_summary_data,
)
from grocy_mcp.core.reference_data import (
    describe_entity_data,
    discover_entity_fields_data,
    entity_create_view,
    entity_update_view,
    list_entity_records,
    search_entity_candidates_data,
)
from grocy_mcp.core.stock_journal import stock_journal
from grocy_mcp.core.system import entity_list, entity_manage, system_info
from grocy_mcp.core.tasks import task_complete, task_create, task_delete, task_undo, tasks_list
from grocy_mcp.core.workflows import (
    workflow_match_products_preview_data,
    workflow_shopping_reconcile_apply_data,
    workflow_shopping_reconcile_preview_data,
    workflow_stock_intake_apply_data,
    workflow_stock_intake_preview_data,
)


@asynccontextmanager
async def _get_client() -> AsyncIterator[GrocyClient]:
    """Create a GrocyClient from the current configuration."""
    config = load_config()
    async with GrocyClient(config.url, config.api_key) as client:
        yield client


def _parse_json_arg(value: str, label: str) -> dict | list:
    """Parse a JSON tool argument and raise a user-facing validation error on failure."""
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise GrocyValidationError(f"Invalid JSON for {label}: {e}") from e


def create_mcp_server() -> FastMCP:
    """Create and return a FastMCP server with all Grocy tools registered."""
    mcp = FastMCP("grocy-mcp")

    # ------------------------------------------------------------------ Stock

    @mcp.tool()
    async def stock_overview_tool() -> str:
        """List all products currently in stock with their quantities.

        Returns each product with its ID, name, and amount. Use this to see
        what is available before adding, consuming, or transferring stock.
        """
        async with _get_client() as client:
            return await stock_overview(client)

    @mcp.tool()
    async def stock_expiring_tool() -> str:
        """List products that are expiring soon, already expired, or below minimum stock.

        Useful for daily checks or deciding what to consume or restock first.
        """
        async with _get_client() as client:
            return await stock_expiring(client)

    @mcp.tool()
    async def stock_product_info_tool(product: str) -> str:
        """Get detailed stock information for a single product.

        Returns current amount, best-before date, and product metadata.

        Args:
            product: Product name (e.g. "Milk") or numeric product ID.
        """
        async with _get_client() as client:
            return await stock_product_info(client, product)

    @mcp.tool()
    async def stock_add_tool(product: str, amount: float) -> str:
        """Add stock for a product (e.g. after a purchase).

        Args:
            product: Product name (e.g. "Milk") or numeric product ID.
            amount: Quantity to add (e.g. 2.0 for two units).
        """
        async with _get_client() as client:
            return await stock_add(client, product, amount)

    @mcp.tool()
    async def stock_consume_tool(product: str, amount: float) -> str:
        """Consume stock for a product (reduces the quantity on hand).

        Args:
            product: Product name (e.g. "Milk") or numeric product ID.
            amount: Quantity to consume.
        """
        async with _get_client() as client:
            return await stock_consume(client, product, amount)

    @mcp.tool()
    async def stock_transfer_tool(product: str, amount: float, to_location: str) -> str:
        """Move stock of a product to a different storage location.

        Args:
            product: Product name (e.g. "Milk") or numeric product ID.
            amount: Quantity to transfer.
            to_location: Destination location name (e.g. "Fridge") or numeric location ID.
        """
        async with _get_client() as client:
            return await stock_transfer(client, product, amount, to_location)

    @mcp.tool()
    async def stock_inventory_tool(product: str, new_amount: float) -> str:
        """Correct the stock level for a product by setting an absolute quantity.

        Use this when the actual count differs from what Grocy shows — e.g. after
        a manual count. This replaces the current amount, not adds to it.

        Args:
            product: Product name (e.g. "Milk") or numeric product ID.
            new_amount: The corrected total stock quantity.
        """
        async with _get_client() as client:
            return await stock_inventory(client, product, new_amount)

    @mcp.tool()
    async def stock_open_tool(product: str, amount: float = 1.0) -> str:
        """Mark stock units as opened (e.g. an opened bottle of milk).

        Args:
            product: Product name (e.g. "Milk") or numeric product ID.
            amount: Number of units to mark as opened (default 1).
        """
        async with _get_client() as client:
            return await stock_open(client, product, amount)

    @mcp.tool()
    async def stock_search_tool(query: str) -> str:
        """Search for products by name substring or barcode.

        Returns matching product names and IDs. Use this when you are not sure
        of the exact product name. For a direct barcode lookup with stock details,
        use stock_barcode_lookup_tool instead.

        Args:
            query: Search string to match against product names and barcodes.
        """
        async with _get_client() as client:
            return await stock_search(client, query)

    @mcp.tool()
    async def stock_barcode_lookup_tool(barcode: str) -> str:
        """Look up a product and its current stock level by exact barcode.

        Returns the product name and quantity in stock. For partial or name-based
        searches, use stock_search_tool instead.

        Args:
            barcode: The exact barcode string (e.g. "5000112637922").
        """
        async with _get_client() as client:
            return await stock_barcode_lookup(client, barcode)

    # --------------------------------------------------------------- Shopping

    @mcp.tool()
    async def shopping_list_view_tool(list_id: int = 1) -> str:
        """View all items on a shopping list.

        Returns each item with its ID, product name, quantity, and optional note.
        Item IDs are needed for update and remove operations.

        Args:
            list_id: Shopping list ID (default 1, which is the primary list).
        """
        async with _get_client() as client:
            return await shopping_list_view(client, list_id)

    @mcp.tool()
    async def shopping_list_add_tool(
        product: str, amount: float = 1.0, list_id: int = 1, note: str | None = None
    ) -> str:
        """Add a product to the shopping list.

        Args:
            product: Product name (e.g. "Butter") or numeric product ID.
            amount: Quantity to buy (default 1).
            list_id: Shopping list ID (default 1).
            note: Optional free-text note (e.g. "salted" or "organic").
        """
        async with _get_client() as client:
            return await shopping_list_add(client, product, amount, list_id, note)

    @mcp.tool()
    async def shopping_list_update_tool(item_id: int, data: str) -> str:
        """Update fields on an existing shopping list item.

        Use shopping_list_view_tool first to find the item_id.

        Args:
            item_id: The shopping list item ID (from shopping_list_view_tool output).
            data: JSON object with fields to update. Supported fields include
                  "amount" (number), "note" (string), and "product_id" (integer).
                  Example: '{"amount": 3, "note": "unsalted"}'.
        """
        async with _get_client() as client:
            return await shopping_list_update(client, item_id, _parse_json_arg(data, "data"))

    @mcp.tool()
    async def shopping_list_remove_tool(item_id: int) -> str:
        """Remove a single item from the shopping list.

        Use shopping_list_view_tool first to find the item_id.

        Args:
            item_id: The shopping list item ID to remove.
        """
        async with _get_client() as client:
            return await shopping_list_remove(client, item_id)

    @mcp.tool()
    async def shopping_list_clear_tool(list_id: int = 1) -> str:
        """Remove ALL items from a shopping list. This cannot be undone.

        Args:
            list_id: Shopping list ID to clear (default 1).
        """
        async with _get_client() as client:
            return await shopping_list_clear(client, list_id)

    @mcp.tool()
    async def shopping_list_add_missing_tool(list_id: int = 1) -> str:
        """Add all products that are below their minimum stock level to the shopping list.

        This is a bulk operation — it scans all products and adds any that are
        below their configured minimum stock quantity.

        Args:
            list_id: Shopping list ID to add missing products to (default 1).
        """
        async with _get_client() as client:
            return await shopping_list_add_missing(client, list_id)

    @mcp.tool()
    async def shopping_list_set_amount_tool(item_id: int, amount: float) -> str:
        """Change the quantity for a shopping list item.

        A simpler alternative to shopping_list_update_tool when you only
        need to change the amount.

        Args:
            item_id: The shopping list item ID (from shopping_list_view_tool).
            amount: New quantity.
        """
        async with _get_client() as client:
            return await shopping_list_set_amount(client, item_id, amount)

    @mcp.tool()
    async def shopping_list_set_note_tool(item_id: int, note: str) -> str:
        """Set or update the note on a shopping list item.

        A simpler alternative to shopping_list_update_tool when you only
        need to change the note.

        Args:
            item_id: The shopping list item ID (from shopping_list_view_tool).
            note: The new note text (e.g. "organic", "2 for 1 deal").
        """
        async with _get_client() as client:
            return await shopping_list_set_note(client, item_id, note)

    # ---------------------------------------------------------------- Recipes

    @mcp.tool()
    async def recipes_list_tool() -> str:
        """List all recipes with their IDs and descriptions.

        Use this to discover available recipes before checking fulfillment
        or consuming ingredients.
        """
        async with _get_client() as client:
            return await recipes_list(client)

    @mcp.tool()
    async def recipe_details_tool(recipe: str) -> str:
        """Show full details for a recipe including all ingredients and amounts.

        Args:
            recipe: Recipe name (e.g. "Spaghetti Bolognese") or numeric recipe ID.
        """
        async with _get_client() as client:
            return await recipe_details(client, recipe)

    @mcp.tool()
    async def recipe_fulfillment_tool(recipe: str) -> str:
        """Check whether a recipe can be made with current stock.

        Reports whether all ingredients are available and how many are missing.

        Args:
            recipe: Recipe name (e.g. "Spaghetti Bolognese") or numeric recipe ID.
        """
        async with _get_client() as client:
            return await recipe_fulfillment(client, recipe)

    @mcp.tool()
    async def recipe_consume_tool(recipe: str) -> str:
        """Consume stock for all ingredients of a recipe (as if you cooked it).

        This deducts each ingredient amount from stock. Check fulfillment first
        to make sure all ingredients are available.

        Args:
            recipe: Recipe name (e.g. "Spaghetti Bolognese") or numeric recipe ID.
        """
        async with _get_client() as client:
            return await recipe_consume(client, recipe)

    @mcp.tool()
    async def recipe_add_to_shopping_tool(recipe: str) -> str:
        """Add only the missing ingredients for a recipe to the shopping list.

        Does not add ingredients that are already sufficiently in stock.

        Args:
            recipe: Recipe name (e.g. "Spaghetti Bolognese") or numeric recipe ID.
        """
        async with _get_client() as client:
            return await recipe_add_to_shopping(client, recipe)

    @mcp.tool()
    async def recipe_create_tool(name: str, description: str = "", ingredients: str = "[]") -> str:
        """Create a new recipe in Grocy.

        Args:
            name: Recipe name (e.g. "Banana Bread").
            description: Optional description or instructions for the recipe.
            ingredients: JSON array of ingredient objects. Each object should have
                         "product_id" (integer) and "amount" (number). Use
                         stock_search_tool to find product IDs.
                         Example: '[{"product_id": 1, "amount": 2}, {"product_id": 5, "amount": 0.5}]'.
        """
        parsed_ingredients = _parse_json_arg(ingredients, "ingredients")
        async with _get_client() as client:
            return await recipe_create(client, name, description, parsed_ingredients or None)

    @mcp.tool()
    async def recipe_create_by_name_tool(
        name: str, description: str = "", ingredients: str = "[]"
    ) -> str:
        """Create a recipe with ingredients specified by product name instead of ID.

        This is the easier alternative to recipe_create_tool — you can use
        product names directly, and they will be resolved automatically.

        Args:
            name: Recipe name (e.g. "Banana Bread").
            description: Optional description or instructions.
            ingredients: JSON array of ingredient objects. Each should have
                         "product" (name string) and "amount" (number).
                         Example: '[{"product": "Flour", "amount": 2}, {"product": "Banana", "amount": 3}]'.
        """
        parsed_ingredients = _parse_json_arg(ingredients, "ingredients")
        async with _get_client() as client:
            return await recipe_create_by_name(
                client, name, description, parsed_ingredients or None
            )

    @mcp.tool()
    async def recipe_update_tool(
        recipe: str,
        name: str | None = None,
        description: str | None = None,
    ) -> str:
        """Update a recipe's name or description.

        Args:
            recipe: Current recipe name or ID to update.
            name: New name (omit to keep current).
            description: New description (omit to keep current).
        """
        async with _get_client() as client:
            return await recipe_update(client, recipe, name, description)

    @mcp.tool()
    async def recipe_add_ingredient_tool(recipe: str, product: str, amount: float = 1.0) -> str:
        """Add an ingredient to an existing recipe using the product name.

        Args:
            recipe: Recipe name or ID.
            product: Product name (e.g. "Flour") — resolved automatically.
            amount: Quantity needed for the recipe (default 1).
        """
        async with _get_client() as client:
            return await recipe_add_ingredient(client, recipe, product, amount)

    @mcp.tool()
    async def recipe_remove_ingredient_tool(position_id: int) -> str:
        """Remove an ingredient from a recipe.

        Use recipe_details_tool to see ingredient position IDs.

        Args:
            position_id: The recipe ingredient position ID to remove.
        """
        async with _get_client() as client:
            return await recipe_remove_ingredient(client, position_id)

    @mcp.tool()
    async def recipe_consume_preview_tool(recipe: str) -> str:
        """Preview what stock would be consumed without actually consuming.

        Shows each ingredient, the amount needed, and whether there is
        enough in stock. Use this before recipe_consume_tool to verify.

        Args:
            recipe: Recipe name or ID.
        """
        async with _get_client() as client:
            return await recipe_consume_preview(client, recipe)

    # ----------------------------------------------------------------- Chores

    @mcp.tool()
    async def chores_list_tool() -> str:
        """List all chores with their IDs and next scheduled execution time.

        Use this to see what chores exist and when they are due next.
        """
        async with _get_client() as client:
            return await chores_list(client)

    @mcp.tool()
    async def chores_overdue_tool() -> str:
        """List chores that are past their scheduled execution time.

        Returns only chores where the next execution time is in the past.
        """
        async with _get_client() as client:
            return await chores_overdue(client)

    @mcp.tool()
    async def chore_execute_tool(chore: str, done_by: int | None = None) -> str:
        """Mark a chore as done.

        This records an execution and advances the next scheduled time.

        Args:
            chore: Chore name (e.g. "Vacuum living room") or numeric chore ID.
            done_by: Optional Grocy user ID of the person who did the chore.
        """
        async with _get_client() as client:
            return await chore_execute(client, chore, done_by)

    @mcp.tool()
    async def chore_undo_tool(chore: str) -> str:
        """Undo the most recent execution of a chore.

        Removes the last recorded execution and reverts the schedule.

        Args:
            chore: Chore name (e.g. "Vacuum living room") or numeric chore ID.
        """
        async with _get_client() as client:
            return await chore_undo(client, chore)

    @mcp.tool()
    async def chore_create_tool(name: str) -> str:
        """Create a new chore in Grocy.

        Args:
            name: Name for the chore (e.g. "Clean bathroom").
        """
        async with _get_client() as client:
            return await chore_create(client, name)

    # -------------------------------------------------------------- Locations

    @mcp.tool()
    async def locations_list_tool() -> str:
        """List all storage locations in Grocy.

        Shows location names, IDs, and whether each is a freezer.
        """
        async with _get_client() as client:
            return await locations_list(client)

    @mcp.tool()
    async def location_create_tool(
        name: str, is_freezer: bool = False, description: str = ""
    ) -> str:
        """Create a new storage location.

        Args:
            name: Location name (e.g. "Pantry", "Garage fridge").
            is_freezer: Whether this location is a freezer (default false).
            description: Optional description.
        """
        async with _get_client() as client:
            return await location_create(client, name, is_freezer, description)

    # ---------------------------------------------------------- Stock Journal

    @mcp.tool()
    async def stock_journal_tool(product: str | None = None) -> str:
        """View recent stock transaction history.

        Shows the 50 most recent stock changes (purchases, consumption,
        transfers, inventory corrections). Optionally filter by product.

        Args:
            product: Optional product name or ID to filter by.
        """
        async with _get_client() as client:
            return await stock_journal(client, product)

    # ------------------------------------------------------------------ Tasks

    @mcp.tool()
    async def tasks_list_tool(show_done: bool = False) -> str:
        """List tasks (to-do items separate from chores).

        By default shows only incomplete tasks.

        Args:
            show_done: If true, also include completed tasks.
        """
        async with _get_client() as client:
            return await tasks_list(client, show_done)

    @mcp.tool()
    async def task_create_tool(
        name: str,
        due_date: str | None = None,
        assigned_to_user_id: int | None = None,
        description: str = "",
    ) -> str:
        """Create a new task.

        Args:
            name: Task description (e.g. "Buy birthday present").
            due_date: Optional due date in YYYY-MM-DD format.
            assigned_to_user_id: Optional Grocy user ID to assign the task to.
            description: Optional longer description or notes.
        """
        async with _get_client() as client:
            return await task_create(client, name, due_date, assigned_to_user_id, description)

    @mcp.tool()
    async def task_complete_tool(task_id: int) -> str:
        """Mark a task as done.

        Args:
            task_id: The task ID (from tasks_list_tool output).
        """
        async with _get_client() as client:
            return await task_complete(client, task_id)

    @mcp.tool()
    async def task_undo_tool(task_id: int) -> str:
        """Mark a task as not completed.

        Args:
            task_id: The task ID to undo.
        """
        async with _get_client() as client:
            return await task_undo(client, task_id)

    @mcp.tool()
    async def task_delete_tool(task_id: int) -> str:
        """Delete a task. This cannot be undone.

        Args:
            task_id: The task ID to delete.
        """
        async with _get_client() as client:
            return await task_delete(client, task_id)

    # --------------------------------------------------------------- Meal Plan

    @mcp.tool()
    async def meal_plan_list_tool() -> str:
        """List all meal plan entries sorted by date.

        Shows scheduled meals with their dates, recipe names, and notes.
        """
        async with _get_client() as client:
            return await meal_plan_list(client)

    @mcp.tool()
    async def meal_plan_add_tool(
        day: str,
        recipe: str | None = None,
        note: str = "",
        meal_type: str = "",
    ) -> str:
        """Add an entry to the meal plan.

        Either specify a recipe or a free-text note (or both).

        Args:
            day: Date in YYYY-MM-DD format (e.g. "2026-04-05").
            recipe: Optional recipe name or ID to schedule.
            note: Optional free-text note (e.g. "Eat out" or "Leftovers").
            meal_type: Optional meal type (e.g. "recipe", "note"). Auto-detected
                       if not provided.
        """
        async with _get_client() as client:
            return await meal_plan_add(client, day, recipe, note, meal_type)

    @mcp.tool()
    async def meal_plan_remove_tool(entry_id: int) -> str:
        """Remove an entry from the meal plan.

        Args:
            entry_id: The meal plan entry ID (from meal_plan_list_tool output).
        """
        async with _get_client() as client:
            return await meal_plan_remove(client, entry_id)

    @mcp.tool()
    async def meal_plan_shopping_tool(
        start_date: str | None = None, end_date: str | None = None
    ) -> str:
        """Add missing ingredients for all planned recipes to the shopping list.

        Scans the meal plan (optionally filtered by date range), finds all
        scheduled recipes, and adds their unfulfilled ingredients to the
        shopping list. This is the "plan meals → shop" workflow in one step.

        Args:
            start_date: Optional start date filter (YYYY-MM-DD, inclusive).
            end_date: Optional end date filter (YYYY-MM-DD, inclusive).
        """
        async with _get_client() as client:
            return await meal_plan_shopping(client, start_date, end_date)

    @mcp.tool()
    async def meal_plan_summary_tool(
        start_date: str | None = None,
        end_date: str | None = None,
        section_id: int | None = None,
    ) -> dict:
        """Return a structured meal-plan summary with recipe and section names.

        Args:
            start_date: Optional start date filter in YYYY-MM-DD format.
            end_date: Optional end date filter in YYYY-MM-DD format.
            section_id: Optional meal-plan section filter.
        """
        async with _get_client() as client:
            return await meal_plan_summary_data(client, start_date, end_date, section_id)

    # ---------------------------------------------------------------- Catalog

    @mcp.tool()
    async def catalog_list_tool(entity: str, query: str | None = None) -> list[dict]:
        """List first-class catalog and metadata entities.

        Supported entities include shopping_lists, shopping_locations,
        quantity_units, quantity_unit_conversions, product_groups,
        task_categories, meal_plan_sections, products_last_purchased,
        and products_average_price.
        """
        async with _get_client() as client:
            return await list_entity_records(client, entity, query)

    @mcp.tool()
    async def catalog_details_tool(entity: str, obj_id: int) -> dict:
        """Return details for a first-class catalog entity record."""
        async with _get_client() as client:
            return await client.get_object(entity, obj_id)

    @mcp.tool()
    async def catalog_create_tool(entity: str, data: str) -> str:
        """Create a record in a writable first-class catalog entity."""
        parsed_data = _parse_json_arg(data, "data")
        async with _get_client() as client:
            return await entity_create_view(client, entity, parsed_data)

    @mcp.tool()
    async def catalog_update_tool(entity: str, obj_id: int, data: str) -> str:
        """Update a record in a writable first-class catalog entity."""
        parsed_data = _parse_json_arg(data, "data")
        async with _get_client() as client:
            return await entity_update_view(client, entity, obj_id, parsed_data)

    # -------------------------------------------------------------- Batteries

    @mcp.tool()
    async def batteries_list_tool() -> list[dict]:
        """List batteries with next estimated charge times."""
        async with _get_client() as client:
            return await batteries_list_data(client)

    @mcp.tool()
    async def battery_details_tool(battery: str) -> dict:
        """Return detailed information for a battery by name or ID."""
        async with _get_client() as client:
            return await battery_details_data(client, battery)

    @mcp.tool()
    async def batteries_due_tool(days: int = 7) -> list[dict]:
        """Return batteries due within the next given number of days."""
        async with _get_client() as client:
            return await batteries_due_data(client, days)

    @mcp.tool()
    async def batteries_overdue_tool() -> list[dict]:
        """Return batteries that are already overdue for charging."""
        async with _get_client() as client:
            return await batteries_overdue_data(client)

    @mcp.tool()
    async def battery_charge_tool(battery: str, tracked_time: str | None = None) -> str:
        """Track a battery charge cycle."""
        async with _get_client() as client:
            return await battery_charge(client, battery, tracked_time)

    @mcp.tool()
    async def battery_history_tool(battery: str) -> list[dict]:
        """Return charge-cycle history for a battery."""
        async with _get_client() as client:
            return await battery_cycle_history_data(client, battery)

    @mcp.tool()
    async def battery_undo_cycle_tool(cycle_id: int) -> str:
        """Undo a tracked battery charge cycle."""
        async with _get_client() as client:
            return await battery_undo_cycle(client, cycle_id)

    @mcp.tool()
    async def battery_create_tool(
        name: str,
        used_in: str = "",
        charge_interval_days: int = 0,
        description: str = "",
    ) -> str:
        """Create a battery object."""
        async with _get_client() as client:
            return await battery_create(client, name, used_in, charge_interval_days, description)

    @mcp.tool()
    async def battery_update_tool(
        battery: str,
        name: str | None = None,
        used_in: str | None = None,
        charge_interval_days: int | None = None,
        description: str | None = None,
    ) -> str:
        """Update a battery object."""
        async with _get_client() as client:
            return await battery_update(
                client, battery, name, used_in, charge_interval_days, description
            )

    # -------------------------------------------------------------- Equipment

    @mcp.tool()
    async def equipment_list_tool() -> list[dict]:
        """List equipment with linked battery visibility where available."""
        async with _get_client() as client:
            return await equipment_list_data(client)

    @mcp.tool()
    async def equipment_details_tool(equipment: str) -> dict:
        """Return details for an equipment item by name or ID."""
        async with _get_client() as client:
            return await equipment_details_data(client, equipment)

    @mcp.tool()
    async def equipment_create_tool(
        name: str,
        description: str = "",
        battery_id: int | None = None,
    ) -> str:
        """Create an equipment item."""
        async with _get_client() as client:
            return await equipment_create(client, name, description, battery_id)

    @mcp.tool()
    async def equipment_update_tool(
        equipment: str,
        name: str | None = None,
        description: str | None = None,
        battery_id: int | None = None,
    ) -> str:
        """Update an equipment item."""
        async with _get_client() as client:
            return await equipment_update(client, equipment, name, description, battery_id)

    # --------------------------------------------------------------- Calendar

    @mcp.tool()
    async def calendar_summary_tool(
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """Return a read-only planning summary across tasks, chores, batteries, and meal plan."""
        async with _get_client() as client:
            return await calendar_summary_data(client, start_date, end_date)

    @mcp.tool()
    async def calendar_ical_tool() -> dict:
        """Return the raw Grocy iCal export."""
        async with _get_client() as client:
            return {"content": await calendar_ical_export(client)}

    @mcp.tool()
    async def calendar_sharing_link_tool() -> dict:
        """Return the public Grocy iCal sharing link."""
        async with _get_client() as client:
            return await client.get_calendar_sharing_link()

    # ------------------------------------------------------------------ Files

    @mcp.tool()
    async def file_download_tool(
        group: str,
        file_name: str,
        force_picture: bool = False,
        best_fit_width: int | None = None,
        best_fit_height: int | None = None,
    ) -> dict:
        """Download a Grocy-managed file as base64 content."""
        async with _get_client() as client:
            return await file_download_data(
                client, group, file_name, force_picture, best_fit_width, best_fit_height
            )

    @mcp.tool()
    async def file_upload_tool(group: str, file_name: str, content_base64: str) -> dict:
        """Upload a Grocy-managed file from base64 content."""
        async with _get_client() as client:
            return await file_upload_data(client, group, file_name, content_base64)

    @mcp.tool()
    async def file_delete_tool(group: str, file_name: str) -> str:
        """Delete a Grocy-managed file."""
        async with _get_client() as client:
            return await file_delete(client, group, file_name)

    # ------------------------------------------------------------------ Print

    @mcp.tool()
    async def print_stock_entry_label_tool(entry_id: int) -> str:
        """Trigger printing of a stock-entry label."""
        async with _get_client() as client:
            return await print_stock_entry_label(client, entry_id)

    @mcp.tool()
    async def print_product_label_tool(product: str) -> str:
        """Trigger printing of a product label."""
        async with _get_client() as client:
            return await print_product_label(client, product)

    @mcp.tool()
    async def print_recipe_label_tool(recipe: str) -> str:
        """Trigger printing of a recipe label."""
        async with _get_client() as client:
            return await print_recipe_label(client, recipe)

    @mcp.tool()
    async def print_chore_label_tool(chore: str) -> str:
        """Trigger printing of a chore label."""
        async with _get_client() as client:
            return await print_chore_label(client, chore)

    @mcp.tool()
    async def print_battery_label_tool(battery: str) -> str:
        """Trigger printing of a battery label."""
        async with _get_client() as client:
            return await print_battery_label(client, battery)

    @mcp.tool()
    async def print_shopping_list_thermal_tool() -> str:
        """Trigger thermal printing of the shopping list."""
        async with _get_client() as client:
            return await print_shopping_list_thermal(client)

    # --------------------------------------------------------------- Discover

    @mcp.tool()
    async def discover_candidates_tool(entity: str, query: str, limit: int = 10) -> list[dict]:
        """Search products, recipes, chores, locations, tasks, or supported metadata domains."""
        async with _get_client() as client:
            return await search_entity_candidates_data(client, entity, query, limit)

    @mcp.tool()
    async def describe_entity_tool(entity: str) -> dict:
        """Describe a Grocy entity and its discovered fields."""
        async with _get_client() as client:
            return await describe_entity_data(client, entity)

    @mcp.tool()
    async def discover_fields_tool(entity: str) -> dict:
        """Return discovered sample fields for a Grocy entity."""
        async with _get_client() as client:
            return await discover_entity_fields_data(client, entity)

    # --------------------------------------------------------------- Workflow

    @mcp.tool()
    async def workflow_match_products_preview_tool(items: str) -> list[dict]:
        """Preview product matches for normalized external items.

        Use this when an LLM or another client has already converted a receipt,
        chat message, or image into a normalized item list and you need Grocy
        product IDs before applying stock changes.

        Args:
            items: JSON array of normalized input items.
        """
        parsed_items = _parse_json_arg(items, "items")
        async with _get_client() as client:
            return await workflow_match_products_preview_data(client, parsed_items)

    @mcp.tool()
    async def workflow_stock_intake_preview_tool(items: str) -> list[dict]:
        """Preview Grocy stock additions for normalized external items.

        This uses the same matching contract as workflow_match_products_preview_tool,
        but is named for the common \"I bought these groceries\" workflow.

        Args:
            items: JSON array of normalized input items.
        """
        parsed_items = _parse_json_arg(items, "items")
        async with _get_client() as client:
            return await workflow_stock_intake_preview_data(client, parsed_items)

    @mcp.tool()
    async def workflow_stock_intake_apply_tool(items: str) -> dict:
        """Apply confirmed stock additions using explicit Grocy product IDs.

        Apply only confirmed IDs from a prior preview step. This tool does not
        resolve names implicitly.

        Args:
            items: JSON array of confirmed apply items, each with product_id and amount.
        """
        parsed_items = _parse_json_arg(items, "items")
        async with _get_client() as client:
            return await workflow_stock_intake_apply_data(client, parsed_items)

    @mcp.tool()
    async def workflow_shopping_reconcile_preview_tool(items: str, list_id: int = 1) -> list[dict]:
        """Preview shopping-list removals and amount updates after a purchase.

        Provide confirmed Grocy product IDs for what was purchased and this tool
        will propose explicit shopping-item actions without applying them.

        Args:
            items: JSON array of confirmed apply items, each with product_id and amount.
            list_id: Shopping list ID to reconcile against.
        """
        parsed_items = _parse_json_arg(items, "items")
        async with _get_client() as client:
            return await workflow_shopping_reconcile_preview_data(client, parsed_items, list_id)

    @mcp.tool()
    async def workflow_shopping_reconcile_apply_tool(actions: str) -> dict:
        """Apply explicit shopping-list reconciliation actions from a preview step.

        Args:
            actions: JSON array of action objects from workflow_shopping_reconcile_preview_tool.
        """
        parsed_actions = _parse_json_arg(actions, "actions")
        async with _get_client() as client:
            return await workflow_shopping_reconcile_apply_data(client, parsed_actions)

    # ----------------------------------------------------------------- System

    @mcp.tool()
    async def system_info_tool() -> str:
        """Show Grocy server version, PHP version, and SQLite version.

        Useful for verifying connectivity and checking compatibility.
        """
        async with _get_client() as client:
            return await system_info(client)

    @mcp.tool()
    async def entity_list_tool(entity: str) -> str:
        """List all objects of a Grocy entity type.

        This is a generic tool for browsing any Grocy data table.

        Args:
            entity: Entity type name. Common values: 'products', 'locations',
                    'product_groups', 'quantity_units', 'shopping_list',
                    'recipes', 'chores', 'batteries', 'tasks'.
        """
        async with _get_client() as client:
            return await entity_list(client, entity)

    @mcp.tool()
    async def entity_create_tool(entity: str, data: str) -> str:
        """Create a new object of any Grocy entity type.

        This is a low-level tool — prefer the domain-specific create tools
        (recipe_create_tool, chore_create_tool) when available.

        Args:
            entity: Entity type name (e.g. 'products', 'locations', 'tasks').
            data: JSON object with fields for the new entity. Required fields vary
                  by entity type. Example for products: '{"name": "Oat Milk"}'.
                  Example for locations: '{"name": "Pantry", "is_freezer": 0}'.
        """
        parsed_data = _parse_json_arg(data, "data")
        async with _get_client() as client:
            return await entity_manage(client, entity, "create", data=parsed_data or None)

    @mcp.tool()
    async def entity_update_tool(entity: str, obj_id: int, data: str) -> str:
        """Update an existing Grocy entity object by its ID.

        Only the fields provided in data are changed; other fields are left as-is.

        Args:
            entity: Entity type name (e.g. 'products', 'locations').
            obj_id: The object ID to update (use entity_list_tool to find IDs).
            data: JSON object with fields to update.
                  Example: '{"name": "Updated Name", "description": "New desc"}'.
        """
        parsed_data = _parse_json_arg(data, "data")
        async with _get_client() as client:
            return await entity_manage(client, entity, "update", obj_id=obj_id, data=parsed_data)

    @mcp.tool()
    async def entity_delete_tool(entity: str, obj_id: int) -> str:
        """Delete a Grocy entity object by its ID. This cannot be undone.

        Args:
            entity: Entity type name (e.g. 'products', 'locations').
            obj_id: The object ID to delete (use entity_list_tool to find IDs).
        """
        async with _get_client() as client:
            return await entity_manage(client, entity, "delete", obj_id=obj_id)

    return mcp


def main() -> None:
    """Entry point for the grocy-mcp MCP server."""
    parser = argparse.ArgumentParser(description="Grocy MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mechanism (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for streamable-http transport (default: 8000)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address for streamable-http transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--path",
        default="/mcp",
        help="MCP endpoint URL path (default: /mcp)",
    )
    args = parser.parse_args()

    server = create_mcp_server()

    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            path=args.path,
            stateless_http=True,
        )
