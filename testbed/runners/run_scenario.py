"""Run a single testbed scenario through CLI or MCP execution paths."""

from __future__ import annotations

import argparse
import asyncio
import os
import time

from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport

from grocy_mcp.client import GrocyClient
from grocy_mcp.mcp.server import create_mcp_server
from testbed.config import TestbedConfig
from testbed.evaluators.report import write_report
from testbed.evaluators.state import assert_expected_outcome, capture_state
from testbed.models import RunReport
from testbed.runners.common import (
    build_stock_apply_items,
    flatten_shopping_actions,
    load_normalized_items,
    load_prompt_template,
    load_scenario_bundle,
    run_cli_json,
    run_cli_text,
    temporary_env,
)
from testbed.seed.auth_proxy import GrocyAuthProxy
from testbed.utils import ensure_dir, hash_text


def _structured_result(payload):
    if isinstance(payload, dict) and "result" in payload:
        return payload["result"]
    return payload


class _InProcessMcpRunner:
    def __init__(self, config: TestbedConfig) -> None:
        self.config = config
        self.server = create_mcp_server()

    async def call(self, tool_name: str, **arguments):
        with temporary_env(
            {
                "GROCY_URL": self.config.proxy_url,
                "GROCY_API_KEY": self.config.proxy_api_key,
            }
        ):
            result = await self.server.call_tool(tool_name, arguments)
        return _structured_result(result.structured_content)


class _StdioMcpRunner:
    def __init__(self, config: TestbedConfig) -> None:
        self.config = config
        self.transport = StdioTransport(
            command=config.mcp_bin,
            args=["--transport", "stdio"],
            env={
                **os.environ,
                "GROCY_URL": config.proxy_url,
                "GROCY_API_KEY": config.proxy_api_key,
            },
            cwd=str(config.root_dir),
        )

    async def __aenter__(self):
        self.client = Client(self.transport)
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.client.__aexit__(exc_type, exc, tb)

    async def call(self, tool_name: str, **arguments):
        result = await self.client.call_tool(tool_name, arguments)
        return _structured_result(result)


async def _product_map(client: GrocyClient) -> dict[str, int]:
    products = await client.get_objects("products")
    return {" ".join(item.get("name", "").casefold().split()): int(item["id"]) for item in products}


async def _receipt_stock_flow(
    mode: str,
    manifest,
    config: TestbedConfig,
    normalized_items: list[dict],
    confirmation,
    mcp_transport: str,
) -> tuple[object, list[dict], list[dict]]:
    preview_output = None
    confirmation_actions: list[dict] = []
    apply_actions: list[dict] = []

    async with GrocyClient(config.proxy_url, config.proxy_api_key) as state_client:
        products_by_name = await _product_map(state_client)

    if mode == "cli":
        preview_output = run_cli_json(
            config,
            ["workflow", "match-products-preview", json_dumps(normalized_items)],
        )
        apply_items, confirmation_actions = build_stock_apply_items(
            preview_output, normalized_items, confirmation, products_by_name
        )
        run_cli_json(config, ["workflow", "stock-intake-apply", json_dumps(apply_items)])
        reconcile_preview = run_cli_json(
            config,
            [
                "workflow",
                "shopping-reconcile-preview",
                json_dumps(apply_items),
                "--list-id",
                str(manifest.source_metadata.get("shopping_list_id", 1)),
            ],
        )
        apply_actions = flatten_shopping_actions(reconcile_preview)
        if apply_actions:
            run_cli_json(
                config, ["workflow", "shopping-reconcile-apply", json_dumps(apply_actions)]
            )
        preview_output = {
            "match_preview": preview_output,
            "shopping_reconcile_preview": reconcile_preview,
        }
        return preview_output, confirmation_actions, apply_actions

    runner = _InProcessMcpRunner(config) if mcp_transport == "in_process" else None
    if mcp_transport == "stdio":
        async with _StdioMcpRunner(config) as stdio_runner:
            return await _receipt_stock_flow_mcp(
                stdio_runner,
                manifest,
                normalized_items,
                confirmation,
                products_by_name,
            )
    if runner is None:
        raise RuntimeError(f"Unsupported MCP transport '{mcp_transport}'.")
    return await _receipt_stock_flow_mcp(
        runner,
        manifest,
        normalized_items,
        confirmation,
        products_by_name,
    )


