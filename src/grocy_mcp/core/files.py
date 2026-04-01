"""File and print helpers for Grocy."""

from __future__ import annotations

import base64

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_battery, resolve_chore, resolve_product, resolve_recipe


def _encode_file_name(file_name: str) -> str:
    return base64.b64encode(file_name.encode("utf-8")).decode("ascii")


async def file_download_data(
    client: GrocyClient,
    group: str,
    file_name: str,
    force_picture: bool = False,
    best_fit_width: int | None = None,
    best_fit_height: int | None = None,
) -> dict:
    """Download a Grocy-managed file and return it as base64."""
    content, content_type = await client.download_file(
        group,
        _encode_file_name(file_name),
        force_serve_as="picture" if force_picture else None,
        best_fit_width=best_fit_width,
        best_fit_height=best_fit_height,
    )
    return {
        "group": group,
        "file_name": file_name,
        "content_type": content_type,
        "content_base64": base64.b64encode(content).decode("ascii"),
    }


async def file_download(
    client: GrocyClient,
    group: str,
    file_name: str,
    force_picture: bool = False,
    best_fit_width: int | None = None,
    best_fit_height: int | None = None,
) -> str:
    """Return a summary of a downloaded Grocy file."""
    data = await file_download_data(
        client,
        group,
        file_name,
        force_picture=force_picture,
        best_fit_width=best_fit_width,
        best_fit_height=best_fit_height,
    )
    return (
        f"Downloaded file '{data['file_name']}' from group '{data['group']}' "
        f"({data.get('content_type') or 'application/octet-stream'})."
    )


async def file_upload_data(
    client: GrocyClient, group: str, file_name: str, content_base64: str
) -> dict:
    """Upload a file to Grocy using base64 content."""
    content = base64.b64decode(content_base64.encode("ascii"))
    await client.upload_file(group, _encode_file_name(file_name), content)
    return {"group": group, "file_name": file_name, "uploaded": True}


async def file_upload(client: GrocyClient, group: str, file_name: str, content_base64: str) -> str:
    """Upload a file to Grocy using base64 content."""
    await file_upload_data(client, group, file_name, content_base64)
    return f"Uploaded file '{file_name}' to group '{group}'."


async def file_delete(client: GrocyClient, group: str, file_name: str) -> str:
    """Delete a Grocy-managed file."""
    await client.delete_file(group, _encode_file_name(file_name))
    return f"Deleted file '{file_name}' from group '{group}'."


async def print_stock_entry_label(client: GrocyClient, entry_id: int) -> str:
    """Trigger printing of a stock-entry label."""
    result = await client.print_stock_entry_label(entry_id)
    return f"Triggered stock entry label print for entry {entry_id}: {result}"


async def print_product_label(client: GrocyClient, product: str) -> str:
    """Trigger printing of a product label."""
    product_id = await resolve_product(client, product)
    result = await client.print_stock_product_label(product_id)
    return f"Triggered product label print for '{product}': {result}"


async def print_recipe_label(client: GrocyClient, recipe: str) -> str:
    """Trigger printing of a recipe label."""
    recipe_id = await resolve_recipe(client, recipe)
    result = await client.print_recipe_label(recipe_id)
    return f"Triggered recipe label print for '{recipe}': {result}"


async def print_chore_label(client: GrocyClient, chore: str) -> str:
    """Trigger printing of a chore label."""
    chore_id = await resolve_chore(client, chore)
    result = await client.print_chore_label(chore_id)
    return f"Triggered chore label print for '{chore}': {result}"


async def print_battery_label(client: GrocyClient, battery: str) -> str:
    """Trigger printing of a battery label."""
    battery_id = await resolve_battery(client, battery)
    result = await client.print_battery_label(battery_id)
    return f"Triggered battery label print for '{battery}': {result}"


async def print_shopping_list_thermal(client: GrocyClient) -> str:
    """Trigger printing of the shopping list on the configured thermal printer."""
    result = await client.print_shopping_list_thermal()
    return f"Triggered shopping list thermal print: {result}"
