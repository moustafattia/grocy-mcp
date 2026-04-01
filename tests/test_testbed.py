"""Tests for the testbed package."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from testbed.evaluators.state import assert_expected_outcome
from testbed.loaders import load_confirmation, load_expected_outcome, load_manifest
from testbed.models import ExpectedOutcome, MutationExpectation, ScenarioConfirmation
from testbed.runners.common import build_stock_apply_items
from testbed.runners.run_suite import run_suite
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


@pytest.mark.asyncio
async def test_run_suite_resets_before_each_scenario(monkeypatch):
    reset_calls: list[str] = []
    run_mock = AsyncMock()

    monkeypatch.setattr(
        "testbed.runners.run_suite.SUITES",
        {"pr": [("a", "cli", "golden", "in_process"), ("b", "mcp", "golden", "in_process")]},
    )
    monkeypatch.setattr(
        "testbed.runners.run_suite.ensure_demo_environment",
        lambda config, seed_profile: reset_calls.append(str(seed_profile)) or [],
    )
    monkeypatch.setattr("testbed.runners.run_suite.run_scenario", run_mock)
    monkeypatch.setattr("testbed.runners.run_suite.source_ready", lambda source, config: True)
    monkeypatch.setattr(
        "testbed.runners.run_suite.TestbedConfig.from_env",
        lambda: SimpleNamespace(
            manage_environment=True,
            seed_dir=TESTBED_DIR / "seed",
            openai_model=None,
            anthropic_model=None,
            openai_compatible_model=None,
        ),
    )

    warnings = await run_suite("pr")

    assert warnings == []
    assert len(reset_calls) == 2
    assert run_mock.await_count == 2
