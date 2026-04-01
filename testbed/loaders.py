"""Scenario, confirmation, and expected-outcome loading helpers."""

from __future__ import annotations

from pathlib import Path

from testbed.models import ExpectedOutcome, ScenarioConfirmation, ScenarioManifest
from testbed.utils import read_json


def load_manifest(path: Path) -> ScenarioManifest:
    return ScenarioManifest.model_validate(read_json(path))


def load_confirmation(path: Path) -> ScenarioConfirmation:
    return ScenarioConfirmation.model_validate(read_json(path))


def load_expected_outcome(path: Path) -> ExpectedOutcome:
    return ExpectedOutcome.model_validate(read_json(path))
