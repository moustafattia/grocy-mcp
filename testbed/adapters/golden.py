"""Golden adapter that returns versioned fixture JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from testbed.adapters.base import ModelAdapter
from testbed.utils import read_json


class GoldenAdapter(ModelAdapter):
    provider_name = "golden"

    def extract(
        self,
        task_type: str,
        asset_ref: Path,
        source_metadata: dict[str, Any],
        prompt_template: str,
    ) -> list[dict]:
        golden_path = source_metadata.get("golden_items_override")
        if not golden_path:
            raise RuntimeError("Golden adapter requires source_metadata.golden_items_override.")
        payload = read_json(asset_ref.parent.parent / str(golden_path))
        if not isinstance(payload, list):
            raise RuntimeError("Golden items payload must be a JSON array.")
        return payload
