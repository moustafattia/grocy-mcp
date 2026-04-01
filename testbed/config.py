"""Environment and path configuration for the testbed package."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from testbed.utils import ROOT_DIR, TESTBED_DIR


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().casefold() not in {"0", "false", "no", "off"}


@dataclass(frozen=True)
class TestbedConfig:
    root_dir: Path
    testbed_dir: Path
    fixtures_dir: Path
    prompts_dir: Path
    scenarios_dir: Path
    seed_dir: Path
    runtime_dir: Path
    reports_dir: Path
    grocy_base_url: str
    proxy_url: str
    proxy_api_key: str
    admin_username: str
    admin_password: str
    cli_bin: str
    mcp_bin: str
    manage_environment: bool
    openai_api_key: str | None
    openai_model: str | None
    anthropic_api_key: str | None
    anthropic_model: str | None
    openai_compatible_base_url: str | None
    openai_compatible_api_key: str | None
    openai_compatible_model: str | None

    @classmethod
    def from_env(cls) -> TestbedConfig:
        runtime_dir = TESTBED_DIR / "runtime"
        return cls(
            root_dir=ROOT_DIR,
            testbed_dir=TESTBED_DIR,
            fixtures_dir=TESTBED_DIR / "fixtures",
            prompts_dir=TESTBED_DIR / "prompts",
            scenarios_dir=TESTBED_DIR / "scenarios",
            seed_dir=TESTBED_DIR / "seed",
            runtime_dir=runtime_dir,
            reports_dir=runtime_dir / "reports",
            grocy_base_url=os.environ.get("TESTBED_GROCY_BASE_URL", "http://127.0.0.1:9283"),
            proxy_url=os.environ.get("TESTBED_PROXY_URL", "http://127.0.0.1:9284"),
            proxy_api_key=os.environ.get("TESTBED_PROXY_API_KEY", "testbed-demo-key"),
            admin_username=os.environ.get("TESTBED_GROCY_ADMIN_USER", "admin"),
            admin_password=os.environ.get("TESTBED_GROCY_ADMIN_PASSWORD", "admin"),
            cli_bin=os.environ.get("TESTBED_GROCY_CLI", "grocy"),
            mcp_bin=os.environ.get("TESTBED_GROCY_MCP_BIN", "grocy-mcp"),
            manage_environment=_env_flag("TESTBED_MANAGE_ENV", True),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            openai_model=os.environ.get("TESTBED_OPENAI_MODEL"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            anthropic_model=os.environ.get("TESTBED_ANTHROPIC_MODEL"),
            openai_compatible_base_url=os.environ.get("TESTBED_OPENAI_COMPAT_BASE_URL"),
            openai_compatible_api_key=os.environ.get("TESTBED_OPENAI_COMPAT_API_KEY"),
            openai_compatible_model=os.environ.get("TESTBED_OPENAI_COMPAT_MODEL"),
        )
