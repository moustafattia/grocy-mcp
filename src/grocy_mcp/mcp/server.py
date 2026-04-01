"""MCP server exposing 30 Grocy tools via FastMCP."""

from __future__ import annotations

import argparse
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastmcp import FastMCP

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


@asynccontextmanager
async def _get_client() -> AsyncIterator[GrocyClient]:
    """Create a GrocyClient from the current configuration."""
    config = load_config()
    async with GrocyClient(config.url, config.api_key) as client:
        yield client


def create_mcp_server() -> FastMCP:
    """Create and return a FastMCP server with all 30 Grocy tools registered."""
    mcp = FastMCP("grocy-mcp")

    # ------------------------------------------------------------------ Stock

    @mcp.tool()
    async def stock_overview_tool() -> str:
        """Return a formatted overview of all products currently in stock.

        Args:
            None
        """
        async with _get_client() as client:
            return await stock_overview(client)

    @mcp.tool()
    async def stock_expiring_tool() -> str:
        """Return products that are expiring soon, already expired, or missing.

        Args:
            None
        """
        async with _get_client() as client:
            return await stock_expiring(client)

    @mcp.tool()
    async def stock_product_info_tool(product: str) -> str:
        """Return detailed stock information for a specific product.

        Args:
            product: Product name or ID to look up.
        """
        async with _get_client() as client:
            return await stock_product_info(client, product)

    @mcp.tool()
    async def stock_add_tool(product: str, amount: float) -> str:
        """Add stock for a product.

        Args:
            product: Product name or ID.
            amount: Quantity to add.
        """
        async with _get_client() as client:
            return await stock_add(client, product, amount)

    @mcp.tool()
    async def stock_consume_tool(product: str, amount: float) -> str:
        """Consume (remove) stock for a product.

        Args:
            product: Product name or ID.
            amount: Quantity to consume.
        """
        async with _get_client() as client:
            return await stock_consume(client, product, amount)

    @mcp.tool()
    async def stock_transfer_tool(product: str, amount: float, to_location: str) -> str:
        """Transfer stock to a different location.

        Args:
            product: Product name or ID.
            amount: Quantity to transfer.
            to_location: Destination location name or ID.
        """
        async with _get_client() as client:
            return await stock_transfer(client, product, amount, to_location)

    @mcp.tool()
    async def stock_inventory_tool(product: str, new_amount: float) -> str:
        """Set the stock amount for a product via inventory adjustment.

        Args:
            product: Product name or ID.
            new_amount: The new total stock quantity.
        """
        async with _get_client() as client:
            return await stock_inventory(client, product, new_amount)

    @mcp.tool()
    async def stock_open_tool(product: str, amount: float = 1.0) -> str:
        """Mark stock as opened for a product.

        Args:
            product: Product name or ID.
            amount: Quantity to mark as opened (default 1).
        """
        async with _get_client() as client:
            return await stock_open(client, product, amount)

    @mcp.tool()
    async def stock_search_tool(query: str) -> str:
        """Search for products by name or barcode.

        Args:
            query: Search string to match against product names and barcodes.
        """
        async with _get_client() as client:
            return await stock_search(client, query)

    @mcp.tool()
    async def stock_barcode_lookup_tool(barcode: str) -> str:
        """Look up stock information by barcode.

        Args:
            barcode: The barcode string to look up.
        """
        async with _get_client() as client:
            return await stock_barcode_lookup(client, barcode)

    # --------------------------------------------------------------- Shopping

    @mcp.tool()
    async def shopping_list_view_tool(list_id: int = 1) -> str:
        """Return a formatted view of the shopping list.

        Args:
            list_id: Shopping list ID (default 1).
        """
        async with _get_client() as client:
            return await shopping_list_view(client, list_id)

    @mcp.tool()
    async def shopping_list_add_tool(
        product: str, amount: float = 1.0, list_id: int = 1, note: str | None = None
    ) -> str:
        """Add a product to the shopping list.

        Args:
            product: Product name or ID to add.
            amount: Quantity to add (default 1).
            list_id: Shopping list ID (default 1).
            note: Optional note for the shopping list item.
        """
        async with _get_client() as client:
            return await shopping_list_add(client, product, amount, list_id, note)

    @mcp.tool()
    async def shopping_list_update_tool(item_id: int, data: str) -> str:
        """Update a shopping list item by its ID.

        Args:
            item_id: Shopping list item ID to update.
            data: JSON string with fields to update (e.g. '{"amount": 3}').
        """
        async with _get_client() as client:
            return await shopping_list_update(client, item_id, json.loads(data))

    @mcp.tool()
    async def shopping_list_remove_tool(item_id: int) -> str:
        """Remove a shopping list item by its ID.

        Args:
            item_id: Shopping list item ID to remove.
        """
        async with _get_client() as client:
            return await shopping_list_remove(client, item_id)

    @mcp.tool()
    async def shopping_list_clear_tool(list_id: int = 1) -> str:
        """Clear all items from a shopping list.

        Args:
            list_id: Shopping list ID to clear (default 1).
        """
        async with _get_client() as client:
            return await shopping_list_clear(client, list_id)

    @mcp.tool()
    async def shopping_list_add_missing_tool(list_id: int = 1) -> str:
        """Add all products below minimum stock to the shopping list.

        Args:
            list_id: Shopping list ID to add missing products to (default 1).
        """
        async with _get_client() as client:
            return await shopping_list_add_missing(client, list_id)

    # ---------------------------------------------------------------- Recipes

    @mcp.tool()
    async def recipes_list_tool() -> str:
        """Return a formatted list of all recipes.

        Args:
            None
        """
        async with _get_client() as client:
            return await recipes_list(client)

    @mcp.tool()
    async def recipe_details_tool(recipe: str) -> str:
        """Return detailed information about a recipe including ingredients.

        Args:
            recipe: Recipe name or ID.
        """
        async with _get_client() as client:
            return await recipe_details(client, recipe)

    @mcp.tool()
    async def recipe_fulfillment_tool(recipe: str) -> str:
        """Check if a recipe can be fulfilled with current stock.

        Args:
            recipe: Recipe name or ID.
        """
        async with _get_client() as client:
            return await recipe_fulfillment(client, recipe)

    @mcp.tool()
    async def recipe_consume_tool(recipe: str) -> str:
        """Consume stock for all ingredients of a recipe.

        Args:
            recipe: Recipe name or ID.
        """
        async with _get_client() as client:
            return await recipe_consume(client, recipe)

    @mcp.tool()
    async def recipe_add_to_shopping_tool(recipe: str) -> str:
        """Add missing recipe ingredients to the shopping list.

        Args:
            recipe: Recipe name or ID.
        """
        async with _get_client() as client:
            return await recipe_add_to_shopping(client, recipe)

    @mcp.tool()
    async def recipe_create_tool(
        name: str, description: str = "", ingredients: str = "[]"
    ) -> str:
        """Create a new recipe with optional ingredients.

        Args:
            name: Recipe name.
            description: Optional description of the recipe.
            ingredients: JSON string of ingredient objects, each with product_id and amount
                         (e.g. '[{"product_id": 1, "amount": 2}]').
        """
        parsed_ingredients = json.loads(ingredients)
        async with _get_client() as client:
            return await recipe_create(client, name, description, parsed_ingredients or None)

    # ----------------------------------------------------------------- Chores

    @mcp.tool()
    async def chores_list_tool() -> str:
        """Return a formatted list of all chores.

        Args:
            None
        """
        async with _get_client() as client:
            return await chores_list(client)

    @mcp.tool()
    async def chores_overdue_tool() -> str:
        """Return chores whose next execution time is in the past.

        Args:
            None
        """
        async with _get_client() as client:
            return await chores_overdue(client)

    @mcp.tool()
    async def chore_execute_tool(chore: str, done_by: int | None = None) -> str:
        """Execute (mark as done) a chore.

        Args:
            chore: Chore name or ID.
            done_by: Optional user ID who completed the chore.
        """
        async with _get_client() as client:
            return await chore_execute(client, chore, done_by)

    @mcp.tool()
    async def chore_undo_tool(chore: str) -> str:
        """Undo the most recent execution of a chore.

        Args:
            chore: Chore name or ID.
        """
        async with _get_client() as client:
            return await chore_undo(client, chore)

    @mcp.tool()
    async def chore_create_tool(name: str) -> str:
        """Create a new chore.

        Args:
            name: Name for the new chore.
        """
        async with _get_client() as client:
            return await chore_create(client, name)

    # ----------------------------------------------------------------- System

    @mcp.tool()
    async def system_info_tool() -> str:
        """Return Grocy system information including version details.

        Args:
            None
        """
        async with _get_client() as client:
            return await system_info(client)

    @mcp.tool()
    async def entity_list_tool(entity: str) -> str:
        """List all objects of a given Grocy entity type.

        Args:
            entity: Entity type name (e.g. 'products', 'locations', 'chores').
        """
        async with _get_client() as client:
            return await entity_list(client, entity)

    @mcp.tool()
    async def entity_manage_tool(
        entity: str,
        action: str,
        obj_id: int | None = None,
        data: str = "{}",
    ) -> str:
        """Perform create, update, or delete on any Grocy entity.

        Args:
            entity: Entity type name (e.g. 'products', 'locations').
            action: One of 'create', 'update', or 'delete'.
            obj_id: Object ID (required for update and delete).
            data: JSON string of fields for create/update (e.g. '{"name": "Pantry"}').
        """
        parsed_data = json.loads(data)
        async with _get_client() as client:
            return await entity_manage(client, entity, action, obj_id, parsed_data or None)

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
