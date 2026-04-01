"""OpenAI-compatible extraction adapter for local/open-model endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from testbed.adapters.base import ModelAdapter, build_prompt, parse_json_array


class OpenAICompatibleAdapter(ModelAdapter):
    provider_name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str | None, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def extract(
        self,
        task_type: str,
        asset_ref: Path,
        source_metadata: dict[str, Any],
        prompt_template: str,
    ) -> list[dict]:
        prompt = build_prompt(task_type, asset_ref, source_metadata, prompt_template)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
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
