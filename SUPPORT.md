# Support Policy

`grocy-mcp` is moving toward a stable `1.0` surface. This file defines what is treated as compatibility-sensitive and what may still evolve.

## Stability Promise

The following surfaces should be treated as compatibility-sensitive:

- MCP tool names
- CLI command names
- workflow JSON contracts documented in:
  - [2026-04-01-grocy-mcp-workflow-design.md](./docs/specs/2026-04-01-grocy-mcp-workflow-design.md)
- documented catalog, calendar, file, print, and discovery command/tool behaviors

For these surfaces:

- additive changes are preferred over breaking renames
- behavior changes should be documented in `CHANGELOG.md`
- any future breaking change should come with a migration note

## Runtime Support

Current supported baselines:

- Python `3.11+`
- Grocy `v4.4.1+`

The project assumes a Grocy instance with API-key access enabled.

## Authoritative Documentation

The current source of truth for design and implementation is:

- [2026-04-01-grocy-mcp-design.md](./docs/specs/2026-04-01-grocy-mcp-design.md)
- [2026-04-01-grocy-mcp-implementation.md](./docs/specs/2026-04-01-grocy-mcp-implementation.md)
- [2026-04-01-grocy-mcp-workflow-design.md](./docs/specs/2026-04-01-grocy-mcp-workflow-design.md)

Older dated specs remain useful as historical artifacts, but they are not the primary source of truth.

## Release Checklist

Before cutting a release:

1. Run `pytest -q`
2. Run `ruff check src tests`
3. Run `ruff format --check src tests`
4. Ensure README, roadmap, and current design/implementation docs match the code
5. Ensure any changed workflow JSON contract is reflected in the workflow design doc
6. Update `CHANGELOG.md`
7. Confirm CLI and MCP parity for newly added first-class surfaces
