# grocy-mcp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `grocy-mcp`, a Python package providing an MCP server (30 tools) and CLI for AI agents and humans to control Grocy stock, shopping lists, recipes, and chores.

**Architecture:** Three layers -- thin async httpx client wraps the Grocy REST API, core modules implement business logic (name resolution, formatting), and two interface layers (FastMCP server + Typer CLI) consume the core. Shared config via env vars / TOML file.

**Tech Stack:** Python 3.11+, httpx, FastMCP, Typer, Pydantic, respx (testing), platformdirs

**Spec:** `docs/specs/2026-03-31-grocy-mcp-design.md`

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Build config, dependencies, entry points (`grocy-mcp`, `grocy`) |
| `src/grocy_mcp/__init__.py` | Package version export |
| `src/grocy_mcp/exceptions.py` | Typed exceptions: `GrocyError`, `GrocyAuthError`, `GrocyValidationError`, `GrocyNotFoundError`, `GrocyServerError` |
| `src/grocy_mcp/models.py` | Pydantic models: `Product`, `ProductBarcode`, `StockEntry`, `ShoppingListItem`, `Recipe`, `RecipeIngredient`, `Chore`, `ChoreExecution`, `SystemInfo` |
| `src/grocy_mcp/config.py` | Load config from env / TOML file / CLI flags. Single `Config` dataclass. |
| `src/grocy_mcp/client.py` | `GrocyClient` async class -- all HTTP calls, auth, retries, error mapping |
| `src/grocy_mcp/core/__init__.py` | Empty |
| `src/grocy_mcp/core/resolve.py` | `resolve_product`, `resolve_recipe`, `resolve_chore`, `resolve_location` -- name-to-ID resolution shared across all core modules |
| `src/grocy_mcp/core/stock.py` | Stock operations: overview, expiring, add, consume, transfer, inventory, open, search, barcode |
| `src/grocy_mcp/core/shopping.py` | Shopping list: view, add, update, remove, clear, add-missing |
| `src/grocy_mcp/core/recipes.py` | Recipe: list, details, fulfillment, consume, add-to-shopping, create |
| `src/grocy_mcp/core/chores.py` | Chore: list, overdue, execute, undo, create |
| `src/grocy_mcp/core/system.py` | System info, generic entity list/manage |
| `src/grocy_mcp/mcp/__init__.py` | Empty |
| `src/grocy_mcp/mcp/server.py` | FastMCP server -- registers all 30 tools, stdio + streamable-http entry point |
| `src/grocy_mcp/cli/__init__.py` | Empty |
| `src/grocy_mcp/cli/app.py` | Typer app -- `stock`, `shopping`, `recipes`, `chores`, `system`, `entity` subcommand groups |
| `tests/conftest.py` | Shared fixtures: mock `GrocyClient`, sample data factories |
| `tests/test_client.py` | Client unit tests: CRUD, stock, shopping, recipe, chore methods + error mapping + retries |
| `tests/test_resolve.py` | Name resolution tests: exact, substring, multiple, zero matches, numeric ID |
| `tests/test_stock.py` | Stock core tests |
| `tests/test_shopping.py` | Shopping core tests |
| `tests/test_recipes.py` | Recipe core tests |
| `tests/test_chores.py` | Chore core tests |
| `tests/test_system.py` | System core tests |
| `tests/test_mcp.py` | MCP server tool tests via FastMCP test client |
| `tests/test_cli.py` | CLI tests via Typer CliRunner |

---

### Task 1: Project Scaffold & Packaging

**Files:**
- Create: `pyproject.toml`
- Create: `src/grocy_mcp/__init__.py`
- Create: `src/grocy_mcp/exceptions.py`
- Create: `src/grocy_mcp/models.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "grocy-mcp"
version = "0.1.0"
description = "MCP server and CLI for Grocy - control stock, shopping lists, recipes and chores via AI agents"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [{ name = "Moustafa Attia" }]
keywords = ["grocy", "mcp", "cli", "home-automation", "ai-agents"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
dependencies = [
    "httpx>=0.27",
    "fastmcp>=2.0",
    "typer>=0.12",
    "pydantic>=2.0",
    "platformdirs>=4.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "respx>=0.22",
    "ruff>=0.8",
]

[project.scripts]
grocy-mcp = "grocy_mcp.mcp.server:main"
grocy = "grocy_mcp.cli.app:main"

[project.urls]
Homepage = "https://github.com/moustafattia/grocy-mcp"
Repository = "https://github.com/moustafattia/grocy-mcp"
Issues = "https://github.com/moustafattia/grocy-mcp/issues"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create package init**

`src/grocy_mcp/__init__.py`:
```python
"""grocy-mcp: MCP server and CLI for Grocy."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create exceptions**

`src/grocy_mcp/exceptions.py`:
```python
"""Typed exceptions for Grocy API errors."""


class GrocyError(Exception):
    """Base exception for all Grocy errors."""


class GrocyAuthError(GrocyError):
    """Raised on 401/403 -- bad or missing API key."""


class GrocyValidationError(GrocyError):
    """Raised on 400 -- invalid request data."""


class GrocyNotFoundError(GrocyError):
    """Raised on 404 -- entity not found."""


class GrocyServerError(GrocyError):
    """Raised on 500 -- Grocy server error."""


class GrocyResolveError(GrocyError):
    """Raised when name-to-ID resolution fails (zero or ambiguous matches)."""
```

- [ ] **Step 4: Create Pydantic models**

`src/grocy_mcp/models.py`:
```python
"""Pydantic models for Grocy API entities."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: int
    name: str
    description: str | None = None
    location_id: int | None = None
    min_stock_amount: float = 0
    qu_id_purchase: int | None = None
    qu_id_stock: int | None = None

    model_config = {"extra": "allow"}


class ProductBarcode(BaseModel):
    id: int
    product_id: int
    barcode: str
    qu_id: int | None = None
    amount: float | None = None

    model_config = {"extra": "allow"}


class StockEntry(BaseModel):
    id: int
    product_id: int
    amount: float
    best_before_date: str | None = None
    location_id: int | None = None
    open: int = 0
    price: float | None = None

    model_config = {"extra": "allow"}


class ShoppingListItem(BaseModel):
    id: int
    shopping_list_id: int = 1
    product_id: int | None = None
    amount: float = 1
    note: str | None = None
    done: int = 0

    model_config = {"extra": "allow"}


class RecipeIngredient(BaseModel):
    id: int
    recipe_id: int
    product_id: int
    amount: float = 1
    qu_id: int | None = None
    note: str | None = None

    model_config = {"extra": "allow"}


class Recipe(BaseModel):
    id: int
    name: str
    description: str | None = None
    instructions: str | None = None
    base_servings: int = Field(default=1, alias="base_servings")
    ingredients: list[RecipeIngredient] = []

    model_config = {"extra": "allow", "populate_by_name": True}


class Chore(BaseModel):
    id: int
    name: str
    period_type: str | None = None
    period_interval: int | None = None
    next_execution_assigned_to_user_id: int | None = None
    next_estimated_execution_time: datetime | None = None

    model_config = {"extra": "allow"}


class ChoreExecution(BaseModel):
    id: int
    chore_id: int
    executed_time: datetime
    done_by_user_id: int | None = None

    model_config = {"extra": "allow"}


class SystemInfo(BaseModel):
    grocy_version: dict
    php_version: str
    sqlite_version: str
    os: str

    model_config = {"extra": "allow"}
```

- [ ] **Step 5: Create empty package directories**

Create empty `__init__.py` files:
- `src/grocy_mcp/core/__init__.py`
- `src/grocy_mcp/mcp/__init__.py`
- `src/grocy_mcp/cli/__init__.py`

- [ ] **Step 6: Install package in dev mode and verify**

Run: `cd C:/Workspace/grocy-mcp && pip install -e ".[dev]"`
Expected: package installs successfully with all dependencies

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/
git commit -m "feat: project scaffold with packaging, models, and exceptions"
```

---

### Task 2: Configuration

**Files:**
- Create: `src/grocy_mcp/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write config tests**

`tests/test_config.py`:
```python
"""Tests for configuration loading."""

import os
from unittest.mock import patch

from grocy_mcp.config import load_config


def test_config_from_env():
    with patch.dict(os.environ, {"GROCY_URL": "http://localhost:9192", "GROCY_API_KEY": "testkey"}):
        config = load_config()
    assert config.url == "http://localhost:9192"
    assert config.api_key == "testkey"


def test_config_missing_url_raises():
    with patch.dict(os.environ, {}, clear=True):
        try:
            load_config()
            assert False, "Should have raised"
        except ValueError as e:
            assert "GROCY_URL" in str(e)


