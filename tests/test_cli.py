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


def test_shopping_add_with_all_options():
    with patch("grocy_mcp.cli.app.shopping_list_add", new_callable=AsyncMock) as mock_add:
        mock_add.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(
                app,
                [
                    "shopping",
                    "add",
                    "Butter",
                    "--amount",
                    "3",
                    "--list-id",
                    "2",
                    "--note",
                    "salted",
                ],
            )

    assert result.exit_code == 0
    mock_add.assert_awaited_once_with(mock_client, "Butter", 3.0, 2, "salted")


def test_chore_execute_with_done_by():
    with patch("grocy_mcp.cli.app.chore_execute", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["chores", "execute", "Vacuum", "--done-by", "7"])

    assert result.exit_code == 0
    mock_execute.assert_awaited_once_with(mock_client, "Vacuum", 7)


def test_recipe_create_with_description_and_ingredients():
    with patch("grocy_mcp.cli.app.recipe_create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(
                app,
                [
                    "recipes",
                    "create",
                    "Pasta",
                    "--description",
                    "Italian pasta",
                    "--ingredients",
                    '[{"product_id": 1, "amount": 2}]',
                ],
            )

    assert result.exit_code == 0
    mock_create.assert_awaited_once_with(
        mock_client, "Pasta", "Italian pasta", [{"product_id": 1, "amount": 2}]
    )


def test_entity_manage_create():
    with patch("grocy_mcp.cli.app.entity_manage", new_callable=AsyncMock) as mock_manage:
        mock_manage.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(
                app,
                ["entity", "manage", "products", "create", "--data", '{"name": "Oat Milk"}'],
            )

    assert result.exit_code == 0
    mock_manage.assert_awaited_once_with(
        mock_client, "products", "create", None, {"name": "Oat Milk"}
    )


def test_entity_manage_delete():
    with patch("grocy_mcp.cli.app.entity_manage", new_callable=AsyncMock) as mock_manage:
        mock_manage.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(
                app,
                ["entity", "manage", "products", "delete", "--id", "5"],
            )

    assert result.exit_code == 0
    mock_manage.assert_awaited_once_with(mock_client, "products", "delete", 5, None)


def test_shopping_view_with_list_id():
    with patch("grocy_mcp.cli.app.shopping_list_view", new_callable=AsyncMock) as mock_view:
        mock_view.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["shopping", "view", "--list-id", "3"])

    assert result.exit_code == 0
    mock_view.assert_awaited_once_with(mock_client, 3)


# ---------------------------------------------------------------- --json flag


