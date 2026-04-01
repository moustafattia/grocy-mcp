# grocy-mcp Implementation Status

**Date:** 2026-04-01  
**Status:** Authoritative current implementation

## Summary

This document records the implemented state of `grocy-mcp` after completing the checkpoint roadmap through CP16.

The repository now provides:

- an 89-tool MCP server
- a mirrored CLI with stock, planning, metadata, workflow, discovery, file, and print surfaces
- stable workflow preview/apply contracts for LLM-assisted Grocy use
- first-class support for the highest-value Grocy household domains outside generic CRUD

## Implemented Areas

### Client Layer

[client.py](C:/Workspace/grocy-mcp/src/grocy_mcp/client.py) now covers:

- generic entity CRUD
- stock, shopping, recipes, chores, tasks, meal plan
- batteries
- calendar iCal export and sharing link
- file download/upload/delete
- print helper endpoints
- retry handling for transient `502`, `503`, and `504` responses

### Core Layer

The current core modules include:

- stock and stock journal
- shopping
- recipes
- chores
- locations
- tasks
- meal plan
- workflow preview/apply
- batteries
- equipment
- calendar
- files/print
- reference-data/discovery helpers
- system and generic entity management

The core layer is intentionally split between:

- human-readable formatted output helpers
- structured data helpers for JSON/reporting surfaces

### Interface Layer

[server.py](C:/Workspace/grocy-mcp/src/grocy_mcp/mcp/server.py) and [app.py](C:/Workspace/grocy-mcp/src/grocy_mcp/cli/app.py) now expose:

- legacy day-to-day household commands/tools
- workflow preview/apply helpers
- catalog metadata helpers
- batteries and equipment
- planning summaries and iCal helpers
- file and print helpers
- entity discovery helpers

## Completed Checkpoints

The roadmap is fully implemented in the current branch:

- CP01–CP06: workflow contracts and preview/apply surface
- CP07–CP08: shopping metadata, quantity metadata, product groups, and price-history views
- CP09–CP10: batteries and equipment
- CP11–CP12: task categories, assignment-aware task output, meal-plan sections, and richer meal-plan reporting
- CP13–CP15: calendar summaries, files/print helpers, and discovery tools
- CP16: support policy, authoritative docs, and completed coverage matrix

## Current Interface Highlights

### Workflow

Implemented workflow helpers:

- product-match preview
- stock-intake preview/apply
- shopping-reconcile preview/apply

Apply flows accept explicit IDs only.

### Catalog

Implemented first-class catalog coverage:

- shopping lists
- shopping locations
- quantity units
- quantity-unit conversions
- product groups
- task categories
- meal-plan sections
- products-last-purchased
- products-average-price

### Household and Planning

Implemented first-class household/planning coverage:

- batteries
- equipment
- meal-plan summary
- calendar summary
- iCal export and sharing link

### Files, Print, and Discovery

Implemented automation-friendly helpers for:

- file-group download/upload/delete
- stock-entry, product, recipe, chore, battery, and shopping-list print triggers
- candidate search
- entity description
- field discovery

## Stability Notes

The following are now treated as compatibility-sensitive:

- MCP tool names
- CLI command names
- documented workflow JSON contracts

The support policy and release checklist live in [SUPPORT.md](C:/Workspace/grocy-mcp/SUPPORT.md).

## Validation

Validation run for the current implementation:

- `pytest -q`
- `ruff check src tests`
- `ruff format --check src tests`

Current result at the time of writing:

- `205 passed, 4 skipped`
- Ruff lint passes
- Ruff format check passes
- the remaining pytest warning is a local `.pytest_cache` permission warning, not an application failure

## Relationship To Older Docs

Historical March 2026 documents remain useful as archival context, but they are not the primary source of truth.

The authoritative current docs are:

- [2026-04-01-grocy-mcp-design.md](C:/Workspace/grocy-mcp/docs/specs/2026-04-01-grocy-mcp-design.md)
- [2026-04-01-grocy-mcp-implementation.md](C:/Workspace/grocy-mcp/docs/specs/2026-04-01-grocy-mcp-implementation.md)
- [2026-04-01-grocy-mcp-workflow-design.md](C:/Workspace/grocy-mcp/docs/specs/2026-04-01-grocy-mcp-workflow-design.md)
