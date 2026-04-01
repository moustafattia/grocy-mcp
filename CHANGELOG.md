# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Nothing yet.

## [0.2.0] - 2026-04-01

### Added

- **Workflow contracts**: stable preview/apply JSON schemas for chat- and vision-driven Grocy workflows
- **Workflow tools**: product-match preview, stock-intake preview/apply, and shopping-reconcile preview/apply in both MCP and CLI surfaces
- **Workflow design docs**: new current design doc describing the two-layer architecture and no-raw-image boundary
- **Catalog surface**: first-class metadata access for shopping lists, shopping locations, quantity units, quantity-unit conversions, product groups, task categories, meal-plan sections, products-last-purchased, and products-average-price
- **Batteries**: list/details, due and overdue views, charge-cycle history, charge and undo-cycle actions, plus create/update flows
- **Equipment**: list/details/create/update with linked battery visibility
- **Calendar helpers**: combined planning summary, iCal export, and sharing-link access
- **Files**: scoped file-group download/upload/delete helpers for Grocy-managed files
- **Print helpers**: stock-entry, product, recipe, chore, battery, and shopping-list thermal print triggers
- **Discovery helpers**: candidate search, entity description, and field discovery for safer generic CRUD usage
- **Support policy**: release checklist and compatibility guidance in `SUPPORT.md`
- **Locations**: list and create storage locations (with freezer flag)
- **Stock journal**: view recent stock transaction history, optionally filtered by product
- **Tasks**: list, create, complete, and delete tasks (separate from chores)
- **Meal plan**: list, add, and remove meal plan entries; `meal-plan shopping` workflow
  to add missing ingredients for all planned recipes to the shopping list
- **Recipe editing**: update recipe name/description, add/remove ingredients by product name
- **Recipe create by name**: create recipes with ingredients specified by product name
  instead of numeric IDs
- **Recipe consume preview**: dry-run showing what stock would be deducted with OK/SHORT status
- **Shopping list ergonomics**: `set-amount` and `set-note` commands for quick edits
  without raw JSON
- **`--json` flag**: global CLI option for machine-readable JSON output on all list/view commands
- **`--url` / `--api-key` flags**: top-level CLI config overrides
- **Short option flags**: `-l`, `-a`, `-n`, `-d`, `-i`, `-r` across relevant commands
- **JSON validation**: clear error messages for malformed JSON arguments (exit code 2)
- **Entity tool split**: `entity_manage_tool` split into `entity_create_tool`,
  `entity_update_tool`, `entity_delete_tool` for safer agent use
- **GitHub Actions CI**: lint, test (Python 3.11/3.12/3.13), and build verification
- **Integration test support**: opt-in tests gated on `GROCY_URL` + `GROCY_API_KEY`

### Changed

- Roadmap rewritten as a checkpoint ledger with Track A/B/C execution slices and merge gates
- Roadmap completed through CP16 with a finished coverage matrix
- README updated to document workflow contracts, external LLM/image handoff, new CLI groups, and richer examples
- Current design and implementation docs rewritten as the authoritative source of truth
- MCP tool descriptions rewritten for AI agent readability with examples and cross-references
- Output formatting standardized: consistent empty states, quoted names, bracket IDs, em-dash separators
- Removed unused `client.search_products()` and `client.update_recipe()` methods
- Replaced `Optional[]` with `str | None` union syntax throughout CLI

## [0.1.1] - 2026-03-31

### Fixed

- Shopping list add now forwards `list_id` and `note` to client
- Chore execution now forwards `done_by` to client
- Removed unused `--json` CLI flag that was advertised but not implemented
- CLI tests rewritten to avoid unawaited coroutine warnings
- Unused imports removed

### Changed

- README and design docs aligned with current implementation

## [0.1.0] - 2026-03-31

### Added

- Initial release with 30 MCP tools and full CLI
- Stock management: overview, expiring, add, consume, transfer, inventory, open, search, barcode
- Shopping list: view, add, update, remove, clear, add-missing
- Recipes: list, details, fulfillment, consume, add-to-shopping, create
- Chores: list, overdue, execute, undo, create
- System: info, entity list, entity manage (create/update/delete)
- Name-to-ID resolution for products, recipes, chores, and locations
- Async HTTP client with retry logic for transient errors
- Configuration from CLI args, environment variables, or TOML file
- stdio and streamable-http MCP transports