def test_stock_overview_json_output():
    """--json flag should call the client directly and output JSON."""
    with patch("grocy_mcp.cli.app._client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.get_stock = AsyncMock(return_value=[{"product_id": 1, "amount": 3}])
        mock_client_factory.return_value.__aenter__.return_value = mock_client
        result = runner.invoke(app, ["--json", "stock", "overview"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["product_id"] == 1


def test_shopping_view_json_output():
    """--json flag should output raw shopping list data."""
    with patch("grocy_mcp.cli.app._client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.get_shopping_list = AsyncMock(
            return_value=[{"id": 1, "product_id": 2, "amount": 3}]
        )
        mock_client_factory.return_value.__aenter__.return_value = mock_client
        result = runner.invoke(app, ["--json", "shopping", "view"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data[0]["id"] == 1


# -------------------------------------------------------------- --url / --api-key


def test_url_and_api_key_flags():
    """--url and --api-key should be forwarded to load_config."""
    with patch("grocy_mcp.cli.app.stock_overview", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = "ok"
        with patch("grocy_mcp.cli.app.load_config") as mock_config:
            mock_config.return_value = MagicMock(url="http://test", api_key="key")
            with patch("grocy_mcp.cli.app.GrocyClient") as mock_gc:
                mock_gc_instance = MagicMock()
                mock_gc.return_value.__aenter__.return_value = mock_gc_instance
                result = runner.invoke(
                    app,
                    ["--url", "http://my-grocy", "--api-key", "secret123", "stock", "overview"],
                )

    assert result.exit_code == 0
    mock_config.assert_called_once_with(url="http://my-grocy", api_key="secret123")


# --------------------------------------------------------- JSON validation errors


def test_shopping_update_invalid_json():
    """Malformed JSON should produce a clear error and exit code 2."""
    result = runner.invoke(app, ["shopping", "update", "1", "not-json"])
    assert result.exit_code == 2
    assert "invalid JSON" in result.output


def test_entity_manage_invalid_json():
    """Malformed --data JSON should produce a clear error."""
    result = runner.invoke(app, ["entity", "manage", "products", "create", "--data", "{bad"])
    assert result.exit_code == 2
    assert "invalid JSON" in result.output


def test_recipe_create_invalid_ingredients_json():
    """Malformed --ingredients JSON should produce a clear error."""
    result = runner.invoke(app, ["recipes", "create", "Test", "--ingredients", "[broken"])
    assert result.exit_code == 2
    assert "invalid JSON" in result.output


# ------------------------------------------------------------ short option flags


def test_shopping_add_short_flags():
    """Short flags -a, -l, -n should work for shopping add."""
    with patch("grocy_mcp.cli.app.shopping_list_add", new_callable=AsyncMock) as mock_add:
        mock_add.return_value = "ok"
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(
                app,
                ["shopping", "add", "Milk", "-a", "2", "-l", "3", "-n", "organic"],
            )

    assert result.exit_code == 0
    mock_add.assert_awaited_once_with(mock_client, "Milk", 2.0, 3, "organic")


# ------------------------------------------------ CLI end-to-end output tests


def test_cli_stock_overview_produces_formatted_output():
    """CLI stock overview should produce the actual formatted output, not just 'ok'."""
    with patch("grocy_mcp.cli.app.stock_overview", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = "Current stock:\n  [1] Milk — 3"
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_cf.return_value.__aenter__.return_value = MagicMock()
            result = runner.invoke(app, ["stock", "overview"])

    assert result.exit_code == 0
    assert "Current stock:" in result.output
    assert "[1] Milk" in result.output


def test_cli_error_handling():
    """GrocyError should print to stderr and exit 1."""
    from grocy_mcp.exceptions import GrocyAuthError

    with patch("grocy_mcp.cli.app.stock_overview", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = GrocyAuthError("Auth failed (401): bad key")
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_cf.return_value.__aenter__.return_value = MagicMock()
            result = runner.invoke(app, ["stock", "overview"])

    assert result.exit_code == 1
    assert "Error:" in result.output or "Auth failed" in result.output


def test_cli_error_json_mode():
    """In --json mode, errors should be JSON formatted."""
    from grocy_mcp.exceptions import GrocyNotFoundError

    with patch("grocy_mcp.cli.app._client") as mock_cf:
        mock_client = MagicMock()
        mock_client.get_stock = AsyncMock(side_effect=GrocyNotFoundError("not found"))
        mock_cf.return_value.__aenter__.return_value = mock_client
        result = runner.invoke(app, ["--json", "stock", "overview"])

    assert result.exit_code == 1
    import json

    data = json.loads(result.output)
    assert "error" in data


def test_cli_tasks_list_command():
    """Tasks list should work through the CLI."""
    with patch("grocy_mcp.cli.app.tasks_list", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = "Tasks:\n  [1] Buy milk"
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_cf.return_value.__aenter__.return_value = MagicMock()
            result = runner.invoke(app, ["tasks", "list"])

    assert result.exit_code == 0
    assert "Buy milk" in result.output


def test_cli_locations_list_command():
    """Locations list should work through the CLI."""
    with patch("grocy_mcp.cli.app.locations_list", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = "Locations:\n  [1] Fridge"
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_cf.return_value.__aenter__.return_value = MagicMock()
            result = runner.invoke(app, ["locations", "list"])

    assert result.exit_code == 0
    assert "Fridge" in result.output


def test_cli_meal_plan_list_command():
    """Meal plan list should work through the CLI."""
    with patch("grocy_mcp.cli.app.meal_plan_list", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = "Meal plan:\n  [1] 2026-04-05 — Pancakes"
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_cf.return_value.__aenter__.return_value = MagicMock()
            result = runner.invoke(app, ["meal-plan", "list"])

    assert result.exit_code == 0
    assert "Pancakes" in result.output


def test_cli_recipe_preview_command():
    """Recipe preview should work through the CLI."""
    with patch("grocy_mcp.cli.app.recipe_consume_preview", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = (
            "Preview — consuming recipe 'Pancakes' would deduct:\n  Flour: 2 — OK"
        )
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_cf.return_value.__aenter__.return_value = MagicMock()
            result = runner.invoke(app, ["recipes", "preview", "Pancakes"])

    assert result.exit_code == 0
    assert "Preview" in result.output
    assert "Flour" in result.output
