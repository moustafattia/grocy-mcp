# Roadmap

This roadmap is a checkpoint ledger, not a feature wishlist.

`grocy-mcp` follows a two-layer model:

- `grocy-mcp` stays the Grocy-facing core: MCP server, CLI, stable workflow contracts
- chat, OCR, and image interpretation stay outside this repo and feed normalized JSON into it

The checkpoint sequence from CP01 through CP16 is now implemented in this branch.

## Operating Model

Every checkpoint is intended to be:

- implemented as a reviewable increment
- covered by unit tests plus targeted CLI/MCP tests
- documented in the same change
- merged only after review feedback is addressed

### Standard acceptance gate

Every checkpoint uses the same merge gate:

- unit tests for new core and workflow logic
- CLI tests for text and JSON modes where applicable
- MCP tests for tool registration, structured output, and malformed JSON/input validation
- opt-in live Grocy integration coverage for mutating checkpoints
- README, roadmap status, command/tool help text, and coverage notes updated in the same PR
- no known doc/code drift left behind

## Coverage Matrix

### First-class support

- stock
- shopping list operations
- shopping list metadata via `catalog`
- recipes
- chores
- locations
- tasks
- task categories via `catalog`
- meal plan
- meal-plan sections via `catalog`
- workflow preview/apply primitives
- quantity units and quantity-unit conversions via `catalog`
- product groups via `catalog`
- products-last-purchased and products-average-price read models via `catalog`
- batteries
- equipment
- calendar summaries and iCal export helpers
- file-group download/upload/delete helpers
- print helpers
- discovery helpers

### Generic-entity-only support

- recipe nestings
- userfields
- userentities
- userobjects
- permission_hierarchy
- product_barcodes_view

### Explicitly out of scope for this repo

- raw image ingestion
- OCR extraction
- model-specific prompting logic
- direct camera, receipt, or photo parsing inside `grocy-mcp`

## Track A: Workflow-Enabling Core

### [x] CP01 - Roadmap rewrite

- Implemented as the checkpoint ledger in this file
- Includes the operating model and shared merge gate

### [x] CP02 - Stable workflow JSON policy

- Implemented in [2026-04-01-grocy-mcp-workflow-design.md](./docs/specs/2026-04-01-grocy-mcp-workflow-design.md)
- Documents the stable preview/apply JSON contracts and the no-raw-image boundary

### [x] CP03 - Batch product matching preview

- Implemented as:
  - `workflow_match_products_preview_tool`
  - `grocy workflow match-products-preview`
- Uses the documented barcode -> exact name -> substring matching policy

### [x] CP04 - Bulk stock intake preview/apply

- Implemented as:
  - `workflow_stock_intake_preview_tool`
  - `workflow_stock_intake_apply_tool`
  - CLI parity under `grocy workflow`
- Apply steps accept explicit product IDs only

### [x] CP05 - Shopping reconciliation preview/apply

- Implemented as:
  - `workflow_shopping_reconcile_preview_tool`
  - `workflow_shopping_reconcile_apply_tool`
  - CLI parity under `grocy workflow`
- Apply actions remain explicit and preview-driven

### [x] CP06 - LLM workflow docs and examples

- README now includes receipt, grocery-photo, and pantry-audit examples
- Sample prompts are documented for ChatGPT and Claude

## Track B: Remaining Grocy Feature Coverage

### [x] CP07 - Shopping metadata coverage

- Implemented via the first-class `catalog` surface for:
  - `shopping_lists`
  - `shopping_locations`
- CLI:
  - `grocy catalog list shopping-lists`
  - `grocy catalog list shopping-locations`
- MCP:
  - `catalog_list_tool`
  - `catalog_details_tool`
  - `catalog_create_tool`
  - `catalog_update_tool`

### [x] CP08 - Quantity units, conversions, product groups, price history

- Implemented via the `catalog` surface for:
  - `quantity_units`
  - `quantity_unit_conversions`
  - `product_groups`
  - `products_last_purchased`
  - `products_average_price`

### [x] CP09 - Batteries

- Implemented as first-class CLI/MCP coverage for:
  - list
  - details
  - due / overdue views
  - charge action
  - charge-cycle history
  - undo charge-cycle
  - create / update
- Replacement remains a generic update concern because Grocy does not expose a dedicated replacement route in the API surface used here

### [x] CP10 - Equipment

- Implemented as first-class CLI/MCP coverage for:
  - list
  - details
  - create
  - update
- Linked battery visibility is included when the equipment record exposes a battery reference

### [x] CP11 - Task categories and assignment-aware flows

- `task_categories` are supported through `catalog`
- Task list formatting and JSON output now preserve assignee context where the API returns it
- Calendar summaries also include assignee-aware task/chore context

### [x] CP12 - Meal-plan sections and richer planning

- `meal_plan_sections` are supported through `catalog`
- `meal-plan summary` adds date-range and section-aware reporting
- MCP parity exists through `meal_plan_summary_tool`

### [x] CP13 - Calendar-oriented read models

- Implemented as:
  - `calendar_summary_tool`
  - `calendar_ical_tool`
  - `calendar_sharing_link_tool`
  - CLI parity under `grocy calendar`
- This remains read-only by design

### [x] CP14 - Files and print/export

- Implemented as scoped file-group support for:
  - product pictures
  - recipe pictures
  - equipment manuals
  - user files/pictures
- Implemented print helpers for:
  - stock entry labels
  - product labels
  - recipe labels
  - chore labels
  - battery labels
  - shopping-list thermal output

### [x] CP15 - Search/discovery helpers

- Implemented as:
  - `grocy discover search`
  - `grocy discover describe-entity`
  - `grocy discover fields`
  - MCP parity through `discover_candidates_tool`, `describe_entity_tool`, and `discover_fields_tool`
- Supported high-value candidate search domains include products, recipes, chores, locations, and tasks

## Track C: 1.0 Readiness

### [x] CP16 - 1.0 readiness

- Compatibility promise and support policy documented in [SUPPORT.md](./SUPPORT.md)
- Current authoritative docs are:
  - [2026-04-01-grocy-mcp-design.md](./docs/specs/2026-04-01-grocy-mcp-design.md)
  - [2026-04-01-grocy-mcp-implementation.md](./docs/specs/2026-04-01-grocy-mcp-implementation.md)
  - [2026-04-01-grocy-mcp-workflow-design.md](./docs/specs/2026-04-01-grocy-mcp-workflow-design.md)
- Coverage matrix in this file is now complete enough to distinguish first-class vs generic-only support

## What "Complete Enough for 1.0" Looks Like

The project is ready for a confident `1.0` when:

- command and tool behavior is predictable and well-tested
- workflow JSON contracts are documented and stable enough for scripting and LLM orchestration
- common Grocy household flows do not require generic CRUD as the default path
- docs clearly separate first-class support from generic-only support
- contributors can extend the project without creating doc/code drift
