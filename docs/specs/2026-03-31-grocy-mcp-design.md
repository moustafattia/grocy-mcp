# grocy-mcp Design Spec

**Date:** 2026-03-31
**Status:** Historical

> Historical snapshot retained for context. For the current design and implementation state, see:
> - [2026-04-01-grocy-mcp-design.md](C:/Workspace/grocy-mcp/docs/specs/2026-04-01-grocy-mcp-design.md)
> - [2026-04-01-grocy-mcp-implementation.md](C:/Workspace/grocy-mcp/docs/specs/2026-04-01-grocy-mcp-implementation.md)

## Overview

`grocy-mcp` is an open-source Python package that provides both an MCP server and a CLI for AI agents and humans to interact with Grocy. It talks directly to the Grocy REST API (v4.4.1+) and covers stock management, shopping lists, recipes, and chores.

## Goals

- Full control of Grocy stock, shopping lists, recipes, and chores from AI agents (via MCP) and terminal (via CLI)
- Published on PyPI as `grocy-mcp`, installable via `pip install grocy-mcp` or `uvx grocy-mcp`
- Supports stdio (local, Claude Code) and Streamable HTTP (remote, Claude.ai via Cloudflare tunnel) transports
- No dependency on Home Assistant -- talks directly to the Grocy REST API

## Architecture

Three layers with clear boundaries:

```
┌─────────────┐  ┌─────────────┐
│  MCP Server  │  │   CLI App   │
│  (FastMCP)   │  │   (Typer)   │
└──────┬───────┘  └──────┬──────┘
       │                 │
       └────────┬────────┘
                │
       ┌────────┴────────┐
       │      Core       │
       │ (business logic)│
       └────────┬────────┘
                │
       ┌────────┴────────┐
       │   GrocyClient   │
       │  (httpx async)  │
       └────────┬────────┘
                │
       ┌────────┴────────┐
       │  Grocy REST API │
       └─────────────────┘
```

- **GrocyClient** -- thin async httpx wrapper. Handles auth, base URL, error mapping. ~200 lines.
- **Core** -- business logic modules (stock, shopping, recipes, chores, system). Uses the client. Shared by both interfaces.
- **MCP Server** -- FastMCP server exposing 30 tools. Stdio by default, Streamable HTTP via flag.
- **CLI App** -- Typer app with subcommands. Bridges async via `asyncio.run()`.

## Project Structure

```
grocy-mcp/
├── src/
│   └── grocy_mcp/
│       ├── __init__.py
│       ├── client.py          # Async httpx client for Grocy REST API
│       ├── models.py          # Pydantic models for API entities
│       ├── exceptions.py      # Typed exceptions
│       ├── config.py          # Configuration loading (env, file, flags)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── stock.py       # Stock operations
│       │   ├── shopping.py    # Shopping list management
│       │   ├── recipes.py     # Recipe CRUD + fulfillment
│       │   ├── chores.py      # Chore CRUD + execution
│       │   └── system.py      # System info, generic entity access
│       ├── mcp/
│       │   ├── __init__.py
│       │   └── server.py      # FastMCP server
│       └── cli/
│           ├── __init__.py
│           └── app.py         # Typer CLI app
├── tests/
│   ├── conftest.py            # Shared fixtures, mock client
│   ├── test_client.py
│   ├── test_stock.py
│   ├── test_shopping.py
│   ├── test_recipes.py
│   ├── test_chores.py
│   ├── test_cli.py
│   └── test_mcp.py
├── pyproject.toml
├── README.md
└── LICENSE                    # MIT
```

## API Client

`GrocyClient` -- single async class using `httpx.AsyncClient`.

**Authentication:** `GROCY-API-KEY` header on every request.

**Generic CRUD methods** (cover any entity type via `/objects/{entity}`):
- `get_objects(entity, query?)` -- list with optional filtering
- `get_object(entity, id)` -- get by ID
- `create_object(entity, data)` -- create, returns ID
- `update_object(entity, id, data)` -- update
- `delete_object(entity, id)` -- delete

