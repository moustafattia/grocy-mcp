"""Configuration loading from explicit overrides, env vars, and TOML files."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_dir


@dataclass(frozen=True)
class Config:
    url: str
    api_key: str


def _load_toml() -> dict:
    config_path = Path(user_config_dir("grocy-mcp")) / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("grocy", {})
    return {}


def load_config(
    url: str | None = None,
    api_key: str | None = None,
) -> Config:
    """Load config with priority: explicit args > env vars > TOML file."""
    toml = _load_toml()

    resolved_url = url or os.environ.get("GROCY_URL") or toml.get("url")
    resolved_key = api_key or os.environ.get("GROCY_API_KEY") or toml.get("api_key")

    if not resolved_url:
        raise ValueError(
            "Grocy URL not configured. Set the GROCY_URL environment variable "
            "or add url to the config file."
        )
    if not resolved_key:
        raise ValueError(
            "Grocy API key not configured. Set the GROCY_API_KEY environment variable "
            "or add api_key to the config file."
        )

    return Config(url=resolved_url.rstrip("/"), api_key=resolved_key)
