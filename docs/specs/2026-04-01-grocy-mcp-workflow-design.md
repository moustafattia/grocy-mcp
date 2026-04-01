# grocy-mcp Workflow Design

Date: 2026-04-01
Status: Current

## Purpose

This document defines the workflow-oriented JSON contracts used by `grocy-mcp`
for chat-driven and vision-assisted Grocy interactions.

The design goal is to keep image interpretation outside this repository while
making `grocy-mcp` the stable Grocy-facing execution layer.

## Architecture Split

`grocy-mcp` does not ingest raw images, OCR payloads, or model-specific vision
responses.

Instead, the external layer does this:

1. interpret chat, receipt text, or images
2. convert that interpretation into normalized JSON items
3. call workflow preview tools in `grocy-mcp`
4. confirm explicit Grocy IDs
5. call workflow apply tools with explicit IDs only

This keeps the repository:

- model-agnostic
- easier to test
- safer for mutations
- useful for both AI clients and non-AI automation

## Stable v1 Contracts

### Normalized input item

Used by preview tools only.

```json
{
  "label": "whole milk",
  "quantity": 2,
  "unit_text": "cartons",
  "barcode": "5000112637922",
  "note": "organic"
}
```

Rules:

- `label` is required and must be non-empty
- `quantity` defaults to `1.0` and must be greater than `0`
- `unit_text`, `barcode`, and `note` are optional
- preview tools never mutate Grocy

### Preview result item

Returned by product-match and stock-intake preview tools.

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

Rules:

- `status` is one of `matched`, `ambiguous`, `unmatched`
- `matched_product_id` and `matched_product_name` are present only for `matched`
- `candidates` contains all plausible products in order of the selected matching stage
- `suggested_amount` comes from the normalized item quantity

### Confirmed apply item

Used by stock-intake apply and shopping-reconcile preview.

```json
{
  "product_id": 12,
  "amount": 2,
  "note": "organic"
}
```

Rules:

- apply tools accept explicit Grocy IDs only
- apply tools do not re-resolve names
- `note` is accepted as workflow metadata in CP04, but is not currently persisted
  to Grocy stock transactions by this repo

### Shopping reconcile preview action

Returned by shopping-reconcile preview.

```json
{
  "shopping_item_id": 5,
  "action": "set_amount",
  "previous_amount": 3,
  "new_amount": 1
}
```

### Shopping reconcile apply action

Used by shopping-reconcile apply.

```json
{
  "shopping_item_id": 5,
  "action": "set_amount",
  "new_amount": 1
}
```

Rules:

- `action` is `remove` or `set_amount`
- `new_amount` is required only for `set_amount`
- apply actions are explicit and come from a prior preview step

## Matching Policy

Preview tools use this exact policy:

1. exact barcode match
2. exact normalized product-name match
3. case-insensitive substring match

If a stage returns:

- exactly one product: `matched`
- more than one product: `ambiguous`
- zero products: continue to the next stage

If all stages return zero products: `unmatched`

Preview/apply separation is strict:

- preview tools can resolve
- apply tools cannot resolve

## Initial Workflow Surface

The first workflow-oriented surface consists of:

- `workflow_match_products_preview`
- `workflow_stock_intake_preview`
- `workflow_stock_intake_apply`
- `workflow_shopping_reconcile_preview`
- `workflow_shopping_reconcile_apply`

CLI parity exists under:

- `grocy workflow match-products-preview`
- `grocy workflow stock-intake-preview`
- `grocy workflow stock-intake-apply`
- `grocy workflow shopping-reconcile-preview`
- `grocy workflow shopping-reconcile-apply`

## Example External Flow

Receipt flow:

1. ChatGPT or Claude extracts normalized items from receipt text or image
2. Call `workflow_match_products_preview`
3. Resolve ambiguous or unmatched items with the user
4. Call `workflow_stock_intake_apply` with explicit `product_id` values
5. Call `workflow_shopping_reconcile_preview`
6. Confirm shopping-list actions
7. Call `workflow_shopping_reconcile_apply`

Pantry audit flow:

1. External model interprets visible products from a pantry photo
2. Call `workflow_match_products_preview`
3. Review matches without mutating Grocy

## Relationship To The Broader Surface

The broader roadmap checkpoints for batteries, equipment, shopping metadata,
calendar, files, print, and discovery are now implemented elsewhere in the
codebase and documented in the current design/implementation docs.

This document remains narrowly focused on the stable workflow JSON layer.

If a future change introduces additional stable workflow contracts, this
document should be updated in the same PR.