def test_config_overrides():
    with patch.dict(os.environ, {"GROCY_URL": "http://env-url", "GROCY_API_KEY": "envkey"}):
        config = load_config(url="http://override-url")
    assert config.url == "http://override-url"
    assert config.api_key == "envkey"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_config.py -v`
Expected: FAIL -- `load_config` not implemented

- [ ] **Step 3: Implement config**

`src/grocy_mcp/config.py`:
```python
"""Configuration loading from env vars, TOML file, and CLI flags."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_dir


@dataclass(frozen=True)
class Config:
    url: str
    api_key: str


def _load_toml() -> dict:
    config_path = Path(user_config_dir("grocy-mcp")) / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("grocy", {})
    return {}


def load_config(
    url: str | None = None,
    api_key: str | None = None,
) -> Config:
    """Load config with priority: explicit args > env vars > TOML file."""
    toml = _load_toml()

    resolved_url = url or os.environ.get("GROCY_URL") or toml.get("url")
    resolved_key = api_key or os.environ.get("GROCY_API_KEY") or toml.get("api_key")

    if not resolved_url:
        raise ValueError(
            "Grocy URL not configured. Set GROCY_URL env var, pass --url, "
            "or add url to config file."
        )
    if not resolved_key:
        raise ValueError(
            "Grocy API key not configured. Set GROCY_API_KEY env var, pass --api-key, "
            "or add api_key to config file."
        )

    return Config(url=resolved_url.rstrip("/"), api_key=resolved_key)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/grocy_mcp/config.py tests/test_config.py
git commit -m "feat: configuration loading from env, TOML, and CLI flags"
```

---

### Task 3: API Client

**Files:**
- Create: `src/grocy_mcp/client.py`
- Create: `tests/conftest.py`
- Create: `tests/test_client.py`

- [ ] **Step 1: Create shared test fixtures**

`tests/conftest.py`:
```python
"""Shared test fixtures."""

import httpx
import pytest
import respx


@pytest.fixture
def base_url():
    return "http://grocy.test"


@pytest.fixture
def api_key():
    return "test-api-key"


@pytest.fixture
def mock_api():
    with respx.mock(base_url="http://grocy.test/api") as respx_mock:
        yield respx_mock
```

- [ ] **Step 2: Write client tests**

`tests/test_client.py`:
```python
"""Tests for GrocyClient."""

import httpx
import pytest
import respx

from grocy_mcp.client import GrocyClient
from grocy_mcp.exceptions import (
    GrocyAuthError,
    GrocyNotFoundError,
    GrocyServerError,
    GrocyValidationError,
)


@pytest.fixture
async def client(base_url, api_key, mock_api):
    async with GrocyClient(base_url, api_key) as c:
        yield c


async def test_get_objects(client, mock_api):
    mock_api.get("/objects/products").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Milk"}])
    )
    result = await client.get_objects("products")
    assert result == [{"id": 1, "name": "Milk"}]


async def test_get_object(client, mock_api):
    mock_api.get("/objects/products/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "name": "Milk"})
    )
    result = await client.get_object("products", 1)
    assert result == {"id": 1, "name": "Milk"}


async def test_create_object(client, mock_api):
    mock_api.post("/objects/products").mock(
        return_value=httpx.Response(200, json={"created_object_id": 5})
    )
    result = await client.create_object("products", {"name": "Bread"})
    assert result == 5


async def test_delete_object(client, mock_api):
    mock_api.delete("/objects/products/1").mock(
        return_value=httpx.Response(204)
    )
    await client.delete_object("products", 1)


async def test_get_stock(client, mock_api):
    mock_api.get("/stock").mock(
        return_value=httpx.Response(200, json=[{"product_id": 1, "amount": 3}])
    )
    result = await client.get_stock()
    assert len(result) == 1


async def test_add_stock(client, mock_api):
    mock_api.post("/stock/products/1/add").mock(
        return_value=httpx.Response(200, json=[{"id": 10}])
    )
    result = await client.add_stock(1, 2.0)
    assert result is not None


async def test_consume_stock(client, mock_api):
    mock_api.post("/stock/products/1/consume").mock(
        return_value=httpx.Response(200, json=[{"id": 10}])
    )
    await client.consume_stock(1, 1.0)


async def test_get_volatile_stock(client, mock_api):
    mock_api.get("/stock/volatile").mock(
        return_value=httpx.Response(200, json={
            "expiring_products": [], "expired_products": [],
            "missing_products": [], "overdue_products": []
        })
    )
    result = await client.get_volatile_stock()
    assert "expiring_products" in result


async def test_auth_error(client, mock_api):
    mock_api.get("/objects/products").mock(return_value=httpx.Response(401))
    with pytest.raises(GrocyAuthError):
        await client.get_objects("products")


async def test_validation_error(client, mock_api):
    mock_api.post("/objects/products").mock(return_value=httpx.Response(400, json={"error_message": "bad"}))
    with pytest.raises(GrocyValidationError):
        await client.create_object("products", {})


async def test_not_found_error(client, mock_api):
    mock_api.get("/objects/products/999").mock(return_value=httpx.Response(404))
    with pytest.raises(GrocyNotFoundError):
        await client.get_object("products", 999)


async def test_server_error(client, mock_api):
    mock_api.get("/stock").mock(return_value=httpx.Response(500))
    with pytest.raises(GrocyServerError):
        await client.get_stock()


async def test_retry_on_502(client, mock_api):
    route = mock_api.get("/stock")
    route.side_effect = [
        httpx.Response(502),
        httpx.Response(200, json=[]),
    ]
    result = await client.get_stock()
    assert result == []
    assert route.call_count == 2


async def test_auth_header(client, mock_api, api_key):
    mock_api.get("/objects/products").mock(return_value=httpx.Response(200, json=[]))
    await client.get_objects("products")
    request = mock_api.calls[0].request
    assert request.headers["GROCY-API-KEY"] == api_key
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_client.py -v`
Expected: FAIL -- `GrocyClient` not implemented

- [ ] **Step 4: Implement the client**

`src/grocy_mcp/client.py`:
```python
"""Async HTTP client for the Grocy REST API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from grocy_mcp.exceptions import (
    GrocyAuthError,
    GrocyNotFoundError,
    GrocyServerError,
    GrocyValidationError,
)

_TRANSIENT_CODES = {502, 503, 504}
_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.0


class GrocyClient:
    """Thin async wrapper around the Grocy REST API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base = base_url.rstrip("/") + "/api"
        self._client = httpx.AsyncClient(
            base_url=self._base,
            headers={"GROCY-API-KEY": api_key, "Accept": "application/json"},
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0),
        )

    async def __aenter__(self) -> GrocyClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await self._client.request(method, path, **kwargs)
            except httpx.TransportError as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_BACKOFF)
                    continue
                raise GrocyServerError(f"Connection failed: {e}") from e

            if resp.status_code in _TRANSIENT_CODES and attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_BACKOFF)
                continue

            self._raise_for_status(resp)
            return resp

        raise GrocyServerError("Max retries exceeded") if last_exc is None else last_exc

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return
        body = resp.text
        match resp.status_code:
            case 401 | 403:
                raise GrocyAuthError(f"Auth failed ({resp.status_code}): {body}")
            case 400:
                raise GrocyValidationError(f"Validation error: {body}")
            case 404:
                raise GrocyNotFoundError(f"Not found: {body}")
            case code if code >= 500:
                raise GrocyServerError(f"Server error ({code}): {body}")

    # --- Generic CRUD ---

    async def get_objects(self, entity: str, query: str | None = None) -> list[dict]:
        params = {"query[]": query} if query else None
        resp = await self._request("GET", f"/objects/{entity}", params=params)
        return resp.json()

    async def get_object(self, entity: str, obj_id: int) -> dict:
        resp = await self._request("GET", f"/objects/{entity}/{obj_id}")
        return resp.json()

    async def create_object(self, entity: str, data: dict) -> int:
        resp = await self._request("POST", f"/objects/{entity}", json=data)
        return resp.json()["created_object_id"]

    async def update_object(self, entity: str, obj_id: int, data: dict) -> None:
        await self._request("PUT", f"/objects/{entity}/{obj_id}", json=data)

    async def delete_object(self, entity: str, obj_id: int) -> None:
        await self._request("DELETE", f"/objects/{entity}/{obj_id}")

    # --- Stock ---

    async def get_stock(self) -> list[dict]:
        resp = await self._request("GET", "/stock")
        return resp.json()

    async def get_stock_product(self, product_id: int) -> dict:
        resp = await self._request("GET", f"/stock/products/{product_id}")
        return resp.json()

    async def add_stock(self, product_id: int, amount: float, **kwargs: Any) -> Any:
        data = {"amount": amount, **kwargs}
        resp = await self._request("POST", f"/stock/products/{product_id}/add", json=data)
        return resp.json()

    async def consume_stock(self, product_id: int, amount: float, **kwargs: Any) -> Any:
        data = {"amount": amount, **kwargs}
        resp = await self._request("POST", f"/stock/products/{product_id}/consume", json=data)
        return resp.json()

    async def transfer_stock(
        self, product_id: int, amount: float, to_location_id: int
    ) -> Any:
        data = {"amount": amount, "location_id_to": to_location_id}
        resp = await self._request(
            "POST", f"/stock/products/{product_id}/transfer", json=data
        )
        return resp.json()

    async def inventory_stock(self, product_id: int, new_amount: float) -> Any:
        data = {"new_amount": new_amount}
        resp = await self._request(
            "POST", f"/stock/products/{product_id}/inventory", json=data
        )
        return resp.json()

    async def open_stock(self, product_id: int, amount: float = 1) -> Any:
        data = {"amount": amount}
        resp = await self._request(
            "POST", f"/stock/products/{product_id}/open", json=data
        )
        return resp.json()

    async def get_volatile_stock(self) -> dict:
        resp = await self._request("GET", "/stock/volatile")
        return resp.json()

    async def get_stock_by_barcode(self, barcode: str) -> dict:
        resp = await self._request(
            "GET", f"/stock/products/by-barcode/{barcode}"
        )
        return resp.json()

    # --- Shopping Lists ---

    async def get_shopping_list(self, list_id: int = 1) -> list[dict]:
        items = await self.get_objects("shopping_list")
        return [i for i in items if i.get("shopping_list_id") == list_id]

    async def add_shopping_list_item(
        self,
        product_id: int,
        amount: float = 1,
        shopping_list_id: int = 1,
        note: str | None = None,
    ) -> int:
        data = {
            "product_id": product_id,
            "amount": amount,
            "shopping_list_id": shopping_list_id,
        }
        if note:
            data["note"] = note
        return await self.create_object("shopping_list", data)

    async def update_shopping_list_item(self, item_id: int, data: dict) -> None:
        await self.update_object("shopping_list", item_id, data)

    async def remove_shopping_list_item(self, item_id: int) -> None:
        await self.delete_object("shopping_list", item_id)

    async def clear_shopping_list(self, list_id: int = 1) -> None:
        await self._request(
            "POST",
            "/stock/shoppinglist/clear",
            json={"list_id": list_id},
        )

    async def add_missing_products_to_shopping_list(self, list_id: int = 1) -> None:
        await self._request(
            "POST",
            "/stock/shoppinglist/add-missing-products",
            json={"list_id": list_id},
        )

    # --- Recipes ---

    async def get_recipes(self) -> list[dict]:
        return await self.get_objects("recipes")

    async def get_recipe(self, recipe_id: int) -> dict:
        return await self.get_object("recipes", recipe_id)

    async def get_recipe_fulfillment(self, recipe_id: int) -> dict:
        resp = await self._request("GET", f"/recipes/{recipe_id}/fulfillment")
        return resp.json()

    async def consume_recipe(self, recipe_id: int) -> None:
        await self._request("POST", f"/recipes/{recipe_id}/consume")

    async def add_recipe_to_shopping_list(self, recipe_id: int) -> None:
        await self._request(
            "POST",
            f"/recipes/{recipe_id}/add-not-fulfilled-products-to-shoppinglist",
        )

    async def search_products(self, query: str) -> list[dict]:
        products = await self.get_objects("products")
        query_lower = query.lower()
        matches = [p for p in products if query_lower in p.get("name", "").lower()]
        barcodes = await self.get_objects("product_barcodes")
        barcode_ids = {
            b["product_id"] for b in barcodes if query_lower in b.get("barcode", "").lower()
        }
        for p in products:
            if p["id"] in barcode_ids and p not in matches:
                matches.append(p)
        return matches

    async def update_recipe(self, recipe_id: int, data: dict) -> None:
        await self.update_object("recipes", recipe_id, data)

    # --- Chores ---

    async def get_chores(self) -> list[dict]:
        resp = await self._request("GET", "/chores")
        return resp.json()

    async def get_chore(self, chore_id: int) -> dict:
        resp = await self._request("GET", f"/chores/{chore_id}")
        return resp.json()

    async def execute_chore(self, chore_id: int, done_by: int | None = None) -> None:
        data: dict[str, Any] = {}
        if done_by is not None:
            data["done_by"] = done_by
        await self._request("POST", f"/chores/{chore_id}/execute", json=data)

    async def get_chore_executions(self, chore_id: int) -> list[dict]:
        all_execs = await self.get_objects("chores_log")
        return [e for e in all_execs if e.get("chore_id") == chore_id]

    async def undo_chore_execution(self, execution_id: int) -> None:
        await self._request("POST", f"/chores/executions/{execution_id}/undo")

    # --- System ---

    async def get_system_info(self) -> dict:
        resp = await self._request("GET", "/system/info")
        return resp.json()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_client.py -v`
Expected: All passed

- [ ] **Step 6: Commit**

```bash
git add src/grocy_mcp/client.py tests/conftest.py tests/test_client.py
git commit -m "feat: async Grocy API client with error handling and retries"
```

---

### Task 4: Name-to-ID Resolution

**Files:**
- Create: `src/grocy_mcp/core/resolve.py`
- Create: `tests/test_resolve.py`

- [ ] **Step 1: Write resolve tests**

`tests/test_resolve.py`:
```python
"""Tests for name-to-ID resolution."""

from unittest.mock import AsyncMock

import pytest

from grocy_mcp.core.resolve import resolve_entity
from grocy_mcp.exceptions import GrocyResolveError


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Milk"},
        {"id": 2, "name": "Milk 2%"},
        {"id": 3, "name": "Almond Milk"},
        {"id": 4, "name": "Bread"},
    ]
    return client


async def test_resolve_by_numeric_id(mock_client):
    result = await resolve_entity(mock_client, "products", "4")
    assert result == 4
    mock_client.get_objects.assert_not_called()


async def test_resolve_exact_match(mock_client):
    result = await resolve_entity(mock_client, "products", "Milk")
    assert result == 1


async def test_resolve_exact_match_case_insensitive(mock_client):
    result = await resolve_entity(mock_client, "products", "milk")
    assert result == 1


async def test_resolve_single_substring_match(mock_client):
    result = await resolve_entity(mock_client, "products", "Bread")
    assert result == 4


async def test_resolve_ambiguous_without_exact(mock_client):
    with pytest.raises(GrocyResolveError, match="Multiple"):
        await resolve_entity(mock_client, "products", "ilk")


async def test_resolve_zero_matches(mock_client):
    with pytest.raises(GrocyResolveError, match="No .* found"):
        await resolve_entity(mock_client, "products", "Cheese")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_resolve.py -v`
Expected: FAIL -- `resolve_entity` not defined

- [ ] **Step 3: Implement resolver**

`src/grocy_mcp/core/resolve.py`:
```python
"""Name-to-ID resolution for Grocy entities."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient
from grocy_mcp.exceptions import GrocyResolveError


