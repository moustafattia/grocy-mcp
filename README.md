# grocy-mcp

[![PyPI](https://img.shields.io/pypi/v/grocy-mcp)](https://pypi.org/project/grocy-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/grocy-mcp)](https://pypi.org/project/grocy-mcp/)
[![CI](https://github.com/moustafattia/grocy-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/moustafattia/grocy-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/moustafattia/grocy-mcp/blob/main/LICENSE)

Python MCP server and CLI for [Grocy](https://grocy.info/).

`grocy-mcp` lets AI agents and terminal users work with Grocy through one shared codebase. It exposes stock, shopping lists, recipes, chores, batteries, equipment, calendar exports, file groups, print helpers, workflow preview/apply helpers, discovery tools, and generic entity management through:

- an MCP server for tools like Claude Desktop, Claude Code, and other MCP clients
- a `grocy` CLI for direct command-line use

## Choose your path

- Want to connect Grocy to Claude, ChatGPT, or another MCP client? Install `grocy-mcp`, run the MCP server, and point your client at it.
- Want to manage Grocy from the terminal? Install the package and use the `grocy` CLI directly.
- Want to build chat, OCR, or photo-driven flows? Normalize items outside this repo, then call the workflow preview/apply tools here.

If you only want the fastest possible first run, this is enough:

```bash
pip install grocy-mcp
export GROCY_URL="https://grocy.example.com"
export GROCY_API_KEY="your-api-key-here"
grocy stock overview
```

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

- 80+ MCP tools across stock, shopping, recipes, chores, locations, tasks, meal plans, batteries, equipment, calendar, files, print, discovery, workflow helpers, and system operations
- Full Typer CLI with grouped subcommands under `grocy`
- Global `--json` mode for machine-readable output on the supported list/view/reporting commands
- Top-level CLI config overrides via `--url` and `--api-key`
- Name-based resolution for products, recipes, chores, locations, batteries, and equipment
- Stable workflow-oriented JSON contracts for preview/apply flows driven by chat, OCR, or vision clients
- Batch preview/apply helpers for product matching, stock intake, and shopping-list reconciliation
- First-class catalog helpers for shopping metadata, quantity metadata, task categories, meal-plan sections, and price-history views
- First-class household helpers for batteries, equipment, calendar summaries, file groups, print actions, and discovery
- Streamable HTTP and stdio MCP transports
- Async client layer with retry handling for transient server errors
- Generic entity access for Grocy resources outside the dedicated commands
- Test suite built with `pytest`, `pytest-asyncio`, and `respx`

## Current status

This project is in active development and the current published version is `0.2.0`.

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

Use whichever option fits your environment best.

Bash / zsh:

```bash
export GROCY_URL="https://grocy.example.com"
export GROCY_API_KEY="your-api-key-here"
```

PowerShell:

```powershell
$env:GROCY_URL = "https://grocy.example.com"
$env:GROCY_API_KEY = "your-api-key-here"
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

### 2. Pick your path

If you want to use an MCP client such as Claude Desktop or Claude Code, start the server:

Local stdio clients:

```bash
grocy-mcp --transport stdio
```

HTTP transport:

```bash
grocy-mcp --transport streamable-http --host 0.0.0.0 --port 8000 --path /mcp
```

If you just want the CLI, run a command immediately:

```bash
grocy stock overview
grocy shopping view
grocy recipes list
grocy chores overdue
```

If you want structured output for scripts or LLM clients:

```bash
grocy --json stock overview
grocy --json workflow match-products-preview '[{"label":"whole milk","quantity":2}]'
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
- 80+ registered tools in the current implementation

## Architecture split

`grocy-mcp` intentionally stays on the Grocy side of the boundary.

- This repo handles Grocy-aware matching, preview/apply flows, CLI commands, and MCP tools.
- Raw images, OCR payloads, and model-specific prompting stay outside this repo.
- ChatGPT, Claude, or another client should first turn receipts, photos, or chat into normalized JSON items, then call the workflow tools here.

That keeps the project easier to test, safer for mutations, and usable by any model or automation stack.

## Stable workflow contracts

The workflow layer is designed for multi-step, confirmation-first flows.

Normalized input items are used for preview only:

```json
{
  "label": "whole milk",
  "quantity": 2,
  "unit_text": "cartons",
  "barcode": "5000112637922",
  "note": "organic"
}
```

Preview results return `matched`, `ambiguous`, or `unmatched` plus candidate Grocy products:

```json
{
  "input_index": 0,
  "label": "whole milk",
  "status": "matched",
  "matched_product_id": 12,
  "matched_product_name": "Whole Milk",
  "candidates": [{"product_id": 12, "name": "Whole Milk"}],
  "suggested_amount": 2,
  "unit_text": "cartons"
}
```

Apply steps accept explicit IDs only:

```json
{
  "product_id": 12,
  "amount": 2,
  "note": "organic"
}
```

Matching policy for preview tools:

1. exact barcode match
2. exact normalized product-name match
3. case-insensitive substring match

If a stage returns multiple plausible products, the result is `ambiguous` and should be confirmed before any apply step.

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

## Workflow-oriented chat and vision examples

These flows use the workflow surface instead of asking an LLM to mutate Grocy directly.

### Receipt text -> preview -> confirm -> apply

1. External client extracts normalized items from a receipt:

```json
[
  {"label": "whole milk", "quantity": 2, "unit_text": "cartons"},
  {"label": "bananas", "quantity": 6},
  {"label": "oat milk", "quantity": 1}
]
```

2. Call `workflow_match_products_preview_tool(...)` or:

```bash
grocy --json workflow match-products-preview '[{"label":"whole milk","quantity":2},{"label":"bananas","quantity":6}]'
```

3. Confirm any `ambiguous` or `unmatched` lines with the user.
4. Apply confirmed stock additions:

```bash
grocy --json workflow stock-intake-apply '[{"product_id":12,"amount":2},{"product_id":44,"amount":6}]'
```

5. Preview shopping reconciliation:

```bash
grocy --json workflow shopping-reconcile-preview '[{"product_id":12,"amount":2},{"product_id":44,"amount":6}]'
```

6. Apply only the explicit actions returned by the preview.

### Grocery photo interpreted by an LLM -> preview -> confirm -> apply

1. ChatGPT or Claude looks at a grocery-bag photo and produces normalized JSON items.
2. Call `workflow_stock_intake_preview_tool(...)`.
3. Review the proposed product matches and quantities.
4. Confirm explicit `product_id` values.
5. Call `workflow_stock_intake_apply_tool(...)`.

### Pantry photo -> read-only audit preview

1. External model describes visible pantry items as normalized JSON.
2. Call `workflow_match_products_preview_tool(...)`.
3. Use the preview as a read-only audit to compare what the model sees against Grocy product names.
4. Do not apply anything until quantities and matches are confirmed.

## Sample prompts for ChatGPT and Claude

Use prompts like these outside `grocy-mcp` to produce normalized items before calling MCP/CLI workflow commands:

```text
Read this grocery receipt and return only JSON.
Return an array of objects with:
- label
- quantity
- unit_text
- barcode
- note
Do not guess Grocy product IDs.
If quantity is unclear, use 1.
```

```text
Look at this grocery photo and list the likely purchased items as JSON only.
Use this schema for each item:
{"label":"string","quantity":number,"unit_text":"string|null","barcode":"string|null","note":"string|null"}
Do not include commentary.
Do not invent product IDs.
```

```text
Look at this pantry photo and return the visible products as JSON only.
Keep the output read-only and approximate if needed, but do not invent Grocy IDs.
Use the same normalized item schema as above.
```

## CLI usage

Top-level command groups:

```bash
grocy stock ...
grocy shopping ...
grocy recipes ...
grocy chores ...
grocy locations ...
grocy tasks ...
grocy meal-plan ...
grocy catalog ...
grocy batteries ...
grocy equipment ...
grocy calendar ...
grocy files ...
grocy print ...
grocy discover ...
grocy workflow ...
grocy system ...
grocy entity ...
```

Use `grocy --help` or `grocy <group> --help` to explore the full surface. The examples below focus on the highest-value day-to-day commands.

### Example commands

```bash
# Stock and shopping
grocy stock overview
grocy stock info Milk
grocy stock add Milk 2
grocy shopping view --list-id 1
grocy shopping add "Oat Milk" --amount 2 --list-id 2 --note "for breakfast"

# Recipes and chores
grocy recipes list
grocy recipes details "Spaghetti Bolognese"
grocy recipes add-to-shopping "Spaghetti Bolognese"
grocy chores overdue
grocy chores execute "Vacuum living room"

# Workflow preview/apply
grocy --json workflow match-products-preview '[{"label":"whole milk","quantity":2}]'
grocy --json workflow stock-intake-preview '[{"label":"whole milk","quantity":2}]'
grocy --json workflow stock-intake-apply '[{"product_id":12,"amount":2}]'
grocy --json workflow shopping-reconcile-preview '[{"product_id":12,"amount":2}]'

# Catalog, planning, and discovery
grocy --json catalog list shopping-lists
grocy --json batteries list
grocy --json meal-plan summary --from 2026-04-01 --to 2026-04-07
grocy --json calendar summary --from 2026-04-01 --to 2026-04-07
grocy --json discover search products milk
```

## Project structure

```text
src/grocy_mcp/
  client.py          async HTTP client for the Grocy REST API
  config.py          environment/config loading
  exceptions.py      typed error hierarchy
  models.py          pydantic models
  workflow_models.py stable workflow JSON contracts
  core/              shared business logic for MCP and CLI
  core/batteries.py  battery views and charge-cycle actions
  core/calendar.py   combined planning summaries and iCal helpers
  core/equipment.py  equipment views with linked battery context
  core/files.py      file-group download/upload/delete and print helpers
  core/reference_data.py first-class metadata/discovery helpers
  core/workflows.py  preview/apply workflow helpers
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

Run the deterministic end-to-end testbed:

```bash
python -m testbed.seed.reset_demo_env
python -m testbed.runners.run_suite pr
```

## Troubleshooting

**"Grocy URL not configured"**
Set `GROCY_URL` via environment variable, config file, or `--url` flag. The URL
should be the base URL of your Grocy instance (e.g. `https://grocy.example.com`),
not the API endpoint.

**"Auth failed (401)"**
Your API key is invalid or expired. Generate a new one in Grocy under
Settings → Manage API keys. Pass it via `GROCY_API_KEY`, config file, or `--api-key`.

**"Connection failed" or timeouts**
Check that the Grocy URL is reachable from the machine running grocy-mcp. Common
causes: wrong port, firewall rules, Grocy behind a reverse proxy without proper
forwarding.

**"No products found matching '...'"**
The name resolver uses case-insensitive substring matching. Check `grocy stock search`
to see available product names. You can also pass numeric IDs directly.

**"Multiple products match '...'"**
Be more specific with the name, or use the numeric ID shown in the error message.

**MCP server not connecting in Claude Desktop**
Make sure the `command` in your MCP config points to the `grocy-mcp` executable
and that `GROCY_URL` and `GROCY_API_KEY` are set in the `env` block. Check
Claude Desktop logs for error details.

## Documentation

- [Changelog](./CHANGELOG.md)
- [Roadmap](./ROADMAP.md)
- [Support policy](./SUPPORT.md)
- [Contributing](./CONTRIBUTING.md)
- [Design and implementation notes](./docs/specs/)
- [Workflow design](./docs/specs/2026-04-01-grocy-mcp-workflow-design.md)
- [Testbed guide](./testbed/README.md)
- [Testbed design](./docs/specs/2026-04-01-grocy-mcp-testbed-design.md)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup instructions, code style, and
guidelines.

## License

MIT