**Stock methods:**
- `get_stock()` -- all products in stock
- `search_products(query)` -- search products by name via client-side filter over `get_objects('products')`. Also searches `product_barcodes` entity for barcode matches.
- `get_stock_product(product_id)` -- single product details
- `add_stock(product_id, amount, **kwargs)` -- add to stock
- `consume_stock(product_id, amount, **kwargs)` -- consume from stock
- `transfer_stock(product_id, amount, to_location)` -- move between locations
- `inventory_stock(product_id, new_amount)` -- set absolute amount
- `open_stock(product_id, amount)` -- mark as opened
- `get_volatile_stock()` -- expiring, overdue, expired, missing
- `get_stock_by_barcode(barcode)` -- barcode lookup

**Shopping list methods:**
- `get_shopping_list(list_id=1)` -- view list
- `add_shopping_list_item(...)` -- add item
- `update_shopping_list_item(item_id, data)` -- update item (quantity, note, etc.)
- `remove_shopping_list_item(item_id)` -- remove item
- `clear_shopping_list(list_id)` -- clear all
- `add_missing_products_to_shopping_list(list_id=1)` -- add all below-min-stock products (POST `/stock/shoppinglist/add-missing-products`)

**Recipe methods:**
- `get_recipes()` -- list all
- `get_recipe(recipe_id)` -- details with ingredients
- `get_recipe_fulfillment(recipe_id)` -- can it be made?
- `consume_recipe(recipe_id)` -- consume ingredients from stock
- `add_recipe_to_shopping_list(recipe_id)` -- add missing ingredients
- `create_recipe(data)` -- create via `create_object('recipes', data)`, then create each ingredient via `create_object('recipes_pos', data)`. Recipe creation is a multi-step operation handled in the core layer.
- `update_recipe(recipe_id, data)` -- update recipe and optionally its ingredients

**Chore methods:**
- `get_chores()` -- list all (includes `next_estimated_execution_time` for overdue filtering)
- `get_chore(chore_id)` -- details
- `execute_chore(chore_id, done_by?)` -- mark done
- `get_chore_executions(chore_id)` -- list executions (needed to resolve last execution ID for undo)
- `undo_chore_execution(execution_id)` -- undo a specific execution

**System methods:**
- `get_system_info()` -- version, config

**Error handling:** Maps HTTP status codes to typed exceptions:
- 401/403 -> `GrocyAuthError`
- 400 -> `GrocyValidationError`
- 404 -> `GrocyNotFoundError`
- 500 -> `GrocyServerError`

**Timeouts and retries:**
- Connection timeout: 10s. Read timeout: 30s.
- Single `httpx.AsyncClient` instance reused for the lifetime of the server/CLI session.
- Retry up to 2 times on transient errors (502, 503, 504) with 1s backoff. No retry on 4xx errors.

## Pydantic Models

Core entities with validation and serialization:

- `Product` -- id, name, description, location_id, min_stock_amount, qu_id_purchase, qu_id_stock (note: barcodes are a separate entity `product_barcodes` in Grocy v4.x, not a field on Product)
- `ProductBarcode` -- id, product_id, barcode, qu_id, amount
- `StockEntry` -- id, product_id, amount, best_before_date, location_id, open, price
- `ShoppingListItem` -- id, shopping_list_id, product_id, amount, note, done
- `Recipe` -- id, name, description, servings, ingredients (list), instructions
- `RecipeIngredient` -- id, recipe_id, product_id, amount, qu_id, note
- `Chore` -- id, name, period_type, period_interval, next_execution_assigned_to_user_id, next_estimated_execution_time
- `ChoreExecution` -- id, chore_id, executed_time, done_by_user_id
- `SystemInfo` -- grocy_version, php_version, sqlite_version, os

Raw dicts used for generic entity access and edge cases.

## Name-to-ID Resolution

Central to AI agent usability. All MCP tools and CLI commands accept human-readable names (e.g., "Milk", "Bathroom cleaning") instead of numeric IDs.

