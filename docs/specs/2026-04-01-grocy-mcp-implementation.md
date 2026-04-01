# grocy-mcp Implementation Status

**Date:** 2026-04-01
**Status:** Current

## Summary

This document records the implemented state of `grocy-mcp` as of 2026-04-01 and captures the cleanup completed in the current PR branch.

The codebase is functional, tested, and organized around a shared async core used by both the MCP server and CLI.

## Implemented Areas

### Client Layer

[client.py](C:/Workspace/grocy-mcp/src/grocy_mcp/client.py) is implemented and currently provides:

- generic CRUD calls via `/objects/{entity}`
- stock operations
- shopping-list operations
- recipe operations
- chore operations
- system info access
- transient retry handling for `502`, `503`, and `504`

### Core Layer

Current core modules:

- [stock.py](C:/Workspace/grocy-mcp/src/grocy_mcp/core/stock.py)
- [shopping.py](C:/Workspace/grocy-mcp/src/grocy_mcp/core/shopping.py)
- [recipes.py](C:/Workspace/grocy-mcp/src/grocy_mcp/core/recipes.py)
- [chores.py](C:/Workspace/grocy-mcp/src/grocy_mcp/core/chores.py)
- [system.py](C:/Workspace/grocy-mcp/src/grocy_mcp/core/system.py)
- [resolve.py](C:/Workspace/grocy-mcp/src/grocy_mcp/core/resolve.py)

These modules currently:

- resolve friendly names to IDs where needed
- call the client layer
- return formatted human-readable output

### Interface Layer

The repo currently ships:

- an MCP server in [server.py](C:/Workspace/grocy-mcp/src/grocy_mcp/mcp/server.py)
- a CLI in [app.py](C:/Workspace/grocy-mcp/src/grocy_mcp/cli/app.py)

The MCP server exposes 30 tools. The CLI mirrors the same domains with Typer subcommands.

## Fixes Included In The Current PR

The current PR branch fixes several behavior and quality issues identified during repo analysis.

### Functional Fixes

1. Shopping-list add now forwards `list_id` and `note`.
   Before this change, [shopping.py](C:/Workspace/grocy-mcp/src/grocy_mcp/core/shopping.py) accepted those parameters but dropped them before the client call.

2. Chore execution now forwards `done_by`.
   Before this change, [chores.py](C:/Workspace/grocy-mcp/src/grocy_mcp/core/chores.py) accepted `done_by` but did not pass it to the client.

3. The unused CLI `--json` callback behavior was removed.
   The flag was advertised in code but not implemented meaningfully, so it was removed to match actual behavior.

### Test and Hygiene Fixes

4. CLI tests were rewritten to avoid unawaited coroutine warnings.
   The new tests exercise the async command path more directly.

5. Unused imports flagged by Ruff were removed.

6. README and design docs were aligned with the current CLI and MCP implementation.

## Validation

Validation run on this branch:

- `ruff check src tests`
- `pytest -q`

Current result at the time of writing:

- Ruff passes
- Pytest passes with `65 passed`
- the remaining warning is a local `.pytest_cache` permission warning, not a test failure

## Current Constraints

The following statements describe the current implementation, not future intent:

- CLI configuration is effectively environment/config-file driven.
- The CLI does not currently support a global `--json` output mode.
- Core functions return strings rather than structured data objects.

## Recommended Follow-ups

These are reasonable next steps, but they are not blockers for the current PR:

1. Decide whether top-level CLI config flags are desirable as a future enhancement.
2. Add a few more CLI tests for argument-rich commands such as:
   - `shopping add --list-id --note`
   - `chores execute --done-by`
   - `shopping update` with JSON payloads
   - `entity manage` with create/update/delete flows
3. Decide whether the historical March planning docs should remain as archival artifacts or be superseded explicitly by the new April docs.

## Relationship To Older Docs

The March 2026 documents in `docs/specs/` are useful as historical design and planning artifacts, but they no longer fully represent the current shipped behavior.

This file and [2026-04-01-grocy-mcp-design.md](C:/Workspace/grocy-mcp/docs/specs/2026-04-01-grocy-mcp-design.md) are intended to document the current state of the repository more accurately.
