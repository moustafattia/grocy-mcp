"""Tests for the testbed package."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastmcp.client.client import CallToolResult as FastMcpCallToolResult

from testbed.evaluators.state import assert_expected_outcome
from testbed.loaders import load_confirmation, load_expected_outcome, load_manifest
from testbed.models import ExpectedOutcome, MutationExpectation, ScenarioConfirmation
from testbed.runners.common import build_stock_apply_items, flatten_shopping_actions
from testbed.runners.run_scenario import _StdioMcpRunner
from testbed.runners.run_suite import run_suite
from testbed.seed.manage import _compose_env, _create_named_entities, wait_for_grocy
from testbed.seed.session import _LoginFormParser
from testbed.utils import TESTBED_DIR


def test_load_manifest_and_related_files():
    manifest = load_manifest(TESTBED_DIR / "scenarios" / "receipt-stock-basic.json")
    confirmation = load_confirmation(
        TESTBED_DIR / "scenarios" / "confirmations" / "receipt-stock-ambiguous.json"
    )
    expected = load_expected_outcome(
        TESTBED_DIR / "scenarios" / "expected" / "receipt-stock-basic.json"
    )

    assert manifest.id == "receipt-stock-basic"
    assert confirmation.product_resolutions[0].product == "Whole Milk"
    assert expected.shopping_lists[0].list_name == "Weekly"


def test_build_stock_apply_items_uses_confirmation_override():
    preview = [
        {"input_index": 0, "status": "ambiguous", "candidates": []},
        {"input_index": 1, "status": "matched", "matched_product_id": 44},
    ]
    normalized = [
        {"label": "milk", "quantity": 1, "note": "receipt"},
        {"label": "oat milk", "quantity": 2},
    ]
    confirmation = ScenarioConfirmation.model_validate(
        {"product_resolutions": [{"input_index": 0, "product": "Whole Milk"}]}
    )

    apply_items, actions = build_stock_apply_items(
        preview,
        normalized,
        confirmation,
        {"whole milk": 12, "oat milk": 44},
    )

    assert apply_items == [
        {"product_id": 12, "amount": 1, "note": "receipt"},
        {"product_id": 44, "amount": 2},
    ]
    assert actions[0]["action"] == "resolve_override"
    assert actions[1]["action"] == "use_matched"


def test_assert_expected_outcome_checks_mutations_and_absent_items():
    before = {
        "stock": {"Whole Milk": 0.0},
        "shopping_lists": {"Weekly": {"Whole Milk": 2.0, "Bread": 1.0}},
    }
    after = {
        "stock": {"Whole Milk": 2.0},
        "shopping_lists": {"Weekly": {"Bread": 1.0}},
    }
    expected = ExpectedOutcome.model_validate(
        {
            "stock": [{"product": "Whole Milk", "amount": 2}],
            "shopping_lists": [
                {
                    "list_name": "Weekly",
                    "items": [{"product": "Bread", "amount": 1}],
                    "absent": ["Whole Milk"],
                }
            ],
            "mutations": MutationExpectation(
                stock_changed=True, shopping_changed=True
            ).model_dump(),
        }
    )

    assertions = assert_expected_outcome(before, after, expected)

    assert all(item["passed"] for item in assertions)


def test_login_form_parser_finds_password_form():
    parser = _LoginFormParser()
    parser.feed(
        """
        <html><body>
        <form action="/login" method="post">
          <input type="hidden" name="_token" value="abc">
          <input type="text" name="username">
          <input type="password" name="password">
        </form>
        </body></html>
        """
    )

    assert parser.forms[0]["action"] == "/login"
    assert any(item.get("type") == "password" for item in parser.forms[0]["inputs"])


def test_wait_for_grocy_drives_root_route_until_database_ready(monkeypatch, tmp_path):
    responses = iter(
        [
            httpx.Response(200, request=httpx.Request("GET", "http://grocy.test/")),
            httpx.Response(200, request=httpx.Request("GET", "http://grocy.test/")),
        ]
    )
    readiness = iter([False, True])
    seen_urls: list[str] = []

    def fake_get(url: str, **kwargs):
        seen_urls.append(url)
        return next(responses)

    monkeypatch.setattr("testbed.seed.manage.httpx.get", fake_get)
    monkeypatch.setattr("testbed.seed.manage._database_ready", lambda path: next(readiness))
    monkeypatch.setattr("testbed.seed.manage.time.sleep", lambda _: None)

    wait_for_grocy("http://grocy.test", tmp_path / "grocy.db", timeout=1)

    assert seen_urls == [
        "http://grocy.test",
        "http://grocy.test",
    ]


def test_session_login_retries_transient_server_error(monkeypatch):
    from testbed.seed.session import GrocySessionClient

    class FakeClient:
        def __init__(self) -> None:
            self.post_calls = 0

        def post(self, url: str, data: dict[str, str]):
            self.post_calls += 1
            status = 500 if self.post_calls == 1 else 200
            return httpx.Response(status, request=httpx.Request("POST", url))

        def get(self, url: str, headers: dict[str, str] | None = None):
            return httpx.Response(200, request=httpx.Request("GET", url))

        def close(self) -> None:
            return

    session = GrocySessionClient("http://grocy.test", "admin", "admin")
    fake_client = FakeClient()
    session.client = fake_client  # type: ignore[assignment]
    monkeypatch.setattr(
        session,
        "_discover_login_form",
        lambda: ("http://grocy.test/login", {"username": "admin", "password": "admin"}),
    )
    monkeypatch.setattr("testbed.seed.session.time.sleep", lambda _: None)

    session.login(retries=1, retry_delay=0)

    assert fake_client.post_calls == 2


def test_create_named_entities_reuses_existing_names_case_insensitively():
    class FakeSession:
        def __init__(self) -> None:
            self.create_calls: list[tuple[str, dict]] = []

        def get_objects(self, entity: str):
            assert entity == "quantity_units"
            return [{"id": 2, "name": "Piece"}, {"id": 3, "name": "Pack"}]

        def create_object(self, entity: str, data: dict):
            self.create_calls.append((entity, data))
            return 10 + len(self.create_calls)

    session = FakeSession()

    ids, warnings = _create_named_entities(
        session,
        "quantity_units",
        "quantity_units",
        [
            {"name": "piece", "description": "Countable items"},
            {"name": "carton", "description": "Cartons"},
        ],
    )

    assert ids == {"piece": 2, "carton": 11}
    assert warnings == []
    assert session.create_calls == [
        ("quantity_units", {"name": "carton", "description": "Cartons"})
    ]


def test_compose_env_inherits_host_ids(monkeypatch):
    monkeypatch.setenv("EXISTING_VAR", "present")
    monkeypatch.setattr("testbed.seed.manage.os.getuid", lambda: 1234, raising=False)
    monkeypatch.setattr("testbed.seed.manage.os.getgid", lambda: 5678, raising=False)

    env = _compose_env()

    assert env["EXISTING_VAR"] == "present"
    assert env["TESTBED_PUID"] == "1234"
    assert env["TESTBED_PGID"] == "5678"


def test_compose_env_preserves_explicit_ids(monkeypatch):
    monkeypatch.setenv("TESTBED_PUID", "1111")
    monkeypatch.setenv("TESTBED_PGID", "2222")
    monkeypatch.setattr("testbed.seed.manage.os.getuid", lambda: 1234, raising=False)
    monkeypatch.setattr("testbed.seed.manage.os.getgid", lambda: 5678, raising=False)

    env = _compose_env()

    assert env["TESTBED_PUID"] == "1111"
    assert env["TESTBED_PGID"] == "2222"


def test_flatten_shopping_actions_strips_preview_only_fields():
    actions = flatten_shopping_actions(
        [
            {
                "actions": [
                    {
                        "shopping_item_id": 1,
                        "action": "remove",
                        "previous_amount": 2,
                    },
                    {
                        "shopping_item_id": 2,
                        "action": "set_amount",
                        "previous_amount": 3,
                        "new_amount": 1,
                    },
                ]
            }
        ]
    )

    assert actions == [
        {"shopping_item_id": 1, "action": "remove"},
        {"shopping_item_id": 2, "action": "set_amount", "new_amount": 1},
    ]


@pytest.mark.asyncio
async def test_stdio_runner_unwraps_fastmcp_call_tool_result():
    runner = _StdioMcpRunner(
        SimpleNamespace(
            mcp_bin="grocy-mcp",
            root_dir=Path.cwd(),
            proxy_url="http://grocy.test",
            proxy_api_key="testbed-demo-key",
        )
    )

    class FakeClient:
        async def call_tool(self, tool_name: str, arguments: dict[str, object]):
            assert tool_name == "workflow_match_products_preview_tool"
            assert arguments == {"items": "[]"}
            return FastMcpCallToolResult(
                content=[],
                structured_content={"result": [{"input_index": 0, "status": "matched"}]},
                meta=None,
                data=[{"input_index": 0, "status": "matched"}],
                is_error=False,
            )

    runner.client = FakeClient()

    result = await runner.call("workflow_match_products_preview_tool", items="[]")

    assert result == [{"input_index": 0, "status": "matched"}]


@pytest.mark.asyncio
async def test_run_suite_bootstraps_once_then_resets(monkeypatch):
    bootstrap_calls: list[str] = []
    reset_calls: list[str] = []
    run_mock = AsyncMock(
        side_effect=[
            SimpleNamespace(duration_ms=101),
            SimpleNamespace(duration_ms=202),
        ]
    )

    monkeypatch.setattr(
        "testbed.runners.run_suite.SUITES",
        {"pr": [("a", "cli", "golden", "in_process"), ("b", "mcp", "golden", "in_process")]},
    )
    monkeypatch.setattr(
        "testbed.runners.run_suite.ensure_demo_environment",
        lambda config, seed_profile: bootstrap_calls.append(str(seed_profile)) or [],
    )
    monkeypatch.setattr(
        "testbed.runners.run_suite.reset_demo_data",
        lambda config, seed_profile: reset_calls.append(str(seed_profile)) or [],
    )
    monkeypatch.setattr("testbed.runners.run_suite.run_scenario", run_mock)
    monkeypatch.setattr("testbed.runners.run_suite.source_ready", lambda source, config: True)
    monkeypatch.setattr(
        "testbed.runners.run_suite.TestbedConfig.from_env",
        lambda: SimpleNamespace(
            manage_environment=True,
            seed_dir=TESTBED_DIR / "seed",
            reports_dir=TESTBED_DIR / "runtime" / "reports",
            openai_model=None,
            anthropic_model=None,
            openai_compatible_model=None,
        ),
    )

    warnings = await run_suite("pr")

    assert warnings == []
    assert len(bootstrap_calls) == 1, "full bootstrap should run exactly once"
    assert len(reset_calls) == 1, "lightweight reset should run for subsequent scenarios"
    assert run_mock.await_count == 2


@pytest.mark.asyncio
async def test_run_suite_prints_progress_and_summary(monkeypatch, capsys):
    run_mock = AsyncMock(
        side_effect=[
            SimpleNamespace(duration_ms=101),
            SimpleNamespace(duration_ms=202),
        ]
    )

    monkeypatch.setattr(
        "testbed.runners.run_suite.SUITES",
        {"pr": [("a", "cli", "golden", "in_process"), ("b", "mcp", "golden", "in_process")]},
    )
    monkeypatch.setattr("testbed.runners.run_suite.run_scenario", run_mock)
    monkeypatch.setattr("testbed.runners.run_suite.source_ready", lambda source, config: True)
    monkeypatch.setattr(
        "testbed.runners.run_suite.TestbedConfig.from_env",
        lambda: SimpleNamespace(
            manage_environment=False,
            seed_dir=TESTBED_DIR / "seed",
            reports_dir=TESTBED_DIR / "runtime" / "reports",
            openai_model=None,
            anthropic_model=None,
            openai_compatible_model=None,
        ),
    )

    warnings = await run_suite("pr")

    output = capsys.readouterr().out
    assert warnings == []
    assert "Running testbed suite 'pr' with 2 scenario(s)." in output
    assert "[1/2] Running a via cli/golden/in_process..." in output
    assert "[1/2] Passed a in 101ms (cli/golden/in_process)." in output
    assert "[2/2] Running b via mcp/golden/in_process..." in output
    assert "[2/2] Passed b in 202ms (mcp/golden/in_process)." in output
    assert "Suite 'pr' completed: 2 passed, 0 skipped, 0 warning(s)." in output
    assert f"Testbed reports written to: {TESTBED_DIR / 'runtime' / 'reports'}" in output


@pytest.mark.asyncio
async def test_run_suite_prints_skipped_provider_summary(monkeypatch, capsys):
    run_mock = AsyncMock()

    monkeypatch.setattr(
        "testbed.runners.run_suite.SUITES",
        {"nightly": [("a", "mcp", "openai", "stdio")]},
    )
    monkeypatch.setattr("testbed.runners.run_suite.run_scenario", run_mock)
    monkeypatch.setattr("testbed.runners.run_suite.source_ready", lambda source, config: False)
    monkeypatch.setattr(
        "testbed.runners.run_suite.TestbedConfig.from_env",
        lambda: SimpleNamespace(
            manage_environment=False,
            seed_dir=TESTBED_DIR / "seed",
            reports_dir=TESTBED_DIR / "runtime" / "reports",
            openai_model=None,
            anthropic_model=None,
            openai_compatible_model=None,
        ),
    )

    warnings = await run_suite("nightly")

    output = capsys.readouterr().out
    assert warnings == ["Skipped a/mcp/openai: provider not configured."]
    assert "[1/1] Skipped a (mcp/openai/stdio): provider not configured." in output
    assert "Suite 'nightly' completed: 0 passed, 1 skipped, 1 warning(s)." in output
    assert run_mock.await_count == 0
