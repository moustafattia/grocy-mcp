"""Base adapter interfaces and prompt-building helpers."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from testbed.utils import read_text

_CODE_FENCE_RE = re.compile(r"^```[^\n]*\n(.*?)```\s*$", re.DOTALL)


def _strip_code_fences(value: str) -> str:
    """Remove a single Markdown code fence wrapper, if present."""
    match = _CODE_FENCE_RE.match(value.strip())
    if match:
        return match.group(1).strip()
    return value.strip()


def parse_json_array(text: str) -> list[dict]:
    payload = json.loads(_strip_code_fences(text))
    if not isinstance(payload, list):
        raise RuntimeError("Model output was not a JSON array.")
    if not all(isinstance(item, dict) for item in payload):
        raise RuntimeError("Model output must be an array of objects.")
    return payload


def build_prompt(
    task_type: str,
    asset_ref: Path,
    source_metadata: dict[str, Any],
    prompt_template: str,
) -> str:
    asset_path = asset_ref
    if source_metadata.get("text_asset_path"):
        asset_path = asset_ref.parent / str(source_metadata["text_asset_path"])

    prompt_lines = [
        prompt_template.rstrip(),
        "",
        f"TASK_TYPE: {task_type}",
        f"ASSET_PATH: {asset_ref.as_posix()}",
    ]
    if source_metadata:
        prompt_lines.append("SOURCE_METADATA:")
        prompt_lines.append(json.dumps(source_metadata, indent=2, sort_keys=True))
    prompt_lines.append("ASSET_CONTENT:")
    prompt_lines.append(read_text(asset_path))
    return "\n".join(prompt_lines)


class ModelAdapter(ABC):
    provider_name = "unknown"

    @abstractmethod
    def extract(
        self,
        task_type: str,
        asset_ref: Path,
        source_metadata: dict[str, Any],
        prompt_template: str,
    ) -> list[dict]:
        raise NotImplementedError
