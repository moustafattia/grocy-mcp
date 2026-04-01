"""Bootstrap a running demo Grocy instance from the committed seed profile."""

from __future__ import annotations

from testbed.config import TestbedConfig
from testbed.seed.manage import bootstrap_demo_household


def main() -> None:
    config = TestbedConfig.from_env()
    warnings = bootstrap_demo_household(config, config.seed_dir / "demo_profile.json")
    if warnings:
        print("Bootstrapped demo environment with warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("Demo environment bootstrapped.")


if __name__ == "__main__":
    main()
