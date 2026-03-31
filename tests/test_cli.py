"""Tests for the CLI application."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from grocy_mcp.cli.app import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_run():
    """Patch _run so CLI commands don't actually start an event loop."""
    with patch("grocy_mcp.cli.app._run") as mock:
        mock.return_value = "ok"
        yield mock


def test_stock_overview_command(mock_run):
    result = runner.invoke(app, ["stock", "overview"])
    assert result.exit_code == 0
    assert "ok" in result.output


def test_stock_expiring_command(mock_run):
    result = runner.invoke(app, ["stock", "expiring"])
    assert result.exit_code == 0
    assert "ok" in result.output


def test_recipes_list_command(mock_run):
    result = runner.invoke(app, ["recipes", "list"])
    assert result.exit_code == 0
    assert "ok" in result.output


def test_chores_list_command(mock_run):
    result = runner.invoke(app, ["chores", "list"])
    assert result.exit_code == 0
    assert "ok" in result.output
