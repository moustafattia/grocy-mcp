"""Report writing helpers for the testbed suite."""

from __future__ import annotations

from pathlib import Path

from testbed.models import RunReport
from testbed.utils import write_json


def write_report(path: Path, report: RunReport) -> None:
    write_json(path, report.model_dump())
