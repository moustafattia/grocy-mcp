"""Reset the writable demo environment and re-seed it from the canonical profile."""

from __future__ import annotations

from testbed.config import TestbedConfig
from testbed.seed.manage import ensure_demo_environment


def main() -> None:
    config = TestbedConfig.from_env()
    warnings = ensure_demo_environment(config, config.seed_dir / "demo_profile.json")
    if warnings:
        print("Demo environment reset with warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("Demo environment reset and re-seeded.")


if __name__ == "__main__":
    main()
