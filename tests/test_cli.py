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


def test_stock_search_json_output():
    """--json stock search should return matching product objects."""
    with patch("grocy_mcp.cli.app._client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.get_objects = AsyncMock(
            side_effect=[
                [{"id": 1, "name": "Milk"}, {"id": 2, "name": "Bread"}],
                [{"id": 10, "product_id": 1, "barcode": "123milk"}],
            ]
        )
        mock_client_factory.return_value.__aenter__.return_value = mock_client
        result = runner.invoke(app, ["--json", "stock", "search", "milk"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data == [{"id": 1, "name": "Milk"}]


def test_recipe_details_json_output():
    """--json recipe details should return recipe data with ingredients."""
    with patch("grocy_mcp.cli.app.resolve_recipe", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = 5
        with patch("grocy_mcp.cli.app._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client.get_recipe = AsyncMock(return_value={"id": 5, "name": "Pancakes"})
            mock_client.get_objects = AsyncMock(
                return_value=[
                    {"id": 1, "recipe_id": 5, "product_id": 2, "amount": 3},
                    {"id": 2, "recipe_id": 9, "product_id": 4, "amount": 1},
                ]
            )
            mock_client_factory.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["--json", "recipes", "details", "Pancakes"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data["id"] == 5
    assert data["ingredients"] == [{"id": 1, "recipe_id": 5, "product_id": 2, "amount": 3}]


def test_chores_overdue_json_output():
    """--json chores overdue should return only overdue entries."""
    with patch("grocy_mcp.cli.app._client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.get_chores = AsyncMock(
            return_value=[
                {
                    "chore_id": 1,
                    "next_estimated_execution_time": "2000-01-01 00:00:00",
                    "chore": {"name": "Vacuum"},
                },
                {
                    "chore_id": 2,
                    "next_estimated_execution_time": "2999-01-01 00:00:00",
                    "chore": {"name": "Dust"},
                },
            ]
        )
        mock_client_factory.return_value.__aenter__.return_value = mock_client
        result = runner.invoke(app, ["--json", "chores", "overdue"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["chore_id"] == 1


def test_stock_journal_json_output():
    """--json stock journal should return newest-first entries."""
    with patch("grocy_mcp.cli.app._client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.get_objects = AsyncMock(
            return_value=[
                {"id": 1, "product_id": 1, "row_created_timestamp": "2026-04-01 10:00:00"},
                {"id": 2, "product_id": 1, "row_created_timestamp": "2026-04-01 12:00:00"},
            ]
        )
        mock_client_factory.return_value.__aenter__.return_value = mock_client
        result = runner.invoke(app, ["--json", "stock", "journal"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert [entry["id"] for entry in data] == [2, 1]


def test_tasks_list_json_hides_done_by_default():
    """--json tasks list should preserve the default incomplete-only behavior."""
    with patch("grocy_mcp.cli.app._client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.get_tasks = AsyncMock(return_value=[{"id": 1, "name": "Open task", "done": 0}])
        mock_client_factory.return_value.__aenter__.return_value = mock_client
        result = runner.invoke(app, ["--json", "tasks", "list"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data == [{"id": 1, "name": "Open task", "done": 0}]


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


def test_workflow_match_products_preview_json_output():
    """Workflow preview should return structured JSON in --json mode."""
    with patch(
        "grocy_mcp.cli.app.workflow_match_products_preview_data", new_callable=AsyncMock
    ) as mock_fn:
        mock_fn.return_value = [
            {
                "input_index": 0,
                "label": "whole milk",
                "status": "matched",
                "matched_product_id": 12,
                "matched_product_name": "Whole Milk",
                "candidates": [{"product_id": 12, "name": "Whole Milk"}],
                "suggested_amount": 2,
                "unit_text": "cartons",
            }
        ]
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_client = MagicMock()
            mock_cf.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(
                app,
                [
                    "--json",
                    "workflow",
                    "match-products-preview",
                    '[{"label":"whole milk","quantity":2}]',
                ],
            )

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data[0]["status"] == "matched"
    mock_fn.assert_awaited_once_with(mock_client, [{"label": "whole milk", "quantity": 2}])


def test_workflow_match_products_preview_text_output():
    """Workflow preview should render human-readable text by default."""
    with patch(
        "grocy_mcp.cli.app.workflow_match_products_preview", new_callable=AsyncMock
    ) as mock_fn:
        mock_fn.return_value = "Workflow product match preview:\n  [0] whole milk: matched"
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_cf.return_value.__aenter__.return_value = MagicMock()
            result = runner.invoke(
                app,
                ["workflow", "match-products-preview", '[{"label":"whole milk","quantity":2}]'],
            )

    assert result.exit_code == 0
    assert "Workflow product match preview" in result.output


def test_workflow_match_products_preview_invalid_json():
    """Workflow preview should reject malformed JSON input."""
    result = runner.invoke(app, ["workflow", "match-products-preview", "not-json"])
    assert result.exit_code == 2
    assert "invalid JSON" in result.output


def test_workflow_stock_intake_apply_json_output():
    """Workflow stock intake apply should return structured JSON in --json mode."""
    with patch(
        "grocy_mcp.cli.app.workflow_stock_intake_apply_data", new_callable=AsyncMock
    ) as mock_fn:
        mock_fn.return_value = {
            "applied_count": 1,
            "applied_items": [{"product_id": 12, "amount": 2, "note": "organic"}],
        }
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_client = MagicMock()
            mock_cf.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(
                app,
                ["--json", "workflow", "stock-intake-apply", '[{"product_id":12,"amount":2}]'],
            )

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data["applied_count"] == 1
    mock_fn.assert_awaited_once_with(mock_client, [{"product_id": 12, "amount": 2}])


def test_workflow_shopping_reconcile_preview_json_output():
    """Workflow shopping reconcile preview should return structured JSON."""
    with patch(
        "grocy_mcp.cli.app.workflow_shopping_reconcile_preview_data", new_callable=AsyncMock
    ) as mock_fn:
        mock_fn.return_value = [
            {
                "input_index": 0,
                "product_id": 12,
                "purchased_amount": 2,
                "status": "matched",
                "actions": [{"shopping_item_id": 5, "action": "remove", "previous_amount": 2}],
                "unapplied_amount": 0,
            }
        ]
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_client = MagicMock()
            mock_cf.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(
                app,
                [
                    "--json",
                    "workflow",
                    "shopping-reconcile-preview",
                    '[{"product_id":12,"amount":2}]',
                    "--list-id",
                    "2",
                ],
            )

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data[0]["actions"][0]["shopping_item_id"] == 5
    mock_fn.assert_awaited_once_with(mock_client, [{"product_id": 12, "amount": 2}], 2)


def test_catalog_list_json_output():
    """Catalog list should return raw structured rows in --json mode."""
    with patch("grocy_mcp.cli.app.list_entity_records", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = [{"id": 1, "name": "Pantry"}]
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_client = MagicMock()
            mock_cf.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["--json", "catalog", "list", "shopping-lists"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data == [{"id": 1, "name": "Pantry"}]
    mock_fn.assert_awaited_once_with(mock_client, "shopping_lists", None)


def test_batteries_overdue_json_output():
    """Battery overdue view should return structured rows in --json mode."""
    with patch("grocy_mcp.cli.app.batteries_overdue_data", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = [{"battery_id": 1, "name": "Remote battery"}]
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_client = MagicMock()
            mock_cf.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["--json", "batteries", "overdue"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data[0]["battery_id"] == 1


def test_calendar_summary_json_output():
    """Calendar summary should return structured planning data in --json mode."""
    with patch("grocy_mcp.cli.app.calendar_summary_data", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = {"tasks": [], "chores": [], "batteries": [], "meal_plan": []}
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_client = MagicMock()
            mock_cf.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["--json", "calendar", "summary"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data["tasks"] == []


def test_files_upload_json_output(tmp_path):
    """Files upload should return structured output in --json mode."""
    local_file = tmp_path / "milk.txt"
    local_file.write_text("hello", encoding="utf-8")
    with patch("grocy_mcp.cli.app.file_upload_data", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = {
            "group": "productpictures",
            "file_name": "milk.txt",
            "uploaded": True,
        }
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_client = MagicMock()
            mock_cf.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(
                app,
                ["--json", "files", "upload", "productpictures", "milk.txt", str(local_file)],
            )

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data["uploaded"] is True


def test_discover_describe_entity_json_output():
    """Entity describe helper should return structured metadata in --json mode."""
    with patch("grocy_mcp.cli.app.describe_entity_data", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = {"entity": "products", "sample_fields": ["id", "name"]}
        with patch("grocy_mcp.cli.app._client") as mock_cf:
            mock_client = MagicMock()
            mock_cf.return_value.__aenter__.return_value = mock_client
            result = runner.invoke(app, ["--json", "discover", "describe-entity", "products"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data["entity"] == "products"
