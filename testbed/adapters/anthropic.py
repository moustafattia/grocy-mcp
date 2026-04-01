"""Anthropic text extraction adapter for nightly/manual testbed runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from testbed.adapters.base import ModelAdapter, build_prompt, parse_json_array


class AnthropicAdapter(ModelAdapter):
    provider_name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def extract(
        self,
        task_type: str,
        asset_ref: Path,
        source_metadata: dict[str, Any],
        prompt_template: str,
    ) -> list[dict]:
        """Extract normalized grocery items via the Anthropic Messages API."""
        prompt = build_prompt(task_type, asset_ref, source_metadata, prompt_template)
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 1200,
                "system": "Return only valid JSON arrays of normalized grocery items.",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        parts = data.get("content", [])
        content = "\n".join(part.get("text", "") for part in parts if part.get("type") == "text")
        return parse_json_array(content)
