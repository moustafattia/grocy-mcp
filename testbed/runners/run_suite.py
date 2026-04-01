"""Run a named testbed suite matrix."""

from __future__ import annotations

import argparse
import asyncio

from testbed.config import TestbedConfig
from testbed.runners.common import source_ready
from testbed.runners.run_scenario import run_scenario
from testbed.seed.manage import ensure_demo_environment


SUITES = {
    "pr": [
        ("receipt-stock-basic", "cli", "golden", "in_process"),
        ("receipt-stock-basic", "mcp", "golden", "in_process"),
        ("pantry-audit-basic", "cli", "golden", "in_process"),
        ("pantry-audit-basic", "mcp", "golden", "in_process"),
        ("recipe-url-shopping-basic", "cli", "golden", "in_process"),
        ("recipe-url-shopping-basic", "mcp", "golden", "in_process"),
        ("receipt-stock-ambiguous", "cli", "golden", "in_process"),
        ("receipt-stock-ambiguous", "mcp", "golden", "in_process"),
    ],
    "nightly": [
        ("receipt-stock-basic", "cli", "golden", "in_process"),
        ("receipt-stock-basic", "mcp", "golden", "in_process"),
        ("pantry-audit-basic", "cli", "golden", "in_process"),
        ("pantry-audit-basic", "mcp", "golden", "in_process"),
        ("recipe-url-shopping-basic", "cli", "golden", "in_process"),
        ("recipe-url-shopping-basic", "mcp", "golden", "in_process"),
        ("receipt-stock-basic", "mcp", "openai", "stdio"),
        ("receipt-stock-basic", "mcp", "anthropic", "stdio"),
        ("pantry-audit-basic", "mcp", "openai_compatible", "stdio"),
        ("recipe-url-shopping-basic", "mcp", "openai", "stdio"),
        ("recipe-url-shopping-basic", "mcp", "anthropic", "stdio"),
    ],
    "release": [
        ("receipt-stock-basic", "cli", "golden", "in_process"),
        ("receipt-stock-basic", "mcp", "golden", "in_process"),
        ("pantry-audit-basic", "cli", "golden", "in_process"),
        ("recipe-url-shopping-basic", "cli", "golden", "in_process"),
        ("receipt-stock-basic", "mcp", "openai", "stdio"),
        ("recipe-url-shopping-basic", "mcp", "anthropic", "stdio"),
    ],
}


async def run_suite(name: str) -> list[str]:
    config = TestbedConfig.from_env()
    if name not in SUITES:
        raise RuntimeError(f"Unknown suite '{name}'.")

    warnings: list[str] = []
    for scenario_id, mode, source, transport in SUITES[name]:
        if config.manage_environment:
            warnings.extend(ensure_demo_environment(config, config.seed_dir / "demo_profile.json"))
        if not source_ready(source, config):
            warnings.append(f"Skipped {scenario_id}/{mode}/{source}: provider not configured.")
            continue
        provider_model = None
        if source == "openai":
            provider_model = config.openai_model
        elif source == "anthropic":
            provider_model = config.anthropic_model
        elif source == "openai_compatible":
            provider_model = config.openai_compatible_model

        await run_scenario(
            scenario_id=scenario_id,
            mode=mode,
            source=source,
            provider_model=provider_model,
            mcp_transport=transport,
        )
    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=sorted(SUITES))
    args = parser.parse_args()
    warnings = asyncio.run(run_suite(args.suite))
    if warnings:
        print("Suite completed with warnings:")
        for warning in warnings:
            print(f"  - {warning}")


if __name__ == "__main__":
    main()
