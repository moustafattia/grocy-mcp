"""Tests for the MCP server."""

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
