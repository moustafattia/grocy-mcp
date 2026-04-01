# grocy-mcp Design Spec

**Date:** 2026-04-01
**Status:** Current

## Overview

`grocy-mcp` is a Python package that exposes Grocy through two interfaces:

- an MCP server for AI agents
- a Typer CLI for human operators

Both interfaces share the same async core logic and the same HTTP client layer.

## Goals

- Provide one consistent integration surface for Grocy stock, shopping, recipes, chores, and system access.
- Keep the MCP server and CLI behavior aligned by routing both through shared core functions.
- Prefer human-friendly names over raw numeric IDs where possible.
- Keep deployment simple: local stdio for MCP, HTTP transport when needed, and environment/config-file based configuration.

## Architecture

The repository uses a three-layer design:

1. `GrocyClient` in [client.py](C:/Workspace/grocy-mcp/src/grocy_mcp/client.py)
   Handles async HTTP requests, auth headers, retries for transient upstream errors, and status-to-exception mapping.
2. Core modules in [core](C:/Workspace/grocy-mcp/src/grocy_mcp/core)
   Implement domain behavior and return human-readable strings for both interfaces.
3. Interface layers in [server.py](C:/Workspace/grocy-mcp/src/grocy_mcp/mcp/server.py) and [app.py](C:/Workspace/grocy-mcp/src/grocy_mcp/cli/app.py)
   Register MCP tools and CLI commands that delegate to the shared core layer.

## Project Structure

```text
src/grocy_mcp/
  client.py          async Grocy REST client
  config.py          env/config-file loading
  exceptions.py      typed domain and transport errors
  models.py          pydantic models for Grocy entities
  core/
    resolve.py       name-to-ID resolution helpers
    stock.py         stock operations
    shopping.py      shopping-list operations
    recipes.py       recipe operations
    chores.py        chore operations
    system.py        system and generic entity operations
  mcp/server.py      FastMCP entry point and tool registration
  cli/app.py         Typer CLI entry point and subcommands
tests/
  test_client.py
  test_resolve.py
  test_stock.py
  test_shopping.py
  test_recipes.py
  test_chores.py
  test_system.py
  test_mcp.py
  test_cli.py
```

## Configuration Model

Current runtime configuration is loaded in this order:

1. explicit function arguments passed to `load_config()`
2. environment variables: `GROCY_URL`, `GROCY_API_KEY`
3. config file at the platform-specific `grocy-mcp/config.toml` path

Current CLI and MCP entry points rely on environment variables or the config file. They do not currently expose top-level `--url` or `--api-key` CLI flags.

## Interface Surface

### MCP

The MCP server exposes 30 tools across these domains:

- stock
- shopping
- recipes
- chores
- system/entity management

The server supports:

- `stdio` transport
- `streamable-http` transport

Current HTTP defaults in [server.py](C:/Workspace/grocy-mcp/src/grocy_mcp/mcp/server.py):

- host: `0.0.0.0`
- port: `8000`
- path: `/mcp`

### CLI

The CLI command groups are:

- `stock`
- `shopping`
- `recipes`
- `chores`
- `system`
- `entity`

Representative commands:

```text
grocy stock overview
grocy stock add Milk 2
grocy shopping view --list-id 1
grocy shopping add Butter --amount 3 --note "salted"
grocy recipes details "Spaghetti Bolognese"
grocy recipes add-to-shopping "Spaghetti Bolognese"
grocy chores execute "Vacuum living room" --done-by 1
grocy entity manage products create --data '{"name": "Oat Milk"}'
```

The CLI currently prints human-readable text returned by the core layer. It does not implement a global `--json` output mode.

## Name Resolution

Name resolution lives in [resolve.py](C:/Workspace/grocy-mcp/src/grocy_mcp/core/resolve.py).

Current behavior:

- numeric strings are treated as IDs directly
- otherwise the system fetches all entities of that type
- case-insensitive substring matching is used
- a single exact case-insensitive match wins when multiple substring matches exist
- ambiguous matches raise `GrocyResolveError` with candidate names

Resolved entities currently include:

- products
- recipes
- chores
- locations

## Error Handling

The client maps Grocy/API failures to typed exceptions in [exceptions.py](C:/Workspace/grocy-mcp/src/grocy_mcp/exceptions.py):

- `401/403` -> `GrocyAuthError`
- `400` -> `GrocyValidationError`
- `404` -> `GrocyNotFoundError`
- `5xx` and transport failures -> `GrocyServerError`
- resolution failures -> `GrocyResolveError`

## Testing Strategy

The repository uses:

- `pytest`
- `pytest-asyncio`
- `respx`
- `typer.testing.CliRunner`

Tests cover:

- client behavior and retries
- name resolution
- core business logic
- MCP server entry behavior
- CLI command execution

## Design Notes

- Shared core functions reduce behavior drift between MCP and CLI.
- Core functions return strings, which keeps both interfaces simple and consistent.
- The code favors straightforward request/response formatting over abstraction-heavy domain layers.
- Generic entity operations provide flexibility for Grocy resources not covered by dedicated commands.