async def _receipt_stock_flow_mcp(
    runner,
    manifest,
    normalized_items: list[dict],
    confirmation,
    products_by_name: dict[str, int],
) -> tuple[dict, list[dict], list[dict]]:
    match_preview = await runner.call(
        "workflow_match_products_preview_tool",
        items=json_dumps(normalized_items),
    )
    apply_items, confirmation_actions = build_stock_apply_items(
        match_preview, normalized_items, confirmation, products_by_name
    )
    await runner.call("workflow_stock_intake_apply_tool", items=json_dumps(apply_items))
    reconcile_preview = await runner.call(
        "workflow_shopping_reconcile_preview_tool",
        items=json_dumps(apply_items),
        list_id=int(manifest.source_metadata.get("shopping_list_id", 1)),
    )
    apply_actions = flatten_shopping_actions(reconcile_preview)
    if apply_actions:
        await runner.call(
            "workflow_shopping_reconcile_apply_tool",
            actions=json_dumps(apply_actions),
        )
    return (
        {"match_preview": match_preview, "shopping_reconcile_preview": reconcile_preview},
        confirmation_actions,
        apply_actions,
    )


async def _pantry_audit_flow(
    mode: str, config: TestbedConfig, normalized_items: list[dict], mcp_transport: str
):
    if mode == "cli":
        preview = run_cli_json(
            config, ["workflow", "match-products-preview", json_dumps(normalized_items)]
        )
        return preview, [], []
    if mcp_transport == "stdio":
        async with _StdioMcpRunner(config) as runner:
            preview = await runner.call(
                "workflow_match_products_preview_tool",
                items=json_dumps(normalized_items),
            )
            return preview, [], []
    runner = _InProcessMcpRunner(config)
    preview = await runner.call(
        "workflow_match_products_preview_tool",
        items=json_dumps(normalized_items),
    )
    return preview, [], []


async def _recipe_url_shopping_flow(
    mode: str,
    manifest,
    config: TestbedConfig,
    normalized_items: list[dict],
    confirmation,
    mcp_transport: str,
) -> tuple[object, list[dict], list[dict]]:
    async with GrocyClient(config.proxy_url, config.proxy_api_key) as state_client:
        products_by_name = await _product_map(state_client)

    if mode == "cli":
        preview = run_cli_json(
            config, ["workflow", "match-products-preview", json_dumps(normalized_items)]
        )
        apply_items, confirmation_actions = build_stock_apply_items(
            preview, normalized_items, confirmation, products_by_name
        )
        list_id = int(manifest.source_metadata.get("shopping_list_id", 1))
        for item in apply_items:
            args = [
                "shopping",
                "add",
                str(item["product_id"]),
                "--amount",
                str(item["amount"]),
                "--list-id",
                str(list_id),
            ]
            if item.get("note"):
                args.extend(["--note", str(item["note"])])
            run_cli_text(config, args)
        return preview, confirmation_actions, apply_items

    if mcp_transport == "stdio":
        async with _StdioMcpRunner(config) as runner:
            return await _recipe_url_shopping_flow_mcp(
                runner, manifest, normalized_items, confirmation, products_by_name
            )
    runner = _InProcessMcpRunner(config)
    return await _recipe_url_shopping_flow_mcp(
        runner, manifest, normalized_items, confirmation, products_by_name
    )


