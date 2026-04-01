"""Integration tests against a real Grocy instance.

These tests are skipped unless both GROCY_URL and GROCY_API_KEY are set in the
environment. Run them with:

    GROCY_URL=http://localhost:9283 GROCY_API_KEY=... pytest tests/test_integration.py -v

They make real API calls and may modify data on the target instance.
"""

from __future__ import annotations

import os

import pytest

from grocy_mcp.client import GrocyClient

_GROCY_URL = os.environ.get("GROCY_URL")
_GROCY_API_KEY = os.environ.get("GROCY_API_KEY")

pytestmark = pytest.mark.skipif(
    not (_GROCY_URL and _GROCY_API_KEY),
    reason="GROCY_URL and GROCY_API_KEY not set — skipping integration tests",
)


@pytest.fixture
async def live_client():
    async with GrocyClient(_GROCY_URL, _GROCY_API_KEY) as client:
        yield client


async def test_system_info(live_client):
    """Verify connectivity by fetching system info."""
    info = await live_client.get_system_info()
    assert "grocy_version" in info


async def test_get_stock(live_client):
    """Stock endpoint should return a list."""
    stock = await live_client.get_stock()
    assert isinstance(stock, list)


async def test_get_objects_products(live_client):
    """Products entity should be listable."""
    products = await live_client.get_objects("products")
    assert isinstance(products, list)


async def test_get_volatile_stock(live_client):
    """Volatile stock endpoint should return expected keys."""
    volatile = await live_client.get_volatile_stock()
    assert "expiring_products" in volatile
    assert "expired_products" in volatile
    assert "missing_products" in volatile
