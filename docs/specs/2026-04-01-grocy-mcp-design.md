# grocy-mcp Design Spec

**Date:** 2026-04-01  
**Status:** Authoritative current design

## Overview

`grocy-mcp` is a Python package that exposes Grocy through two aligned interfaces:

- an MCP server for AI agents and MCP-aware clients
- a Typer CLI for direct operator use and shell automation

The design goal is not to move LLM logic into this repository. The repository stays focused on Grocy-aware execution, preview/apply safety, and stable interfaces.

## Core Design Principles

- one shared implementation for MCP and CLI
- human-friendly names instead of raw IDs where practical
- structured JSON contracts for workflow-style preview/apply flows
- read-only reporting surfaces before risky mutation surfaces for new domains
- explicit separation between model interpretation and Grocy mutation

## Architecture

The repository uses a layered design:

1. [client.py](C:/Workspace/grocy-mcp/src/grocy_mcp/client.py)  
   Async HTTP client for Grocy. Handles auth headers, retries, direct API actions, file endpoints, calendar export, and print helpers.

2. [core](C:/Workspace/grocy-mcp/src/grocy_mcp/core)  
   Shared domain logic used by both interfaces. This layer includes:
   - stock, shopping, recipes, chores, tasks, meal-plan
   - workflow preview/apply helpers
   - catalog/reference-data helpers
   - batteries, equipment, calendar, files, and discovery helpers

3. [server.py](C:/Workspace/grocy-mcp/src/grocy_mcp/mcp/server.py) and [app.py](C:/Workspace/grocy-mcp/src/grocy_mcp/cli/app.py)  
   Interface registration and transport-specific ergonomics.

## Workflow Boundary

The workflow layer is intentionally external-model-friendly:

- raw images are not ingested in this repo
- OCR extraction is not implemented in this repo
- ChatGPT, Claude, or another client should first produce normalized JSON items
- `grocy-mcp` then performs preview, matching, confirmation-safe apply, and follow-up Grocy actions

The workflow contracts are defined in [2026-04-01-grocy-mcp-workflow-design.md](C:/Workspace/grocy-mcp/docs/specs/2026-04-01-grocy-mcp-workflow-design.md).

## Interface Surface

### MCP

The MCP server currently exposes 89 tools across:

- stock
- shopping
- recipes
- chores
- locations
- tasks
- meal plan
- catalog metadata
- batteries
- equipment
- calendar
- files
- print
- discovery
- workflow preview/apply
- system and generic entity management

Supported transports:

- `stdio`
- `streamable-http`

HTTP defaults:

- host: `0.0.0.0`
- port: `8000`
- path: `/mcp`

### CLI

The CLI command groups are:

- `stock`
- `shopping`
- `recipes`
- `chores`
- `locations`
- `tasks`
- `meal-plan`
- `catalog`
- `batteries`
- `equipment`
- `calendar`
- `files`
- `print`
- `discover`
- `workflow`
- `system`
- `entity`

The CLI supports:

- global `--json` mode for supported list/view/reporting commands
- top-level `--url` and `--api-key` config overrides
- human-readable output by default

## Name Resolution

Name resolution lives in [resolve.py](C:/Workspace/grocy-mcp/src/grocy_mcp/core/resolve.py).

Current behavior:

- numeric strings are treated as IDs directly
- otherwise all records of the target entity are fetched
- case-insensitive substring matching is used
- a single exact case-insensitive match wins over broader substring matches
- ambiguous matches raise `GrocyResolveError` with candidate labels

Resolved entities currently include:

- products
- recipes
- chores
- locations
- batteries
- equipment

## First-Class vs Generic Coverage

First-class support now covers:

- day-to-day Grocy household domains
- workflow preview/apply
- catalog metadata and price-history views
- calendar and file/print helpers
- discovery helpers for safer generic CRUD

Generic entity management remains for:

- rarely used Grocy entities
- historical or permission-oriented views
- advanced userfield and userentity surfaces

## Error Handling

Typed exceptions in [exceptions.py](C:/Workspace/grocy-mcp/src/grocy_mcp/exceptions.py) remain the error boundary:

- `GrocyAuthError`
- `GrocyValidationError`
- `GrocyNotFoundError`
- `GrocyServerError`
- `GrocyResolveError`

Both CLI and MCP convert malformed JSON into explicit validation failures instead of leaking raw decoder errors.

## Testing Strategy

The repository uses:

- `pytest`
- `pytest-asyncio`
- `respx`
- `typer.testing.CliRunner`

Coverage includes:

- client behavior
- core domain behavior
- workflow contracts
- CLI command execution
- MCP tool registration and structured output
- opt-in live integration smoke tests against a real Grocy instance

## Authoritative Documents

The current source of truth is:

- [2026-04-01-grocy-mcp-design.md](C:/Workspace/grocy-mcp/docs/specs/2026-04-01-grocy-mcp-design.md)
- [2026-04-01-grocy-mcp-implementation.md](C:/Workspace/grocy-mcp/docs/specs/2026-04-01-grocy-mcp-implementation.md)
- [2026-04-01-grocy-mcp-workflow-design.md](C:/Workspace/grocy-mcp/docs/specs/2026-04-01-grocy-mcp-workflow-design.md)
