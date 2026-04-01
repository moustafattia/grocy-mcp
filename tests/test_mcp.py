"""Tests for the MCP server."""

from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest

from grocy_mcp.mcp.server import create_mcp_server, main


def test_create_mcp_server_returns_server_with_correct_name():
    server = create_mcp_server()
    assert server.name == "grocy-mcp"


def test_main_stdio_default(monkeypatch):
    """Default transport is stdio."""
    server = MagicMock()
    monkeypatch.setattr("grocy_mcp.mcp.server.create_mcp_server", lambda: server)
    monkeypatch.setattr("sys.argv", ["grocy-mcp"])
    main()
    server.run.assert_called_once_with(transport="stdio")


def test_main_http_with_defaults(monkeypatch):
    """HTTP transport passes host, port, path, stateless_http."""
    server = MagicMock()
    monkeypatch.setattr("grocy_mcp.mcp.server.create_mcp_server", lambda: server)
    monkeypatch.setattr("sys.argv", ["grocy-mcp", "--transport", "streamable-http"])
    main()
    server.run.assert_called_once_with(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        path="/mcp",
        stateless_http=True,
    )


def test_main_http_custom_args(monkeypatch):
    """HTTP transport respects --host, --port, --path."""
    server = MagicMock()
    monkeypatch.setattr("grocy_mcp.mcp.server.create_mcp_server", lambda: server)
    monkeypatch.setattr(
        "sys.argv",
        [
            "grocy-mcp",
            "--transport",
            "streamable-http",
            "--host",
            "127.0.0.1",
            "--port",
            "9193",
            "--path",
            "/private_abc",
        ],
    )
    main()
    server.run.assert_called_once_with(
        transport="streamable-http",
        host="127.0.0.1",
        port=9193,
        path="/private_abc",
        stateless_http=True,
    )


async def test_entity_create_tool_invalid_json_returns_clear_error():
    mcp = create_mcp_server()

    with pytest.raises(Exception, match="Invalid JSON for data"):
        await mcp.call_tool("entity_create_tool", {"entity": "products", "data": "{bad"})


async def test_workflow_match_products_preview_tool_invalid_json_returns_clear_error():
    mcp = create_mcp_server()

    with pytest.raises(Exception, match="Invalid JSON for items"):
        await mcp.call_tool("workflow_match_products_preview_tool", {"items": "{bad"})


async def test_workflow_match_products_preview_tool_returns_structured_data(monkeypatch):
    mcp = create_mcp_server()

    @asynccontextmanager
    async def fake_client():
        class Client:
            async def get_objects(self, entity: str):
                if entity == "products":
                    return [{"id": 12, "name": "Whole Milk"}]
                if entity == "product_barcodes":
                    return [{"id": 2, "product_id": 12, "barcode": "5000112637922"}]
                return []

        yield Client()

    monkeypatch.setattr("grocy_mcp.mcp.server._get_client", fake_client)

    result = await mcp.call_tool(
        "workflow_match_products_preview_tool",
        {"items": '[{"label": "whole milk", "quantity": 2, "barcode": "5000112637922"}]'},
    )

    preview = result.structured_content["result"]
    assert preview[0]["status"] == "matched"
    assert preview[0]["matched_product_id"] == 12


async def test_catalog_list_tool_returns_structured_data(monkeypatch):
    mcp = create_mcp_server()

    @asynccontextmanager
    async def fake_client():
        class Client:
            async def get_objects(self, entity: str):
                assert entity == "shopping_lists"
                return [{"id": 1, "name": "Weekly"}]

        yield Client()

    monkeypatch.setattr("grocy_mcp.mcp.server._get_client", fake_client)

    result = await mcp.call_tool("catalog_list_tool", {"entity": "shopping_lists"})

    rows = result.structured_content["result"]
    assert rows == [{"id": 1, "name": "Weekly"}]


async def test_calendar_summary_tool_returns_structured_data(monkeypatch):
    mcp = create_mcp_server()

    @asynccontextmanager
    async def fake_client():
        class Client:
            async def get_tasks(self):
                return [{"id": 1, "name": "Buy milk", "due_date": "2026-04-05"}]

            async def get_chores(self):
                return []

            async def get_batteries(self):
                return []

            async def get_objects(self, entity: str):
                if entity == "meal_plan":
                    return []
                if entity == "recipes":
                    return []
                return []

        yield Client()

    monkeypatch.setattr("grocy_mcp.mcp.server._get_client", fake_client)

    result = await mcp.call_tool("calendar_summary_tool", {})

    summary = result.structured_content.get("result", result.structured_content)
    assert summary["tasks"][0]["id"] == 1


async def test_file_download_tool_returns_base64(monkeypatch):
    mcp = create_mcp_server()

    @asynccontextmanager
    async def fake_client():
        class Client:
            async def download_file(
                self,
                group: str,
                file_name_b64: str,
                force_serve_as=None,
                best_fit_width=None,
                best_fit_height=None,
            ):
                return b"hello", "text/plain"

        yield Client()

    monkeypatch.setattr("grocy_mcp.mcp.server._get_client", fake_client)

    result = await mcp.call_tool(
        "file_download_tool",
        {"group": "productpictures", "file_name": "milk.jpg"},
    )

    payload = result.structured_content.get("result", result.structured_content)
    assert payload["group"] == "productpictures"
    assert payload["content_type"] == "text/plain"