**Resolution logic** (implemented in each core module):
1. If the input is a numeric string, treat it as an ID and look up directly.
2. Otherwise, fetch all entities of the type (e.g., all products) and perform case-insensitive substring matching.
3. **Zero matches** -- return a clear error: "No product found matching 'Mlk'. Did you mean: Milk, Milk (2%)?"
4. **Exactly one match** -- use it.
5. **Multiple matches** -- if one is an exact match (case-insensitive), use it. Otherwise return an error listing the matches: "Multiple products match 'Milk': Milk (ID 1), Milk 2% (ID 5), Almond Milk (ID 12). Please be more specific."

**Applies to:** Products, recipes, chores, locations, shopping lists (by name). Each core module has a `resolve_<entity>(client, name_or_id)` helper.

**No fuzzy matching library needed** -- simple substring matching is sufficient and predictable. AI agents can retry with the suggested names from error messages.

**Caching:** Entity lists are not cached between tool calls. Grocy instances are small enough that re-fetching is negligible (<50ms). This avoids stale cache issues.

## MCP Tools (30 total)

### Stock (10 tools)

| Tool | Parameters | Description |
|---|---|---|
| `stock_overview` | -- | List all products in stock with quantities and locations |
| `stock_expiring` | -- | Show expiring, expired, and missing products |
| `stock_product_info` | `product` (name or ID) | Get details for a specific product |
| `stock_add` | `product`, `amount`, `best_before?`, `price?`, `location?` | Add stock |
| `stock_consume` | `product`, `amount`, `spoiled?` | Consume stock |
| `stock_transfer` | `product`, `amount`, `to_location` | Move stock between locations |
| `stock_inventory` | `product`, `new_amount` | Set absolute stock amount |
| `stock_open` | `product`, `amount?` (default 1) | Mark product as opened |
| `stock_search` | `query` | Search products by name, barcode, or category |
| `stock_barcode_lookup` | `barcode` | Look up product by barcode |

### Shopping Lists (6 tools)

| Tool | Parameters | Description |
|---|---|---|
| `shopping_list_view` | `list_id?` (default 1) | View shopping list items |
| `shopping_list_add` | `product`, `amount?`, `list_id?`, `note?` | Add item |
| `shopping_list_update` | `item_id`, `amount?`, `note?` | Update an existing item |
| `shopping_list_remove` | `item_id` | Remove item |
| `shopping_list_clear` | `list_id?` | Clear all items |
| `shopping_list_add_missing` | `list_id?` | Add all below-min-stock products |

### Recipes (6 tools)

| Tool | Parameters | Description |
|---|---|---|
| `recipes_list` | -- | List all recipes |
| `recipe_details` | `recipe` (name or ID) | Get recipe with ingredients and instructions |
| `recipe_fulfillment` | `recipe` | Check if recipe can be made with current stock |
| `recipe_consume` | `recipe` | Consume recipe ingredients from stock |
| `recipe_add_to_shopping` | `recipe` | Add missing ingredients to shopping list |
| `recipe_create` | `name`, `ingredients`, `instructions`, `servings?` | Create a recipe |

### Chores (5 tools)

| Tool | Parameters | Description |
|---|---|---|
| `chores_list` | -- | List all chores with next execution dates |
| `chores_overdue` | -- | Show overdue chores |
| `chore_execute` | `chore` (name or ID), `done_by?` | Mark chore as done |
| `chore_undo` | `chore` (name or ID) | Undo last execution (resolves chore to its most recent execution ID via `get_chore_executions`) |
| `chore_create` | `name`, `period_type`, `period_interval?`, `assigned_to?` | Create a chore |

### System (3 tools)

| Tool | Parameters | Description |
|---|---|---|
| `system_info` | -- | Get Grocy version and system info |
| `entity_list` | `entity_type` | List any generic entity (locations, quantity units, etc.) |
| `entity_manage` | `action` (create/update/delete), `entity_type`, `id?`, `data?` | Manage generic entities |

### Design decisions

- **Name-based lookups** -- tools like `stock_add` accept product names, not just IDs. The core layer resolves names to IDs via fuzzy search against the product list. This is essential for AI agent usability.
- **Sensible defaults** -- shopping list defaults to list 1, stock_open defaults to amount 1, etc.
- **Structured returns** -- tools return formatted, human-readable text (not raw JSON). Summaries, tables, confirmation messages.

