"""Base adapter interfaces and prompt-building helpers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from testbed.utils import read_text


def _strip_code_fences(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```"):
        parts = stripped.split("```")
        if len(parts) >= 3:
            return parts[1].split("\n", 1)[-1].strip()
    return stripped


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
