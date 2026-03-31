"""Tests for the MCP server."""

from grocy_mcp.mcp.server import create_mcp_server


def test_create_mcp_server_returns_server_with_correct_name():
    server = create_mcp_server()
    assert server.name == "grocy-mcp"