async def resolve_entity(
    client: GrocyClient,
    entity: str,
    name_or_id: str,
    name_field: str = "name",
) -> int:
    """Resolve a human-readable name (or numeric ID string) to an entity ID.

    Resolution logic:
    1. If numeric string, return it as int directly (no API call).
    2. Fetch all entities, case-insensitive substring match.
    3. Zero matches -> error with suggestions.
    4. One match -> return ID.
    5. Multiple matches -> if one is exact (case-insensitive), use it. Otherwise error.
    """
    if name_or_id.isdigit():
        return int(name_or_id)

    items = await client.get_objects(entity)
    query_lower = name_or_id.lower()

    matches = [
        item for item in items
        if query_lower in item.get(name_field, "").lower()
    ]

    if not matches:
        all_names = [item.get(name_field, "?") for item in items[:10]]
        suggestion = ", ".join(all_names)
        raise GrocyResolveError(
            f"No {entity} found matching '{name_or_id}'. "
            f"Available: {suggestion}"
        )

    if len(matches) == 1:
        return matches[0]["id"]

    # Multiple matches -- check for exact match
    exact = [m for m in matches if m.get(name_field, "").lower() == query_lower]
    if len(exact) == 1:
        return exact[0]["id"]

    names = [f"{m.get(name_field)} (ID {m['id']})" for m in matches]
    raise GrocyResolveError(
        f"Multiple {entity} match '{name_or_id}': {', '.join(names)}. "
        f"Please be more specific."
    )


async def resolve_product(client: GrocyClient, name_or_id: str) -> int:
    return await resolve_entity(client, "products", name_or_id)


async def resolve_recipe(client: GrocyClient, name_or_id: str) -> int:
    return await resolve_entity(client, "recipes", name_or_id)


async def resolve_chore(client: GrocyClient, name_or_id: str) -> int:
    return await resolve_entity(client, "chores", name_or_id)


