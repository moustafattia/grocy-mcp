# grocy-mcp

Python MCP server and CLI for [Grocy](https://grocy.info/).

`grocy-mcp` lets AI agents and terminal users work with Grocy through one shared codebase. It exposes stock, shopping lists, recipes, chores, and generic entity management through:

- an MCP server for tools like Claude Desktop, Claude Code, and other MCP clients
- a `grocy` CLI for direct command-line use

## Why this project

Grocy already has a solid REST API, but most day-to-day interactions still require either:

- clicking through the Grocy UI
- writing one-off API scripts
- wiring ad hoc automations around numeric IDs

`grocy-mcp` packages those API capabilities into a cleaner operator experience:

- human-friendly names instead of IDs for common flows
- a reusable MCP surface for AI agents
- a mirrored CLI for shell workflows and scripting
- one shared implementation for both interfaces

## Features

- 30 MCP tools across stock, shopping, recipes, chores, and system operations
- Full Typer CLI with grouped subcommands under `grocy`
- Name-based resolution for products, recipes, chores, and locations
- Streamable HTTP and stdio MCP transports
- Async client layer with retry handling for transient server errors
- Generic entity access for Grocy resources outside the dedicated commands
- Test suite built with `pytest`, `pytest-asyncio`, and `respx`

## Current status

This project is in active development and currently published as version `0.1.1`.

- Python: `3.11+`
- Grocy: `v4.4.1+`
- Packaging: PyPI package with `grocy-mcp` and `grocy` entry points

## Installation

Install from PyPI:

```bash
pip install grocy-mcp
```

Or run without a permanent install:

```bash
uvx grocy-mcp --transport stdio
```

## Quick start

### 1. Configure access to Grocy

Set environment variables:

```bash
export GROCY_URL="https://grocy.example.com"
export GROCY_API_KEY="your-api-key-here"
```

Or create a config file:

```toml
[grocy]
url = "https://grocy.example.com"
api_key = "your-api-key-here"
```

Expected config path:

- Linux: `~/.config/grocy-mcp/config.toml`
- macOS: `~/Library/Application Support/grocy-mcp/config.toml`
- Windows: platform-specific `grocy-mcp/config.toml` config dir via `platformdirs`

### 2. Run the MCP server

For local stdio clients:

```bash
grocy-mcp --transport stdio
```

For HTTP transport:

```bash
grocy-mcp --transport streamable-http --host 0.0.0.0 --port 8000 --path /mcp
```

### 3. Or use the CLI directly

```bash
grocy stock overview
grocy shopping view
grocy recipes list
grocy chores overdue
```

## MCP usage

Example Claude Desktop / Claude Code-style MCP configuration:

```json
{
  "mcpServers": {
    "grocy": {
      "command": "grocy-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "GROCY_URL": "https://grocy.example.com",
        "GROCY_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

The MCP server currently supports:

- `stdio`
- `streamable-http`

## Agent workflow examples

These are practical multi-step workflows an AI agent can perform by chaining
grocy-mcp tools together:

### "What can I cook tonight?"

1. `recipes_list_tool` — see all available recipes
2. `recipe_fulfillment_tool("Spaghetti Bolognese")` — check if ingredients are in stock
3. If fulfillable: `recipe_consume_tool("Spaghetti Bolognese")` — deduct ingredients
4. If not: `recipe_add_to_shopping_tool("Spaghetti Bolognese")` — add missing items to shopping list

### "Restock after a grocery run"

1. `shopping_list_view_tool` — see what was on the list
2. For each purchased item: `stock_add_tool("Milk", 2)` — add to stock
3. `shopping_list_remove_tool(item_id)` — clear purchased items from the list

### "Weekly kitchen check"

1. `stock_expiring_tool` — find expiring or below-minimum products
2. `chores_overdue_tool` — find overdue household chores
3. `shopping_list_add_missing_tool` — auto-add understocked products to shopping list
4. For each overdue chore: `chore_execute_tool("Vacuum living room")` — mark as done

### "Add a new recipe from a description"

1. `stock_search_tool("flour")` — find product IDs for ingredients
2. `recipe_create_tool("Banana Bread", "Easy banana bread", '[{"product_id": 3, "amount": 2}, ...]')` — create the recipe
3. `recipe_fulfillment_tool("Banana Bread")` — check if you can make it right away

## CLI usage

Top-level command groups:

```bash
grocy stock ...
grocy shopping ...
grocy recipes ...
grocy chores ...
grocy system ...
grocy entity ...
```

### Example commands

```bash
# Stock
grocy stock overview
grocy stock info Milk
grocy stock add Milk 2
grocy stock consume "Oat Milk" 1
grocy stock transfer Milk 1 Fridge
grocy stock inventory Milk 4
grocy stock search milk
grocy stock barcode 5000112637922

# Shopping
grocy shopping view --list-id 1
grocy shopping add Butter --amount 3
grocy shopping update 12 '{"amount": 2, "note": "discount brand"}'
grocy shopping remove 12
grocy shopping clear --list-id 1
grocy shopping add-missing --list-id 1
grocy shopping add "Oat Milk" --amount 2 --list-id 2 --note "for breakfast"

# Recipes
grocy recipes list
grocy recipes details "Spaghetti Bolognese"
grocy recipes fulfillment "Spaghetti Bolognese"
grocy recipes consume "Spaghetti Bolognese"
grocy recipes add-to-shopping "Spaghetti Bolognese"
grocy recipes create "Pancakes" --description "Weekend breakfast" --ingredients '[{"product_id": 1, "amount": 2}]'

# Chores
grocy chores list
grocy chores overdue
grocy chores execute "Vacuum living room"
grocy chores execute "Vacuum living room" --done-by 1
grocy chores undo "Vacuum living room"
grocy chores create "Water plants"

# System / generic entities
grocy system info
grocy entity list products
grocy entity manage products create --data '{"name": "Oat Milk"}'
grocy entity manage products update --id 42 --data '{"name": "Organic Oat Milk"}'
grocy entity manage products delete --id 42
```

## Project structure

```text
src/grocy_mcp/
  client.py          async HTTP client for the Grocy REST API
  config.py          environment/config loading
  exceptions.py      typed error hierarchy
  models.py          pydantic models
  core/              shared business logic for MCP and CLI
  mcp/server.py      FastMCP entry point
  cli/app.py         Typer CLI entry point
tests/
  unit tests for client, core modules, MCP entry point, and CLI
```

## Development

Clone and install for local development:

```bash
git clone https://github.com/moustafattia/grocy-mcp
cd grocy-mcp
pip install -e ".[dev]"
```

Run checks:

```bash
pytest -v
ruff check src/ tests/
ruff format --check src/ tests/
```

Run a specific test:

```bash
pytest tests/test_stock.py -v
pytest tests/test_stock.py::test_stock_overview -v
```

## Documentation

- [Roadmap](./ROADMAP.md)
- [Design and implementation notes](./docs/specs/)

## Roadmap highlights

The next high-value work is tracked in [ROADMAP.md](./ROADMAP.md). The short version:

- close remaining UX gaps between the CLI surface and the underlying implementation
- expand tool coverage deeper into Grocy features
- improve MCP ergonomics for AI agents
- strengthen test coverage for argument-heavy and integration-heavy flows
- tighten release, packaging, and contributor onboarding

## Contributing

Issues, bug reports, docs improvements, and feature proposals are welcome.

Good contribution areas:

- new Grocy domain coverage
- CLI usability improvements
- MCP schema/tool ergonomics
- documentation and examples
- tests around edge cases and Grocy API quirks

## License

MIT