## CLI Structure

Four top-level command groups plus utilities:

```
grocy stock list
grocy stock expiring
grocy stock info <product>
grocy stock add <product> <amount>
grocy stock consume <product> <amount>
grocy stock transfer <product> <amount> --to <location>
grocy stock inventory <product> <amount>
grocy stock open <product> [amount]
grocy stock search <query>
grocy stock barcode <barcode>

grocy shopping list [list_id]
grocy shopping add <product> [amount]
grocy shopping remove <item>
grocy shopping clear [list_id]
grocy shopping add-missing

grocy recipes list
grocy recipes show <recipe>
grocy recipes check <recipe>
grocy recipes consume <recipe>
grocy recipes to-shopping <recipe>
grocy recipes create <name>

grocy chores list
grocy chores overdue
grocy chores done <chore> [--by <person>]
grocy chores undo <chore>
grocy chores create <name>

grocy shopping update <item_id> --amount <n> --note "..."

grocy system info
grocy entity list <type>
grocy entity create <type> --data '{...}'
grocy entity update <type> <id> --data '{...}'
grocy entity delete <type> <id>
```

### Design decisions

- **Positional args for common cases** -- `grocy stock add Milk 2` works without flags.
- **Output formats** -- human-friendly tables via `rich` by default. `--json` flag for machine-readable output.
- **Async bridge** -- CLI uses `asyncio.run()` to call the same async core modules the MCP server uses.

## Configuration

Single config system shared by MCP and CLI. Priority (highest to lowest):

1. CLI flags (`--url`, `--api-key`)
2. Environment variables (`GROCY_URL`, `GROCY_API_KEY`)
3. Config file (cross-platform via `platformdirs`: `~/.config/grocy-mcp/config.toml` on Linux, `%APPDATA%/grocy-mcp/config.toml` on Windows, `~/Library/Application Support/grocy-mcp/config.toml` on macOS)

Config file format:
```toml
[grocy]
url = "https://grocy.attiamo.com"
api_key = "your-api-key"
```

## Transport & Deployment

**MCP transports:**
- **stdio** (default) -- for Claude Code. Launched via `uvx grocy-mcp`.
- **Streamable HTTP** (`--transport streamable-http --port 8765`) -- for remote access via Cloudflare tunnel. This is the current MCP specification standard, replacing the deprecated SSE transport. FastMCP supports this natively.

**Claude Code config example:**
```json
{
  "type": "stdio",
  "command": "uvx",
  "args": ["grocy-mcp@latest"],
  "env": {
    "GROCY_URL": "http://homeassistant.local:9192",
    "GROCY_API_KEY": "<key>"
  }
}
```

**Remote access pattern:** Run `grocy-mcp --transport streamable-http --port 8765` on the HA server, add Cloudflare tunnel route `grocy-mcp.attiamo.com` -> `localhost:8765`.

**PyPI entry points:**
- `grocy-mcp` -> MCP server (`grocy_mcp.mcp.server:main`)
- `grocy` -> CLI (`grocy_mcp.cli.app:main`)

## Dependencies

- `httpx` -- async HTTP client
- `fastmcp` -- MCP server framework
- `typer` -- CLI framework
- `pydantic` -- data validation and models
- `rich` -- terminal output formatting (installed with typer)
- `platformdirs` -- cross-platform config file paths

**Python:** 3.11+

## Pagination

Grocy's API returns all results by default with no server-side pagination. For typical home Grocy instances (< 500 products, < 100 recipes/chores), this is not a concern. The client fetches all results in a single request. If this becomes a problem for large instances, the generic `get_objects` method supports Grocy's `limit` and `offset` query parameters, but this is not exposed in the MCP tools or CLI initially -- YAGNI.

## Testing

- **Framework:** pytest + pytest-asyncio
- **HTTP mocking:** respx (httpx-native mocking, no real Grocy needed)
- **Unit tests:** client methods, core business logic, CLI commands
- **Integration tests:** optional, run against a real Grocy instance. Skipped in CI by default, enabled via `GROCY_TEST_URL` and `GROCY_TEST_API_KEY` env vars.

## License

MIT
