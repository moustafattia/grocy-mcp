# grocy-mcp Testbed Design

Date: 2026-04-01

## Purpose

The `testbed/` layer validates real Grocy workflows end to end against a disposable demo Grocy instance.

It exists to answer one release-critical question:

Can the same seeded household state support both of these paths safely and repeatably?

- MCP for chat-native LLM clients
- CLI JSON mode for agent systems such as OpenClaw

## Architecture

The testbed keeps `grocy-mcp` on the Grocy-aware execution side of the boundary.

- External models handle receipt parsing, pantry interpretation, and recipe extraction
- `grocy-mcp` handles matching, preview/apply behavior, and Grocy mutations
- The testbed validates that handoff using the existing normalized workflow schema

The testbed is intentionally split into two tiers:

- deterministic PR/CI runs using frozen fixtures and golden normalized JSON
- nightly/manual runs using provider adapters for OpenAI, Anthropic, and OpenAI-compatible endpoints

## Demo environment

The demo stack is defined in `testbed/compose.yaml` and seeded from `testbed/seed/demo_profile.json`.

The committed seed profile is the canonical household snapshot. It creates:

- quantity units
- locations
- shopping lists and shopping locations
- products and product barcodes
- shopping-list entries
- recipes and recipe positions
- a few tasks, chores, batteries, equipment items, and meal-plan entries

Reset behavior:

1. stop the disposable stack
2. wipe `testbed/runtime/`
3. start the stack fresh
4. bootstrap the demo household from the committed seed profile

## Auth model

The demo environment does not require a long-lived real Grocy API key.

Instead:

- the bootstrap layer logs into Grocy through the frontend login form using disposable admin credentials
- a local auth shim exposes a fixed testbed key (`testbed-demo-key` by default)
- the real `grocy` CLI and `grocy-mcp` server then run against that shim exactly as API-key clients

This keeps PR CI self-contained while preserving the same API-key usage pattern that production clients use.

## Scenario model

Scenario manifests live in `testbed/scenarios/*.json` and define:

- seed profile
- task type
- input asset
- source metadata
- golden normalized items
- confirmation file
- expected final outcome
- supported execution modes and extraction sources

The first implemented task types are:

- `receipt_stock`
- `pantry_audit`
- `recipe_url_shopping`

Confirmation rules:

- ambiguous matches never auto-apply
- unmatched items never silently disappear
- mutating scenarios must become fully explicit before any apply step

## Execution paths

CLI mode:

- runs real subprocess commands against `grocy --json ...`
- uses the real shopping commands for Phase 1 recipe-to-shopping scenarios

MCP mode:

- PR tier uses in-process FastMCP tool calls for deterministic speed
- nightly/release tier includes a real stdio transport smoke path through `fastmcp.client`

All final assertions inspect Grocy state through `GrocyClient`, not human-readable command output.

## Initial scenarios

Deterministic:

1. `receipt-stock-basic`
2. `pantry-audit-basic`
3. `recipe-url-shopping-basic`
4. `receipt-stock-ambiguous`

Provider-backed nightly/release runs use the same scenario manifests and expected outcomes.

## Notes and follow-up

The current recipe URL path is intentionally Phase 1:

- extract normalized ingredients
- resolve products through preview
- add confirmed items to a shopping list one by one

The follow-up core improvement is still planned:

- `workflow_shopping_list_preview`
- `workflow_shopping_list_apply`

When that exists, the recipe scenario can move from per-item shopping adds to the same preview/apply contract style used by receipt-to-stock.