async def resolve_location(client: GrocyClient, name_or_id: str) -> int:
    return await resolve_entity(client, "locations", name_or_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_resolve.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/grocy_mcp/core/resolve.py tests/test_resolve.py
git commit -m "feat: name-to-ID resolution with substring matching"
```

---

### Task 5: Core Stock Module

**Files:**
- Create: `src/grocy_mcp/core/stock.py`
- Create: `tests/test_stock.py`

- [ ] **Step 1: Write stock tests**

`tests/test_stock.py`:
```python
"""Tests for stock core module."""

from unittest.mock import AsyncMock

import pytest

from grocy_mcp.core.stock import (
    stock_overview,
    stock_expiring,
    stock_product_info,
    stock_add,
    stock_consume,
    stock_transfer,
    stock_inventory,
    stock_open,
    stock_search,
    stock_barcode_lookup,
)


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_stock.return_value = [
        {
            "product_id": 1,
            "amount": 3,
            "product": {"id": 1, "name": "Milk", "location_id": 1},
        }
    ]
    client.get_volatile_stock.return_value = {
        "expiring_products": [{"product_id": 1, "amount": 1, "product": {"name": "Milk"}}],
        "expired_products": [],
        "missing_products": [],
        "overdue_products": [],
    }
    client.get_objects.return_value = [
        {"id": 1, "name": "Milk"},
        {"id": 2, "name": "Bread"},
    ]
    client.add_stock.return_value = [{"id": 10}]
    client.consume_stock.return_value = [{"id": 10}]
    return client


async def test_stock_overview(mock_client):
    result = await stock_overview(mock_client)
    assert "Milk" in result
    assert "3" in result


async def test_stock_expiring(mock_client):
    result = await stock_expiring(mock_client)
    assert "Milk" in result


async def test_stock_add(mock_client):
    result = await stock_add(mock_client, "Milk", 2.0)
    assert "added" in result.lower() or "Milk" in result
    mock_client.add_stock.assert_called_once_with(1, 2.0)


async def test_stock_consume(mock_client):
    result = await stock_consume(mock_client, "Milk", 1.0)
    assert "consumed" in result.lower() or "Milk" in result
    mock_client.consume_stock.assert_called_once()


async def test_stock_search(mock_client):
    result = await stock_search(mock_client, "Milk")
    assert "Milk" in result


async def test_stock_product_info(mock_client):
    mock_client.get_stock_product.return_value = {
        "stock_amount": 3,
        "product": {"id": 1, "name": "Milk"},
        "default_location": {"name": "Fridge"},
    }
    result = await stock_product_info(mock_client, "Milk")
    assert "Milk" in result
    assert "3" in result


async def test_stock_transfer(mock_client):
    mock_client.get_objects.side_effect = lambda entity: {
        "products": [{"id": 1, "name": "Milk"}],
        "locations": [{"id": 2, "name": "Pantry"}],
    }.get(entity, [])
    mock_client.transfer_stock.return_value = None
    result = await stock_transfer(mock_client, "Milk", 1.0, "Pantry")
    assert "Transferred" in result


async def test_stock_inventory(mock_client):
    mock_client.inventory_stock.return_value = None
    result = await stock_inventory(mock_client, "Milk", 5.0)
    assert "5" in result


async def test_stock_open(mock_client):
    mock_client.open_stock.return_value = None
    result = await stock_open(mock_client, "Milk")
    assert "opened" in result.lower()


async def test_stock_barcode_lookup(mock_client):
    mock_client.get_stock_by_barcode.return_value = {
        "product": {"name": "Milk"}, "stock_amount": 3,
    }
    result = await stock_barcode_lookup(mock_client, "1234567890")
    assert "Milk" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_stock.py -v`
Expected: FAIL

- [ ] **Step 3: Implement stock core**

`src/grocy_mcp/core/stock.py`:
```python
"""Stock operations core module."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_product, resolve_location


async def stock_overview(client: GrocyClient) -> str:
    stock = await client.get_stock()
    if not stock:
        return "Stock is empty."
    lines = ["**Current Stock:**", ""]
    for entry in stock:
        product = entry.get("product", {})
        name = product.get("name", f"Product {entry['product_id']}")
        amount = entry.get("amount", 0)
        lines.append(f"- {name}: {amount}")
    return "\n".join(lines)


async def stock_expiring(client: GrocyClient) -> str:
    volatile = await client.get_volatile_stock()
    sections = []
    for key, label in [
        ("expiring_products", "Expiring Soon"),
        ("expired_products", "Expired"),
        ("missing_products", "Missing / Below Min Stock"),
        ("overdue_products", "Overdue"),
    ]:
        items = volatile.get(key, [])
        if items:
            lines = [f"**{label}:**"]
            for item in items:
                name = item.get("product", {}).get("name", f"ID {item.get('product_id')}")
                amount = item.get("amount", "")
                lines.append(f"- {name} (amount: {amount})")
            sections.append("\n".join(lines))
    return "\n\n".join(sections) if sections else "No expiring, expired, or missing products."


async def stock_product_info(client: GrocyClient, product: str) -> str:
    product_id = await resolve_product(client, product)
    info = await client.get_stock_product(product_id)
    stock_amount = info.get("stock_amount", 0)
    product_data = info.get("product", {})
    name = product_data.get("name", product)
    location = info.get("default_location", {}).get("name", "Unknown")
    lines = [
        f"**{name}**",
        f"- In stock: {stock_amount}",
        f"- Default location: {location}",
    ]
    if info.get("best_before_date"):
        lines.append(f"- Next best before: {info['best_before_date']}")
    return "\n".join(lines)


async def stock_add(
    client: GrocyClient,
    product: str,
    amount: float,
    best_before_date: str | None = None,
    price: float | None = None,
    location: str | None = None,
) -> str:
    product_id = await resolve_product(client, product)
    kwargs: dict = {}
    if best_before_date:
        kwargs["best_before_date"] = best_before_date
    if price is not None:
        kwargs["price"] = price
    if location:
        location_id = await resolve_location(client, location)
        kwargs["location_id"] = location_id
    await client.add_stock(product_id, amount, **kwargs)
    return f"Added {amount} of '{product}' to stock."


async def stock_consume(
    client: GrocyClient,
    product: str,
    amount: float,
    spoiled: bool = False,
) -> str:
    product_id = await resolve_product(client, product)
    await client.consume_stock(product_id, amount, spoiled=spoiled)
    return f"Consumed {amount} of '{product}' from stock."


async def stock_transfer(
    client: GrocyClient,
    product: str,
    amount: float,
    to_location: str,
) -> str:
    product_id = await resolve_product(client, product)
    location_id = await resolve_location(client, to_location)
    await client.transfer_stock(product_id, amount, location_id)
    return f"Transferred {amount} of '{product}' to '{to_location}'."


async def stock_inventory(
    client: GrocyClient, product: str, new_amount: float
) -> str:
    product_id = await resolve_product(client, product)
    await client.inventory_stock(product_id, new_amount)
    return f"Inventory for '{product}' set to {new_amount}."


async def stock_open(
    client: GrocyClient, product: str, amount: float = 1
) -> str:
    product_id = await resolve_product(client, product)
    await client.open_stock(product_id, amount)
    return f"Marked {amount} of '{product}' as opened."


async def stock_search(client: GrocyClient, query: str) -> str:
    products = await client.get_objects("products")
    query_lower = query.lower()
    matches = [p for p in products if query_lower in p.get("name", "").lower()]

    # Also search barcodes
    barcodes = await client.get_objects("product_barcodes")
    barcode_product_ids = {
        b["product_id"] for b in barcodes if query_lower in b.get("barcode", "").lower()
    }
    barcode_matches = [p for p in products if p["id"] in barcode_product_ids and p not in matches]
    matches.extend(barcode_matches)

    if not matches:
        return f"No products matching '{query}'."
    lines = [f"**Search results for '{query}':**"]
    for p in matches:
        lines.append(f"- {p['name']} (ID {p['id']})")
    return "\n".join(lines)


async def stock_barcode_lookup(client: GrocyClient, barcode: str) -> str:
    info = await client.get_stock_by_barcode(barcode)
    product = info.get("product", {})
    name = product.get("name", "Unknown")
    stock_amount = info.get("stock_amount", 0)
    return f"**{name}** (barcode: {barcode})\n- In stock: {stock_amount}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_stock.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/grocy_mcp/core/stock.py tests/test_stock.py
git commit -m "feat: stock core module with overview, add, consume, search"
```

---

### Task 6: Core Shopping Module

**Files:**
- Create: `src/grocy_mcp/core/shopping.py`
- Create: `tests/test_shopping.py`

- [ ] **Step 1: Write shopping tests**

`tests/test_shopping.py`:
```python
"""Tests for shopping list core module."""

from unittest.mock import AsyncMock

import pytest

from grocy_mcp.core.shopping import (
    shopping_list_view,
    shopping_list_add,
    shopping_list_update,
    shopping_list_remove,
    shopping_list_clear,
    shopping_list_add_missing,
)


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_shopping_list.return_value = [
        {"id": 1, "product_id": 10, "amount": 2, "note": None, "done": 0},
    ]
    client.get_objects.return_value = [
        {"id": 10, "name": "Milk"},
        {"id": 11, "name": "Bread"},
    ]
    client.add_shopping_list_item.return_value = 5
    return client


async def test_shopping_list_view(mock_client):
    result = await shopping_list_view(mock_client)
    assert "Milk" in result


async def test_shopping_list_add(mock_client):
    result = await shopping_list_add(mock_client, "Bread", 3)
    assert "Bread" in result
    mock_client.add_shopping_list_item.assert_called_once()


async def test_shopping_list_remove(mock_client):
    result = await shopping_list_remove(mock_client, 1)
    assert "removed" in result.lower()
    mock_client.remove_shopping_list_item.assert_called_once_with(1)


async def test_shopping_list_clear(mock_client):
    result = await shopping_list_clear(mock_client)
    assert "cleared" in result.lower()
    mock_client.clear_shopping_list.assert_called_once()


async def test_shopping_list_update(mock_client):
    result = await shopping_list_update(mock_client, 1, amount=5, note="urgent")
    assert "Updated" in result
    mock_client.update_shopping_list_item.assert_called_once()


async def test_shopping_list_add_missing(mock_client):
    result = await shopping_list_add_missing(mock_client)
    assert "missing" in result.lower()
    mock_client.add_missing_products_to_shopping_list.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_shopping.py -v`
Expected: FAIL

- [ ] **Step 3: Implement shopping core**

`src/grocy_mcp/core/shopping.py`:
```python
"""Shopping list core module."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_product


async def _product_name_map(client: GrocyClient) -> dict[int, str]:
    products = await client.get_objects("products")
    return {p["id"]: p["name"] for p in products}


async def shopping_list_view(client: GrocyClient, list_id: int = 1) -> str:
    items = await client.get_shopping_list(list_id)
    if not items:
        return "Shopping list is empty."
    names = await _product_name_map(client)
    lines = [f"**Shopping List (ID {list_id}):**", ""]
    for item in items:
        name = names.get(item.get("product_id"), item.get("note") or "Unknown")
        amount = item.get("amount", 1)
        done = " [done]" if item.get("done") else ""
        note = f" ({item['note']})" if item.get("note") else ""
        lines.append(f"- {name} x{amount}{note}{done}  [item_id: {item['id']}]")
    return "\n".join(lines)


async def shopping_list_add(
    client: GrocyClient,
    product: str,
    amount: float = 1,
    list_id: int = 1,
    note: str | None = None,
) -> str:
    product_id = await resolve_product(client, product)
    await client.add_shopping_list_item(product_id, amount, list_id, note)
    return f"Added '{product}' x{amount} to shopping list."


async def shopping_list_update(
    client: GrocyClient,
    item_id: int,
    amount: float | None = None,
    note: str | None = None,
) -> str:
    data: dict = {}
    if amount is not None:
        data["amount"] = amount
    if note is not None:
        data["note"] = note
    await client.update_shopping_list_item(item_id, data)
    return f"Updated shopping list item {item_id}."


async def shopping_list_remove(client: GrocyClient, item_id: int) -> str:
    await client.remove_shopping_list_item(item_id)
    return f"Removed item {item_id} from shopping list."


async def shopping_list_clear(client: GrocyClient, list_id: int = 1) -> str:
    await client.clear_shopping_list(list_id)
    return f"Cleared shopping list {list_id}."


async def shopping_list_add_missing(client: GrocyClient, list_id: int = 1) -> str:
    await client.add_missing_products_to_shopping_list(list_id)
    return "Added all missing/below-min-stock products to shopping list."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_shopping.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/grocy_mcp/core/shopping.py tests/test_shopping.py
git commit -m "feat: shopping list core module"
```

---

### Task 7: Core Recipes Module

**Files:**
- Create: `src/grocy_mcp/core/recipes.py`
- Create: `tests/test_recipes.py`

- [ ] **Step 1: Write recipe tests**

`tests/test_recipes.py`:
```python
"""Tests for recipes core module."""

from unittest.mock import AsyncMock

import pytest

from grocy_mcp.core.recipes import (
    recipes_list,
    recipe_details,
    recipe_fulfillment,
    recipe_consume,
    recipe_add_to_shopping,
    recipe_create,
)


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_recipes.return_value = [
        {"id": 1, "name": "Pancakes", "description": "Fluffy pancakes"},
        {"id": 2, "name": "Pasta", "description": "Simple pasta"},
    ]
    client.get_recipe.return_value = {
        "id": 1,
        "name": "Pancakes",
        "description": "Fluffy pancakes",
        "base_servings": 4,
    }
    client.get_objects.side_effect = lambda entity: {
        "recipes": [
            {"id": 1, "name": "Pancakes"},
            {"id": 2, "name": "Pasta"},
        ],
        "recipes_pos": [
            {"id": 1, "recipe_id": 1, "product_id": 10, "amount": 2},
        ],
        "products": [
            {"id": 10, "name": "Flour"},
        ],
    }.get(entity, [])
    client.get_recipe_fulfillment.return_value = {
        "recipe_id": 1,
        "need_fulfilled": True,
        "missing_products_count": 0,
    }
    client.create_object.return_value = 3
    return client


async def test_recipes_list(mock_client):
    result = await recipes_list(mock_client)
    assert "Pancakes" in result
    assert "Pasta" in result


async def test_recipe_details(mock_client):
    result = await recipe_details(mock_client, "Pancakes")
    assert "Pancakes" in result


async def test_recipe_fulfillment(mock_client):
    result = await recipe_fulfillment(mock_client, "Pancakes")
    assert "fulfilled" in result.lower() or "can be made" in result.lower()


async def test_recipe_consume(mock_client):
    result = await recipe_consume(mock_client, "Pancakes")
    assert "consumed" in result.lower() or "Pancakes" in result


async def test_recipe_add_to_shopping(mock_client):
    result = await recipe_add_to_shopping(mock_client, "Pancakes")
    assert "Pancakes" in result
    mock_client.add_recipe_to_shopping_list.assert_called_once()


async def test_recipe_create(mock_client):
    result = await recipe_create(
        mock_client,
        name="Omelette",
        ingredients=[{"product": "Flour", "amount": 3}],
        instructions="Mix and cook.",
    )
    assert "created" in result.lower() or "Omelette" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_recipes.py -v`
Expected: FAIL

- [ ] **Step 3: Implement recipes core**

`src/grocy_mcp/core/recipes.py`:
```python
"""Recipes core module."""

from __future__ import annotations

from typing import Any

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_recipe, resolve_product


async def recipes_list(client: GrocyClient) -> str:
    recipes = await client.get_recipes()
    if not recipes:
        return "No recipes found."
    lines = ["**Recipes:**", ""]
    for r in recipes:
        desc = f" - {r['description']}" if r.get("description") else ""
        lines.append(f"- {r['name']} (ID {r['id']}){desc}")
    return "\n".join(lines)


async def recipe_details(client: GrocyClient, recipe: str) -> str:
    recipe_id = await resolve_recipe(client, recipe)
    data = await client.get_recipe(recipe_id)
    ingredients = await client.get_objects("recipes_pos")
    recipe_ingredients = [i for i in ingredients if i.get("recipe_id") == recipe_id]

    products = await client.get_objects("products")
    product_names = {p["id"]: p["name"] for p in products}

    lines = [
        f"**{data['name']}**",
        f"Servings: {data.get('base_servings', 1)}",
    ]
    if data.get("description"):
        lines.append(f"Description: {data['description']}")

    if recipe_ingredients:
        lines.append("\n**Ingredients:**")
        for ing in recipe_ingredients:
            name = product_names.get(ing.get("product_id"), f"Product {ing.get('product_id')}")
            amount = ing.get("amount", "")
            note = f" ({ing['note']})" if ing.get("note") else ""
            lines.append(f"- {name}: {amount}{note}")

    return "\n".join(lines)


async def recipe_fulfillment(client: GrocyClient, recipe: str) -> str:
    recipe_id = await resolve_recipe(client, recipe)
    data = await client.get_recipe_fulfillment(recipe_id)
    fulfilled = data.get("need_fulfilled", False)
    missing = data.get("missing_products_count", 0)
    if fulfilled:
        return f"Recipe can be made with current stock."
    return f"Recipe cannot be made. Missing {missing} product(s)."


async def recipe_consume(client: GrocyClient, recipe: str) -> str:
    recipe_id = await resolve_recipe(client, recipe)
    await client.consume_recipe(recipe_id)
    return f"Consumed ingredients for recipe '{recipe}' from stock."


async def recipe_add_to_shopping(client: GrocyClient, recipe: str) -> str:
    recipe_id = await resolve_recipe(client, recipe)
    await client.add_recipe_to_shopping_list(recipe_id)
    return f"Added missing ingredients for '{recipe}' to shopping list."


async def recipe_create(
    client: GrocyClient,
    name: str,
    ingredients: list[dict[str, Any]],
    instructions: str = "",
    servings: int = 1,
) -> str:
    recipe_id = await client.create_object("recipes", {
        "name": name,
        "description": instructions,
        "base_servings": servings,
    })

    for ing in ingredients:
        product_id = await resolve_product(client, ing["product"])
        await client.create_object("recipes_pos", {
            "recipe_id": recipe_id,
            "product_id": product_id,
            "amount": ing.get("amount", 1),
        })

    return f"Created recipe '{name}' (ID {recipe_id}) with {len(ingredients)} ingredient(s)."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_recipes.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/grocy_mcp/core/recipes.py tests/test_recipes.py
git commit -m "feat: recipes core module with CRUD and fulfillment"
```

---

### Task 8: Core Chores Module

**Files:**
- Create: `src/grocy_mcp/core/chores.py`
- Create: `tests/test_chores.py`

- [ ] **Step 1: Write chore tests**

`tests/test_chores.py`:
```python
"""Tests for chores core module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from grocy_mcp.core.chores import (
    chores_list,
    chores_overdue,
    chore_execute,
    chore_undo,
    chore_create,
)


@pytest.fixture
def mock_client():
    now = datetime.now(tz=timezone.utc)
    client = AsyncMock()
    client.get_chores.return_value = [
        {
            "chore_id": 1,
            "chore": {"id": 1, "name": "Vacuum"},
            "next_estimated_execution_time": (now + timedelta(days=1)).isoformat(),
        },
        {
            "chore_id": 2,
            "chore": {"id": 2, "name": "Dishes"},
            "next_estimated_execution_time": (now - timedelta(days=2)).isoformat(),
        },
    ]
    client.get_objects.return_value = [
        {"id": 1, "name": "Vacuum"},
        {"id": 2, "name": "Dishes"},
    ]
    client.get_chore_executions.return_value = [
        {"id": 100, "chore_id": 1, "executed_time": now.isoformat()},
    ]
    client.create_object.return_value = 3
    return client


async def test_chores_list(mock_client):
    result = await chores_list(mock_client)
    assert "Vacuum" in result
    assert "Dishes" in result


async def test_chores_overdue(mock_client):
    result = await chores_overdue(mock_client)
    assert "Dishes" in result


async def test_chore_execute(mock_client):
    result = await chore_execute(mock_client, "Vacuum")
    assert "Vacuum" in result
    mock_client.execute_chore.assert_called_once_with(1, None)


async def test_chore_undo(mock_client):
    result = await chore_undo(mock_client, "Vacuum")
    assert "undone" in result.lower() or "Vacuum" in result
    mock_client.undo_chore_execution.assert_called_once_with(100)


async def test_chore_create(mock_client):
    result = await chore_create(mock_client, "Laundry", "weekly", 7)
    assert "created" in result.lower() or "Laundry" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_chores.py -v`
Expected: FAIL

- [ ] **Step 3: Implement chores core**

`src/grocy_mcp/core/chores.py`:
```python
"""Chores core module."""

from __future__ import annotations

from datetime import datetime, timezone

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_chore
from grocy_mcp.exceptions import GrocyError


async def chores_list(client: GrocyClient) -> str:
    chores = await client.get_chores()
    if not chores:
        return "No chores found."
    lines = ["**Chores:**", ""]
    for entry in chores:
        chore = entry.get("chore", {})
        name = chore.get("name", f"Chore {entry.get('chore_id')}")
        next_exec = entry.get("next_estimated_execution_time", "Not scheduled")
        lines.append(f"- {name}: next due {next_exec}")
    return "\n".join(lines)


async def chores_overdue(client: GrocyClient) -> str:
    chores = await client.get_chores()
    now = datetime.now(tz=timezone.utc)
    overdue = []
    for entry in chores:
        next_time = entry.get("next_estimated_execution_time")
        if next_time:
            try:
                dt = datetime.fromisoformat(next_time)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt < now:
                    overdue.append(entry)
            except (ValueError, TypeError):
                continue

    if not overdue:
        return "No overdue chores."
    lines = ["**Overdue Chores:**", ""]
    for entry in overdue:
        chore = entry.get("chore", {})
        name = chore.get("name", f"Chore {entry.get('chore_id')}")
        next_time = entry.get("next_estimated_execution_time", "")
        lines.append(f"- {name} (due: {next_time})")
    return "\n".join(lines)


async def chore_execute(
    client: GrocyClient, chore: str, done_by: int | None = None
) -> str:
    chore_id = await resolve_chore(client, chore)
    await client.execute_chore(chore_id, done_by)
    return f"Chore '{chore}' marked as done."


async def chore_undo(client: GrocyClient, chore: str) -> str:
    chore_id = await resolve_chore(client, chore)
    executions = await client.get_chore_executions(chore_id)
    if not executions:
        raise GrocyError(f"No executions found for chore '{chore}' to undo.")
    # Get the most recent execution
    latest = max(executions, key=lambda e: e.get("executed_time", ""))
    await client.undo_chore_execution(latest["id"])
    return f"Last execution of chore '{chore}' has been undone."


async def chore_create(
    client: GrocyClient,
    name: str,
    period_type: str = "manually",
    period_interval: int | None = None,
    assigned_to: int | None = None,
) -> str:
    data: dict = {
        "name": name,
        "period_type": period_type,
    }
    if period_interval is not None:
        data["period_interval"] = period_interval
    if assigned_to is not None:
        data["next_execution_assigned_to_user_id"] = assigned_to
    chore_id = await client.create_object("chores", data)
    return f"Created chore '{name}' (ID {chore_id})."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_chores.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/grocy_mcp/core/chores.py tests/test_chores.py
git commit -m "feat: chores core module with overdue detection and undo"
```

---

### Task 9: Core System Module

**Files:**
- Create: `src/grocy_mcp/core/system.py`
- Create: `tests/test_system.py`

- [ ] **Step 1: Write system tests**

`tests/test_system.py`:
```python
"""Tests for system core module."""

from unittest.mock import AsyncMock

import pytest

from grocy_mcp.core.system import system_info, entity_list, entity_manage


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_system_info.return_value = {
        "grocy_version": {"Version": "4.4.1"},
        "php_version": "8.2",
        "os": "Linux",
    }
    client.get_objects.return_value = [
        {"id": 1, "name": "Fridge"},
        {"id": 2, "name": "Pantry"},
    ]
    client.create_object.return_value = 3
    return client


async def test_system_info(mock_client):
    result = await system_info(mock_client)
    assert "4.4.1" in result
    assert "PHP" in result


async def test_entity_list(mock_client):
    result = await entity_list(mock_client, "locations")
    assert "Fridge" in result
    assert "Pantry" in result


async def test_entity_list_empty(mock_client):
    mock_client.get_objects.return_value = []
    result = await entity_list(mock_client, "locations")
    assert "No locations found" in result


async def test_entity_manage_create(mock_client):
    result = await entity_manage(mock_client, "create", "locations", data={"name": "Garage"})
    assert "Created" in result
    assert "3" in result


async def test_entity_manage_update(mock_client):
    result = await entity_manage(mock_client, "update", "locations", 1, {"name": "Big Fridge"})
    assert "Updated" in result


async def test_entity_manage_delete(mock_client):
    result = await entity_manage(mock_client, "delete", "locations", 1)
    assert "Deleted" in result


async def test_entity_manage_unknown_action(mock_client):
    result = await entity_manage(mock_client, "drop", "locations")
    assert "Unknown" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_system.py -v`
Expected: FAIL

- [ ] **Step 3: Implement system core**

`src/grocy_mcp/core/system.py`:
```python
"""System and generic entity operations."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient


async def system_info(client: GrocyClient) -> str:
    info = await client.get_system_info()
    version = info.get("grocy_version", {}).get("Version", "Unknown")
    php = info.get("php_version", "Unknown")
    os_info = info.get("os", "Unknown")
    return f"**Grocy {version}**\n- PHP: {php}\n- OS: {os_info}"


async def entity_list(client: GrocyClient, entity_type: str) -> str:
    items = await client.get_objects(entity_type)
    if not items:
        return f"No {entity_type} found."
    lines = [f"**{entity_type}:**", ""]
    for item in items:
        name = item.get("name", f"ID {item.get('id', '?')}")
        lines.append(f"- {name} (ID {item.get('id')})")
    return "\n".join(lines)


async def entity_manage(
    client: GrocyClient,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    data: dict | None = None,
) -> str:
    match action:
        case "create":
            new_id = await client.create_object(entity_type, data or {})
            return f"Created {entity_type} (ID {new_id})."
        case "update":
            if entity_id is None:
                return "Error: entity ID required for update."
            await client.update_object(entity_type, entity_id, data or {})
            return f"Updated {entity_type} ID {entity_id}."
        case "delete":
            if entity_id is None:
                return "Error: entity ID required for delete."
            await client.delete_object(entity_type, entity_id)
            return f"Deleted {entity_type} ID {entity_id}."
        case _:
            return f"Unknown action '{action}'. Use create, update, or delete."
```

- [ ] **Step 2: Commit**

```bash
git add src/grocy_mcp/core/system.py tests/test_system.py
git commit -m "feat: system info and generic entity management core"
```

---

### Task 10: MCP Server

**Files:**
- Create: `src/grocy_mcp/mcp/server.py`
- Create: `tests/test_mcp.py`

- [ ] **Step 1: Write MCP server tests**

`tests/test_mcp.py`:
```python
"""Tests for MCP server tools."""

from unittest.mock import AsyncMock, patch

import pytest

from grocy_mcp.mcp.server import create_mcp_server


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_stock.return_value = [
        {"product_id": 1, "amount": 3, "product": {"id": 1, "name": "Milk", "location_id": 1}}
    ]
    client.get_volatile_stock.return_value = {
        "expiring_products": [], "expired_products": [],
        "missing_products": [], "overdue_products": [],
    }
    client.get_objects.return_value = [{"id": 1, "name": "Milk"}]
    client.get_system_info.return_value = {
        "grocy_version": {"Version": "4.4.1"},
        "php_version": "8.2",
        "os": "Linux",
    }
    return client


async def test_server_has_tools():
    with patch("grocy_mcp.mcp.server._get_client") as mock_get:
        mock_get.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
        server = create_mcp_server()
    # Server should be created successfully
    assert server is not None
    assert server.name == "grocy-mcp"
```

- [ ] **Step 2: Implement MCP server**

`src/grocy_mcp/mcp/server.py`:
```python
"""FastMCP server exposing Grocy tools."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP

from grocy_mcp.client import GrocyClient
from grocy_mcp.config import load_config
from grocy_mcp.core import stock, shopping, recipes, chores, system
from grocy_mcp.exceptions import GrocyError


@asynccontextmanager
async def _get_client():
    config = load_config()
    async with GrocyClient(config.url, config.api_key) as client:
        yield client


def create_mcp_server() -> FastMCP:
    mcp = FastMCP("grocy-mcp")

    # --- Stock tools ---

    @mcp.tool()
    async def stock_overview() -> str:
        """List all products currently in stock with quantities and locations."""
        async with _get_client() as client:
            return await stock.stock_overview(client)

    @mcp.tool()
    async def stock_expiring() -> str:
        """Show products that are expiring soon, already expired, or below minimum stock."""
        async with _get_client() as client:
            return await stock.stock_expiring(client)

    @mcp.tool()
    async def stock_product_info(product: str) -> str:
        """Get detailed stock info for a specific product.

        Args:
            product: Product name or numeric ID.
        """
        async with _get_client() as client:
            return await stock.stock_product_info(client, product)

    @mcp.tool()
    async def stock_add(
        product: str,
        amount: float,
        best_before: str | None = None,
        price: float | None = None,
        location: str | None = None,
    ) -> str:
        """Add stock for a product.

        Args:
            product: Product name or numeric ID.
            amount: Quantity to add.
            best_before: Best before date (YYYY-MM-DD). Optional.
            price: Purchase price per unit. Optional.
            location: Location name or ID. Optional (uses product default).
        """
        async with _get_client() as client:
            return await stock.stock_add(client, product, amount, best_before, price, location)

    @mcp.tool()
    async def stock_consume(product: str, amount: float, spoiled: bool = False) -> str:
        """Consume/use stock for a product.

        Args:
            product: Product name or numeric ID.
            amount: Quantity to consume.
            spoiled: Whether the consumed amount was spoiled.
        """
        async with _get_client() as client:
            return await stock.stock_consume(client, product, amount, spoiled)

    @mcp.tool()
    async def stock_transfer(product: str, amount: float, to_location: str) -> str:
        """Move stock between locations.

        Args:
            product: Product name or numeric ID.
            amount: Quantity to transfer.
            to_location: Destination location name or ID.
        """
        async with _get_client() as client:
            return await stock.stock_transfer(client, product, amount, to_location)

    @mcp.tool()
    async def stock_inventory(product: str, new_amount: float) -> str:
        """Set absolute stock amount for a product (inventory correction).

        Args:
            product: Product name or numeric ID.
            new_amount: The corrected total amount.
        """
        async with _get_client() as client:
            return await stock.stock_inventory(client, product, new_amount)

    @mcp.tool()
    async def stock_open(product: str, amount: float = 1) -> str:
        """Mark a product as opened.

        Args:
            product: Product name or numeric ID.
            amount: Number of units to mark as opened. Defaults to 1.
        """
        async with _get_client() as client:
            return await stock.stock_open(client, product, amount)

    @mcp.tool()
    async def stock_search(query: str) -> str:
        """Search products by name, barcode, or category.

        Args:
            query: Search query string.
        """
        async with _get_client() as client:
            return await stock.stock_search(client, query)

    @mcp.tool()
    async def stock_barcode_lookup(barcode: str) -> str:
        """Look up a product by its barcode.

        Args:
            barcode: The barcode string to look up.
        """
        async with _get_client() as client:
            return await stock.stock_barcode_lookup(client, barcode)

    # --- Shopping list tools ---

    @mcp.tool()
    async def shopping_list_view(list_id: int = 1) -> str:
        """View items on a shopping list.

        Args:
            list_id: Shopping list ID. Defaults to 1 (main list).
        """
        async with _get_client() as client:
            return await shopping.shopping_list_view(client, list_id)

    @mcp.tool()
    async def shopping_list_add(
        product: str, amount: float = 1, list_id: int = 1, note: str | None = None
    ) -> str:
        """Add an item to the shopping list.

        Args:
            product: Product name or numeric ID.
            amount: Quantity needed. Defaults to 1.
            list_id: Shopping list ID. Defaults to 1.
            note: Optional note for this item.
        """
        async with _get_client() as client:
            return await shopping.shopping_list_add(client, product, amount, list_id, note)

    @mcp.tool()
    async def shopping_list_update(
        item_id: int, amount: float | None = None, note: str | None = None
    ) -> str:
        """Update an existing shopping list item.

        Args:
            item_id: The shopping list item ID to update.
            amount: New quantity. Optional.
            note: New note. Optional.
        """
        async with _get_client() as client:
            return await shopping.shopping_list_update(client, item_id, amount, note)

    @mcp.tool()
    async def shopping_list_remove(item_id: int) -> str:
        """Remove an item from the shopping list.

        Args:
            item_id: The shopping list item ID to remove.
        """
        async with _get_client() as client:
            return await shopping.shopping_list_remove(client, item_id)

    @mcp.tool()
    async def shopping_list_clear(list_id: int = 1) -> str:
        """Clear all items from a shopping list.

        Args:
            list_id: Shopping list ID to clear. Defaults to 1.
        """
        async with _get_client() as client:
            return await shopping.shopping_list_clear(client, list_id)

    @mcp.tool()
    async def shopping_list_add_missing(list_id: int = 1) -> str:
        """Add all products that are below minimum stock to the shopping list.

        Args:
            list_id: Shopping list ID. Defaults to 1.
        """
        async with _get_client() as client:
            return await shopping.shopping_list_add_missing(client, list_id)

    # --- Recipe tools ---

    @mcp.tool()
    async def recipes_list() -> str:
        """List all recipes."""
        async with _get_client() as client:
            return await recipes.recipes_list(client)

    @mcp.tool()
    async def recipe_details(recipe: str) -> str:
        """Get a recipe with its ingredients and instructions.

        Args:
            recipe: Recipe name or numeric ID.
        """
        async with _get_client() as client:
            return await recipes.recipe_details(client, recipe)

    @mcp.tool()
    async def recipe_fulfillment(recipe: str) -> str:
        """Check if a recipe can be made with current stock.

        Args:
            recipe: Recipe name or numeric ID.
        """
        async with _get_client() as client:
            return await recipes.recipe_fulfillment(client, recipe)

    @mcp.tool()
    async def recipe_consume(recipe: str) -> str:
        """Consume the ingredients for a recipe from stock.

        Args:
            recipe: Recipe name or numeric ID.
        """
        async with _get_client() as client:
            return await recipes.recipe_consume(client, recipe)

    @mcp.tool()
    async def recipe_add_to_shopping(recipe: str) -> str:
        """Add missing ingredients for a recipe to the shopping list.

        Args:
            recipe: Recipe name or numeric ID.
        """
        async with _get_client() as client:
            return await recipes.recipe_add_to_shopping(client, recipe)

    @mcp.tool()
    async def recipe_create(
        name: str,
        ingredients: str,
        instructions: str = "",
        servings: int = 1,
    ) -> str:
        """Create a new recipe.

        Args:
            name: Recipe name.
            ingredients: JSON array of ingredients, e.g. [{"product": "Flour", "amount": 2}]
            instructions: Cooking instructions text.
            servings: Number of servings. Defaults to 1.
        """
        async with _get_client() as client:
            parsed = json.loads(ingredients)
            return await recipes.recipe_create(client, name, parsed, instructions, servings)

    # --- Chore tools ---

    @mcp.tool()
    async def chores_list() -> str:
        """List all chores with their next execution dates."""
        async with _get_client() as client:
            return await chores.chores_list(client)

    @mcp.tool()
    async def chores_overdue() -> str:
        """Show chores that are overdue."""
        async with _get_client() as client:
            return await chores.chores_overdue(client)

    @mcp.tool()
    async def chore_execute(chore: str, done_by: int | None = None) -> str:
        """Mark a chore as done.

        Args:
            chore: Chore name or numeric ID.
            done_by: User ID who completed the chore. Optional.
        """
        async with _get_client() as client:
            return await chores.chore_execute(client, chore, done_by)

    @mcp.tool()
    async def chore_undo(chore: str) -> str:
        """Undo the last execution of a chore.

        Args:
            chore: Chore name or numeric ID.
        """
        async with _get_client() as client:
            return await chores.chore_undo(client, chore)

    @mcp.tool()
    async def chore_create(
        name: str,
        period_type: str = "manually",
        period_interval: int | None = None,
        assigned_to: int | None = None,
    ) -> str:
        """Create a new chore.

        Args:
            name: Chore name.
            period_type: How often (manually, daily, weekly, monthly, yearly).
            period_interval: Interval between executions (e.g. 7 for weekly). Optional.
            assigned_to: User ID to assign. Optional.
        """
        async with _get_client() as client:
            return await chores.chore_create(client, name, period_type, period_interval, assigned_to)

    # --- System tools ---

    @mcp.tool()
    async def system_info() -> str:
        """Get Grocy version and system info."""
        async with _get_client() as client:
            return await system.system_info(client)

    @mcp.tool()
    async def entity_list(entity_type: str) -> str:
        """List any generic Grocy entity type (locations, quantity_units, product_groups, etc.).

        Args:
            entity_type: The entity type name (e.g. 'locations', 'quantity_units').
        """
        async with _get_client() as client:
            return await system.entity_list(client, entity_type)

    @mcp.tool()
    async def entity_manage(
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        data: str | None = None,
    ) -> str:
        """Create, update, or delete any generic Grocy entity.

        Args:
            action: One of 'create', 'update', 'delete'.
            entity_type: The entity type (e.g. 'locations', 'quantity_units').
            entity_id: Entity ID (required for update/delete).
            data: JSON object with entity data (required for create/update).
        """
        async with _get_client() as client:
            parsed = json.loads(data) if data else None
            return await system.entity_manage(client, action, entity_type, entity_id, parsed)

    return mcp


def main():
    """Entry point for the grocy-mcp command."""
    import sys

    server = create_mcp_server()

    transport = "stdio"
    port = 8765
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--transport" and i + 1 < len(args):
            transport = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        else:
            i += 1

    if transport == "streamable-http":
        server.run(transport="streamable-http", port=port)
    else:
        server.run(transport="stdio")
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_mcp.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/grocy_mcp/mcp/server.py tests/test_mcp.py
git commit -m "feat: MCP server with 30 tools for stock, shopping, recipes, chores"
```

---

### Task 11: CLI Application

**Files:**
- Create: `src/grocy_mcp/cli/app.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write CLI tests**

`tests/test_cli.py`:
```python
"""Tests for CLI application."""

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from grocy_mcp.cli.app import app

runner = CliRunner()


@patch("grocy_mcp.cli.app._run")
def test_stock_list(mock_run):
    mock_run.return_value = "**Current Stock:**\n- Milk: 3"
    result = runner.invoke(app, ["stock", "list"])
    assert result.exit_code == 0
    assert "Milk" in result.output


@patch("grocy_mcp.cli.app._run")
def test_shopping_list(mock_run):
    mock_run.return_value = "**Shopping List:**\n- Bread x2"
    result = runner.invoke(app, ["shopping", "list"])
    assert result.exit_code == 0
    assert "Bread" in result.output


@patch("grocy_mcp.cli.app._run")
def test_system_info(mock_run):
    mock_run.return_value = "**Grocy 4.4.1**"
    result = runner.invoke(app, ["system", "info"])
    assert result.exit_code == 0
    assert "4.4.1" in result.output


@patch("grocy_mcp.cli.app._run")
def test_stock_add(mock_run):
    mock_run.return_value = "Added 2.0 of 'Milk' to stock."
    result = runner.invoke(app, ["stock", "add", "Milk", "2"])
    assert result.exit_code == 0
    assert "Added" in result.output
```

- [ ] **Step 2: Implement CLI**

`src/grocy_mcp/cli/app.py`:
```python
"""Typer CLI application for Grocy."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Coroutine, Optional

import typer
from rich.console import Console

from grocy_mcp.client import GrocyClient
from grocy_mcp.config import load_config
from grocy_mcp.core import stock, shopping, recipes, chores, system
from grocy_mcp.exceptions import GrocyError

app = typer.Typer(name="grocy", help="CLI for Grocy - manage stock, shopping, recipes, and chores.")
stock_app = typer.Typer(help="Stock management")
shopping_app = typer.Typer(help="Shopping list management")
recipes_app = typer.Typer(help="Recipe management")
chores_app = typer.Typer(help="Chore management")
system_app = typer.Typer(help="System info")
entity_app = typer.Typer(help="Generic entity management")

app.add_typer(stock_app, name="stock")
app.add_typer(shopping_app, name="shopping")
app.add_typer(recipes_app, name="recipes")
app.add_typer(chores_app, name="chores")
app.add_typer(system_app, name="system")
app.add_typer(entity_app, name="entity")

console = Console()

# Global --json flag via callback
json_output = False

@app.callback()
def main_callback(use_json: bool = typer.Option(False, "--json", help="Output raw JSON instead of formatted text")):
    global json_output
    json_output = use_json


def _run(coro: Coroutine) -> Any:
    return asyncio.run(coro)


def _exec(coro: Coroutine) -> None:
    try:
        result = _run(coro)
        if json_output:
            console.print_json(data=result) if isinstance(result, (dict, list)) else console.print(result)
        else:
            console.print(result)
    except GrocyError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _client() -> GrocyClient:
    config = load_config()
    return GrocyClient(config.url, config.api_key)


# --- Stock ---

@stock_app.command("list")
def stock_list_cmd():
    """List all products in stock."""
    async def _inner():
        async with _client() as c:
            return await stock.stock_overview(c)
    _exec(_inner())


@stock_app.command("expiring")
def stock_expiring_cmd():
    """Show expiring, expired, and missing products."""
    async def _inner():
        async with _client() as c:
            return await stock.stock_expiring(c)
    _exec(_inner())


@stock_app.command("info")
def stock_info_cmd(product: str):
    """Get details for a specific product."""
    async def _inner():
        async with _client() as c:
            return await stock.stock_product_info(c, product)
    _exec(_inner())


@stock_app.command("add")
def stock_add_cmd(
    product: str,
    amount: float,
    best_before: Optional[str] = None,
    price: Optional[float] = None,
    location: Optional[str] = None,
):
    """Add stock for a product."""
    async def _inner():
        async with _client() as c:
            return await stock.stock_add(c, product, amount, best_before, price, location)
    _exec(_inner())


@stock_app.command("consume")
def stock_consume_cmd(product: str, amount: float, spoiled: bool = False):
    """Consume stock for a product."""
    async def _inner():
        async with _client() as c:
            return await stock.stock_consume(c, product, amount, spoiled)
    _exec(_inner())


@stock_app.command("transfer")
def stock_transfer_cmd(product: str, amount: float, to: str = typer.Option(..., "--to")):
    """Move stock between locations."""
    async def _inner():
        async with _client() as c:
            return await stock.stock_transfer(c, product, amount, to)
    _exec(_inner())


@stock_app.command("inventory")
def stock_inventory_cmd(product: str, amount: float):
    """Set absolute stock amount."""
    async def _inner():
        async with _client() as c:
            return await stock.stock_inventory(c, product, amount)
    _exec(_inner())


@stock_app.command("open")
def stock_open_cmd(product: str, amount: float = 1):
    """Mark product as opened."""
    async def _inner():
        async with _client() as c:
            return await stock.stock_open(c, product, amount)
    _exec(_inner())


@stock_app.command("search")
def stock_search_cmd(query: str):
    """Search products by name, barcode, or category."""
    async def _inner():
        async with _client() as c:
            return await stock.stock_search(c, query)
    _exec(_inner())


@stock_app.command("barcode")
def stock_barcode_cmd(barcode: str):
    """Look up a product by barcode."""
    async def _inner():
        async with _client() as c:
            return await stock.stock_barcode_lookup(c, barcode)
    _exec(_inner())


# --- Shopping ---

@shopping_app.command("list")
def shopping_list_cmd(list_id: int = 1):
    """View shopping list items."""
    async def _inner():
        async with _client() as c:
            return await shopping.shopping_list_view(c, list_id)
    _exec(_inner())


@shopping_app.command("add")
def shopping_add_cmd(product: str, amount: float = 1, list_id: int = 1, note: Optional[str] = None):
    """Add an item to the shopping list."""
    async def _inner():
        async with _client() as c:
            return await shopping.shopping_list_add(c, product, amount, list_id, note)
    _exec(_inner())


@shopping_app.command("update")
def shopping_update_cmd(
    item_id: int,
    amount: Optional[float] = typer.Option(None, "--amount"),
    note: Optional[str] = typer.Option(None, "--note"),
):
    """Update an existing shopping list item."""
    async def _inner():
        async with _client() as c:
            return await shopping.shopping_list_update(c, item_id, amount, note)
    _exec(_inner())


@shopping_app.command("remove")
def shopping_remove_cmd(item_id: int):
    """Remove an item from the shopping list."""
    async def _inner():
        async with _client() as c:
            return await shopping.shopping_list_remove(c, item_id)
    _exec(_inner())


@shopping_app.command("clear")
def shopping_clear_cmd(list_id: int = 1):
    """Clear all items from a shopping list."""
    async def _inner():
        async with _client() as c:
            return await shopping.shopping_list_clear(c, list_id)
    _exec(_inner())


@shopping_app.command("add-missing")
def shopping_add_missing_cmd(list_id: int = 1):
    """Add all below-min-stock products to the shopping list."""
    async def _inner():
        async with _client() as c:
            return await shopping.shopping_list_add_missing(c, list_id)
    _exec(_inner())


# --- Recipes ---

@recipes_app.command("list")
def recipes_list_cmd():
    """List all recipes."""
    async def _inner():
        async with _client() as c:
            return await recipes.recipes_list(c)
    _exec(_inner())


@recipes_app.command("show")
def recipes_show_cmd(recipe: str):
    """Get recipe details with ingredients."""
    async def _inner():
        async with _client() as c:
            return await recipes.recipe_details(c, recipe)
    _exec(_inner())


@recipes_app.command("check")
def recipes_check_cmd(recipe: str):
    """Check if a recipe can be made with current stock."""
    async def _inner():
        async with _client() as c:
            return await recipes.recipe_fulfillment(c, recipe)
    _exec(_inner())


@recipes_app.command("consume")
def recipes_consume_cmd(recipe: str):
    """Consume recipe ingredients from stock."""
    async def _inner():
        async with _client() as c:
            return await recipes.recipe_consume(c, recipe)
    _exec(_inner())


@recipes_app.command("to-shopping")
def recipes_to_shopping_cmd(recipe: str):
    """Add missing recipe ingredients to shopping list."""
    async def _inner():
        async with _client() as c:
            return await recipes.recipe_add_to_shopping(c, recipe)
    _exec(_inner())


@recipes_app.command("create")
def recipes_create_cmd(
    name: str,
    ingredients: str = typer.Option(..., "--ingredients", help='JSON array, e.g. \'[{"product":"Flour","amount":2}]\''),
    instructions: str = typer.Option("", "--instructions"),
    servings: int = 1,
):
    """Create a new recipe."""
    async def _inner():
        async with _client() as c:
            parsed = json.loads(ingredients)
            return await recipes.recipe_create(c, name, parsed, instructions, servings)
    _exec(_inner())


# --- Chores ---

@chores_app.command("list")
def chores_list_cmd():
    """List all chores."""
    async def _inner():
        async with _client() as c:
            return await chores.chores_list(c)
    _exec(_inner())


@chores_app.command("overdue")
def chores_overdue_cmd():
    """Show overdue chores."""
    async def _inner():
        async with _client() as c:
            return await chores.chores_overdue(c)
    _exec(_inner())


@chores_app.command("done")
def chores_done_cmd(chore: str, by: Optional[int] = typer.Option(None, "--by")):
    """Mark a chore as done."""
    async def _inner():
        async with _client() as c:
            return await chores.chore_execute(c, chore, by)
    _exec(_inner())


@chores_app.command("undo")
def chores_undo_cmd(chore: str):
    """Undo the last execution of a chore."""
    async def _inner():
        async with _client() as c:
            return await chores.chore_undo(c, chore)
    _exec(_inner())


@chores_app.command("create")
def chores_create_cmd(
    name: str,
    period_type: str = "manually",
    period_interval: Optional[int] = None,
    assigned_to: Optional[int] = None,
):
    """Create a new chore."""
    async def _inner():
        async with _client() as c:
            return await chores.chore_create(c, name, period_type, period_interval, assigned_to)
    _exec(_inner())


# --- System ---

@system_app.command("info")
def system_info_cmd():
    """Get Grocy version and system info."""
    async def _inner():
        async with _client() as c:
            return await system.system_info(c)
    _exec(_inner())


# --- Entity ---

@entity_app.command("list")
def entity_list_cmd(entity_type: str):
    """List any generic entity type."""
    async def _inner():
        async with _client() as c:
            return await system.entity_list(c, entity_type)
    _exec(_inner())


@entity_app.command("create")
def entity_create_cmd(entity_type: str, data: str = typer.Option(..., "--data")):
    """Create a generic entity."""
    async def _inner():
        async with _client() as c:
            return await system.entity_manage(c, "create", entity_type, data=json.loads(data))
    _exec(_inner())


@entity_app.command("update")
def entity_update_cmd(entity_type: str, entity_id: int, data: str = typer.Option(..., "--data")):
    """Update a generic entity."""
    async def _inner():
        async with _client() as c:
            return await system.entity_manage(c, "update", entity_type, entity_id, json.loads(data))
    _exec(_inner())


@entity_app.command("delete")
def entity_delete_cmd(entity_type: str, entity_id: int):
    """Delete a generic entity."""
    async def _inner():
        async with _client() as c:
            return await system.entity_manage(c, "delete", entity_type, entity_id)
    _exec(_inner())


def main():
    app()
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd C:/Workspace/grocy-mcp && pytest tests/test_cli.py -v`
Expected: 4 passed

- [ ] **Step 4: Commit**

```bash
git add src/grocy_mcp/cli/app.py tests/test_cli.py
git commit -m "feat: Typer CLI with stock, shopping, recipes, chores, system commands"
```

---

### Task 12: README and Final Verification

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

`README.md`:
````markdown
# grocy-mcp

MCP server and CLI for [Grocy](https://grocy.info) — control stock, shopping lists, recipes, and chores via AI agents or the command line.

## Features

- **30 MCP tools** for stock, shopping lists, recipes, chores, and system management
- **Full CLI** with intuitive subcommands (`grocy stock add Milk 2`)
- **Name-based lookups** — use product/recipe/chore names, not IDs
- **Dual transport** — stdio for local use, Streamable HTTP for remote access
- Targets Grocy v4.4.1+ REST API directly (no Home Assistant dependency)

## Installation

```bash
pip install grocy-mcp
```

Or with [uvx](https://docs.astral.sh/uv/):

```bash
uvx grocy-mcp
```

## Configuration

Set environment variables:

```bash
export GROCY_URL="http://your-grocy-instance:9192"
export GROCY_API_KEY="your-api-key"
```

Or create a config file at `~/.config/grocy-mcp/config.toml`:

```toml
[grocy]
url = "http://your-grocy-instance:9192"
api_key = "your-api-key"
```

## Usage

### MCP Server (for AI agents)

```bash
# stdio (Claude Code, local)
grocy-mcp

# Streamable HTTP (remote, e.g. behind Cloudflare tunnel)
grocy-mcp --transport streamable-http --port 8765
```

**Claude Code config** (`~/.claude.json`):

```json
{
  "mcpServers": {
    "grocy": {
      "type": "stdio",
      "command": "uvx",
      "args": ["grocy-mcp@latest"],
      "env": {
        "GROCY_URL": "http://your-grocy-instance:9192",
        "GROCY_API_KEY": "your-api-key"
      }
    }
  }
}
```

### CLI

```bash
# Stock
grocy stock list
grocy stock add Milk 2
grocy stock consume Bread 1
grocy stock expiring

# Shopping
grocy shopping list
grocy shopping add Eggs 12
grocy shopping clear

# Recipes
grocy recipes list
grocy recipes check "Pancakes"
grocy recipes to-shopping "Pancakes"

# Chores
grocy chores list
grocy chores overdue
grocy chores done "Vacuum"
```

## Development

```bash
git clone https://github.com/moustafattia/grocy-mcp.git
cd grocy-mcp
pip install -e ".[dev]"
pytest
```

## License

MIT
````

- [ ] **Step 2: Run full test suite**

Run: `cd C:/Workspace/grocy-mcp && pytest -v`
Expected: All tests pass

- [ ] **Step 3: Verify entry points work**

Run: `cd C:/Workspace/grocy-mcp && python -c "from grocy_mcp.mcp.server import create_mcp_server; print('MCP OK')"` and `python -c "from grocy_mcp.cli.app import app; print('CLI OK')"`
Expected: Both print OK

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with installation, config, and usage examples"
```

- [ ] **Step 5: Push all to GitHub**

```bash
git push origin main
```
