"""OpenAI text extraction adapter for nightly/manual testbed runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from testbed.adapters.base import ModelAdapter, build_prompt, parse_json_array


class OpenAIAdapter(ModelAdapter):
    provider_name = "openai"

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
        """Extract normalized grocery items via the OpenAI Chat Completions API."""
        prompt = build_prompt(task_type, asset_ref, source_metadata, prompt_template)
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only valid JSON arrays of normalized grocery items.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return parse_json_array(content)