async def _recipe_url_shopping_flow_mcp(
    runner,
    manifest,
    normalized_items: list[dict],
    confirmation,
    products_by_name: dict[str, int],
) -> tuple[object, list[dict], list[dict]]:
    preview = await runner.call(
        "workflow_match_products_preview_tool",
        items=json_dumps(normalized_items),
    )
    apply_items, confirmation_actions = build_stock_apply_items(
        preview, normalized_items, confirmation, products_by_name
    )
    list_id = int(manifest.source_metadata.get("shopping_list_id", 1))
    for item in apply_items:
        await runner.call(
            "shopping_list_add_tool",
            product=str(item["product_id"]),
            amount=float(item["amount"]),
            list_id=list_id,
            note=item.get("note"),
        )
    return preview, confirmation_actions, apply_items


def json_dumps(value) -> str:
    import json

    return json.dumps(value)


async def run_scenario(
    scenario_id: str,
    mode: str,
    source: str,
    provider_model: str | None = None,
    mcp_transport: str = "in_process",
) -> RunReport:
    config = TestbedConfig.from_env()
    manifest, confirmation, expected = load_scenario_bundle(config, scenario_id)
    normalized_items = load_normalized_items(manifest, config, source, provider_model)
    shopping_names = [item.list_name for item in expected.shopping_lists]

    start = time.perf_counter()
    with GrocyAuthProxy(
        proxy_url=config.proxy_url,
        backend_base=config.grocy_base_url,
        api_key=config.proxy_api_key,
        username=config.admin_username,
        password=config.admin_password,
    ):
        async with GrocyClient(config.proxy_url, config.proxy_api_key) as client:
            state_before = await capture_state(client, shopping_names)

        if manifest.task_type == "receipt_stock":
            preview_output, confirmation_actions, apply_actions = await _receipt_stock_flow(
                mode,
                manifest,
                config,
                normalized_items,
                confirmation,
                mcp_transport,
            )
        elif manifest.task_type == "pantry_audit":
            preview_output, confirmation_actions, apply_actions = await _pantry_audit_flow(
                mode, config, normalized_items, mcp_transport
            )
        elif manifest.task_type == "recipe_url_shopping":
            preview_output, confirmation_actions, apply_actions = await _recipe_url_shopping_flow(
                mode,
                manifest,
                config,
                normalized_items,
                confirmation,
                mcp_transport,
            )
        else:  # pragma: no cover - manifest validation prevents this
            raise RuntimeError(f"Unsupported task type '{manifest.task_type}'.")

        async with GrocyClient(config.proxy_url, config.proxy_api_key) as client:
            state_after = await capture_state(client, shopping_names)

    assertions = assert_expected_outcome(state_before, state_after, expected)
    passed = all(item["passed"] for item in assertions)
    duration_ms = int((time.perf_counter() - start) * 1000)
    prompt_hash = hash_text(load_prompt_template(config, manifest.task_type))
    report = RunReport(
        scenario_id=scenario_id,
        mode=mode,
        source=source,
        provider=provider_model or source,
        prompt_hash=prompt_hash,
        normalized_items=normalized_items,
        preview_output=preview_output,
        confirmation_actions=confirmation_actions,
        apply_actions=apply_actions,
        state_before=state_before,
        state_after=state_after,
        assertions=assertions,
        status="passed" if passed else "failed",
        duration_ms=duration_ms,
    )
    ensure_dir(config.reports_dir)
    report_name = f"{scenario_id}-{mode}-{source}.json"
    write_report(config.reports_dir / report_name, report)
    if not passed:
        raise RuntimeError(
            f"Scenario {scenario_id} failed. See {config.reports_dir / report_name}."
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario_id")
    parser.add_argument("--mode", choices=["cli", "mcp"], required=True)
    parser.add_argument(
        "--source", choices=["golden", "openai", "anthropic", "openai_compatible"], required=True
    )
    parser.add_argument("--provider-model")
    parser.add_argument("--mcp-transport", choices=["in_process", "stdio"], default="in_process")
    args = parser.parse_args()
    asyncio.run(
        run_scenario(
            scenario_id=args.scenario_id,
            mode=args.mode,
            source=args.source,
            provider_model=args.provider_model,
            mcp_transport=args.mcp_transport,
        )
    )


if __name__ == "__main__":
    main()
