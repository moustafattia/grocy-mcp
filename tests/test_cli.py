"""Tests for the CLI application."""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from grocy_mcp.cli.app import app

runner = CliRunner()


def test_stock_overview_command():
    with patch("grocy_mcp.cli.app.stock_overview", new_callable=AsyncMock) as mock_stock_overview:
        mock_stock_overview.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["stock", "overview"])

    assert result.exit_code == 0
    assert "ok" in result.output
    mock_stock_overview.assert_awaited_once_with(mock_client)


def test_stock_expiring_command():
    with patch("grocy_mcp.cli.app.stock_expiring", new_callable=AsyncMock) as mock_stock_expiring:
        mock_stock_expiring.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["stock", "expiring"])

    assert result.exit_code == 0
    assert "ok" in result.output
    mock_stock_expiring.assert_awaited_once_with(mock_client)


def test_recipes_list_command():
    with patch("grocy_mcp.cli.app.recipes_list", new_callable=AsyncMock) as mock_recipes_list:
        mock_recipes_list.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["recipes", "list"])

    assert result.exit_code == 0
    assert "ok" in result.output
    mock_recipes_list.assert_awaited_once_with(mock_client)


def test_chores_list_command():
    with patch("grocy_mcp.cli.app.chores_list", new_callable=AsyncMock) as mock_chores_list:
        mock_chores_list.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["chores", "list"])

    assert result.exit_code == 0
    assert "ok" in result.output
    mock_chores_list.assert_awaited_once_with(mock_client)
