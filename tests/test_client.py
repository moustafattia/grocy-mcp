"""Tests for GrocyClient."""

import httpx
import pytest

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


# --------------------------------------------------------- Retry and transport


async def test_retry_on_503(client, mock_api):
    """503 should also trigger retry."""
    route = mock_api.get("/stock")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json=[{"product_id": 1}]),
    ]
    result = await client.get_stock()
    assert result == [{"product_id": 1}]
    assert route.call_count == 2


async def test_retry_on_504(client, mock_api):
    """504 should also trigger retry."""
    route = mock_api.get("/stock")
    route.side_effect = [
        httpx.Response(504),
        httpx.Response(200, json=[]),
    ]
    result = await client.get_stock()
    assert result == []


async def test_retry_exhaustion_raises(client, mock_api):
    """All retries returning 502 should raise GrocyServerError."""
    route = mock_api.get("/stock")
    route.side_effect = [
        httpx.Response(502),
        httpx.Response(502),
        httpx.Response(502),
    ]
    with pytest.raises(GrocyServerError):
        await client.get_stock()
    assert route.call_count == 3  # initial + 2 retries


async def test_transport_error_retries(client, mock_api):
    """Transport errors should be retried."""
    route = mock_api.get("/stock")
    route.side_effect = [
        httpx.ConnectError("connection refused"),
        httpx.Response(200, json=[]),
    ]
    result = await client.get_stock()
    assert result == []


async def test_transport_error_exhaustion(client, mock_api):
    """Persistent transport errors should raise GrocyServerError."""
    route = mock_api.get("/stock")
    route.side_effect = [
        httpx.ConnectError("refused"),
        httpx.ConnectError("refused"),
        httpx.ConnectError("refused"),
    ]
    with pytest.raises(GrocyServerError, match="Connection failed"):
        await client.get_stock()


async def test_403_raises_auth_error(client, mock_api):
    """403 should map to GrocyAuthError like 401."""
    mock_api.get("/stock").mock(return_value=httpx.Response(403))
    with pytest.raises(GrocyAuthError):
        await client.get_stock()


async def test_non_transient_error_no_retry(client, mock_api):
    """400/404 errors should not be retried."""
    route = mock_api.post("/objects/products")
    route.mock(return_value=httpx.Response(400, json={"error": "bad"}))
    with pytest.raises(GrocyValidationError):
        await client.create_object("products", {})
    assert route.call_count == 1  # no retry


async def test_url_trailing_slash_normalization(base_url, api_key):
    """URL with trailing slash should be normalized."""
    client = GrocyClient(base_url + "/", api_key)
    assert client._base == base_url + "/api"
    await client._client.aclose()
