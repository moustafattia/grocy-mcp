"""Core stock management functions for Grocy."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_location, resolve_product


async def stock_overview(client: GrocyClient) -> str:
    """Return a formatted overview of current stock."""
    items = await client.get_stock()
    if not items:
        return "No stock found."
    lines = ["Current stock:"]
    for item in items:
        product = item.get("product") or {}
        name = product.get("name", f"Product {item.get('product_id')}")
        amount = item.get("amount", 0)
        lines.append(f"  [{item.get('product_id', '?')}] {name} — {amount}")
    return "\n".join(lines)


async def stock_expiring(client: GrocyClient) -> str:
    """Return products that are expiring soon or already expired."""
    volatile = await client.get_volatile_stock()
    expiring = volatile.get("expiring_products", [])
    expired = volatile.get("expired_products", [])
    missing = volatile.get("missing_products", [])

    lines = []

    if expiring:
        lines.append("Expiring soon:")
        for item in expiring:
            product = item.get("product") or {}
            name = product.get("name", f"Product {item.get('product_id')}")
            lines.append(f"  {name}")

    if expired:
        lines.append("Expired:")
        for item in expired:
            product = item.get("product") or {}
            name = product.get("name", f"Product {item.get('product_id')}")
            lines.append(f"  {name}")

    if missing:
        lines.append("Missing (below min stock):")
        for item in missing:
            product = item.get("product") or {}
            name = product.get("name", f"Product {item.get('product_id')}")
            lines.append(f"  {name}")

    if not lines:
        return "No expiring, expired, or missing products found."

    return "\n".join(lines)


async def stock_product_info(client: GrocyClient, product: str) -> str:
    """Return detailed stock information for a specific product."""
    product_id = await resolve_product(client, product)
    info = await client.get_stock_product(product_id)

    product_data = info.get("product") or {}
    name = product_data.get("name", f"Product {product_id}")
    amount = info.get("stock_amount", 0)
    best_before = info.get("next_best_before_date", "unknown")

    return f"Product: {name}\n  In stock: {amount}\n  Next best before: {best_before}"


async def stock_add(client: GrocyClient, product: str, amount: float, **kwargs) -> str:
    """Add stock for a product."""
    product_id = await resolve_product(client, product)
    await client.add_stock(product_id, amount, **kwargs)
    return f"Added {amount} of '{product}' to stock."


async def stock_consume(client: GrocyClient, product: str, amount: float, **kwargs) -> str:
    """Consume stock for a product."""
    product_id = await resolve_product(client, product)
    await client.consume_stock(product_id, amount, **kwargs)
    return f"Consumed {amount} of '{product}' from stock."


async def stock_transfer(client: GrocyClient, product: str, amount: float, to_location: str) -> str:
    """Transfer stock to a different location."""
    product_id = await resolve_product(client, product)
    location_id = await resolve_location(client, to_location)
    await client.transfer_stock(product_id, amount, location_id)
    return f"Transferred {amount} of '{product}' to location '{to_location}'."


async def stock_inventory(client: GrocyClient, product: str, new_amount: float) -> str:
    """Set the stock amount for a product via inventory."""
    product_id = await resolve_product(client, product)
    await client.inventory_stock(product_id, new_amount)
    return f"Inventory updated: '{product}' set to {new_amount}."


async def stock_open(client: GrocyClient, product: str, amount: float = 1.0) -> str:
    """Mark stock as opened for a product."""
    product_id = await resolve_product(client, product)
    await client.open_stock(product_id, amount)
    return f"Opened {amount} of '{product}'."


async def stock_search(client: GrocyClient, query: str) -> str:
    """Search for products by name or barcode."""
    products = await client.get_objects("products")
    query_lower = query.lower()
    matches = [p for p in products if query_lower in p.get("name", "").lower()]

    barcodes = await client.get_objects("product_barcodes")
    barcode_ids = {b["product_id"] for b in barcodes if query_lower in b.get("barcode", "").lower()}
    for p in products:
        if p["id"] in barcode_ids and p not in matches:
            matches.append(p)

    if not matches:
        return f"No products found matching '{query}'."

    lines = [f"Products matching '{query}':"]
    for p in matches:
        lines.append(f"  [{p['id']}] {p.get('name', '?')}")
    return "\n".join(lines)


async def stock_barcode_lookup(client: GrocyClient, barcode: str) -> str:
    """Look up stock information by barcode."""
    info = await client.get_stock_by_barcode(barcode)
    product = info.get("product") or {}
    name = product.get("name", f"Barcode {barcode}")
    amount = info.get("stock_amount", 0)
    return f"Barcode {barcode}: {name} — {amount} in stock."
