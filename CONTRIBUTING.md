# Contributing to grocy-mcp

Thank you for your interest in contributing. This guide covers the basics.

## Getting started

```bash
git clone https://github.com/moustafattia/grocy-mcp
cd grocy-mcp
pip install -e ".[dev]"
```

## Running checks

Before submitting a PR, make sure everything passes:

```bash
ruff check src/ tests/
ruff format --check src/ tests/
pytest -v
```

## Code style

- Python 3.11+, use `str | None` (not `Optional`)
- `from __future__ import annotations` at the top of every module
- Line length: 100 characters
- Google-style docstrings on public functions
- snake_case for functions/variables, PascalCase for classes

## Architecture

All business logic lives in `src/grocy_mcp/core/`. Both the MCP server and CLI
call into these shared modules. If you add a new feature:

1. Add the core logic in `core/`
2. Wire it into `mcp/server.py` (MCP tool)
3. Wire it into `cli/app.py` (CLI command)
4. Add tests in `tests/`

## Testing

- Use `pytest-asyncio` — all async tests run automatically
- Mock HTTP calls with `respx` or `unittest.mock.AsyncMock`
- No real Grocy instance is needed for unit tests
- Integration tests in `test_integration.py` are opt-in (set `GROCY_URL` and `GROCY_API_KEY`)

## What to work on

Check [ROADMAP.md](./ROADMAP.md) for prioritized tasks, or look at open issues.

Good areas for contributions:

- New Grocy domain coverage (batteries, equipment, product groups, etc.)
- CLI usability improvements
- MCP tool ergonomics
- Tests for edge cases
- Documentation and examples

## Pull requests

- Keep PRs focused on a single concern
- Include tests for new functionality
- Make sure `ruff check` and `pytest` pass
- Write a clear commit message explaining what and why
