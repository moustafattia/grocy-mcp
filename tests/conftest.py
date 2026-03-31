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
