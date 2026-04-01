# Testbed

The `testbed/` layer validates real Grocy workflows end to end against a disposable demo Grocy instance.

It covers both intended integration paths:

- MCP for chat-native LLM clients
- CLI JSON mode for agent systems such as OpenClaw

## What it does

- starts a disposable Grocy instance with Docker Compose
- seeds a deterministic demo household from `testbed/seed/demo_profile.json`
- exposes a fixed local testbed key through a small auth shim so the real `grocy` CLI and `grocy-mcp` server can run without external secrets
- runs fixture-driven scenarios in PR mode
- supports provider-backed nightly/manual runs for OpenAI, Anthropic, and OpenAI-compatible endpoints

## Quick start

From the repo root:

```bash
python -m testbed.seed.reset_demo_env
python -m testbed.runners.run_suite pr
```

Run a single scenario:

```bash
python -m testbed.runners.run_scenario receipt-stock-basic --mode cli --source golden
python -m testbed.runners.run_scenario receipt-stock-basic --mode mcp --source golden
```

Run the nightly/manual matrix once provider credentials are configured:

```bash
export OPENAI_API_KEY=...
export TESTBED_OPENAI_MODEL=...
export ANTHROPIC_API_KEY=...
export TESTBED_ANTHROPIC_MODEL=...
python -m testbed.runners.run_suite nightly
```

## Environment variables

- `TESTBED_GROCY_BASE_URL`
  Default: `http://127.0.0.1:9283`
- `TESTBED_PROXY_URL`
  Default: `http://127.0.0.1:9284`
- `TESTBED_PROXY_API_KEY`
  Default: `testbed-demo-key`
- `TESTBED_GROCY_ADMIN_USER`
  Default: `admin`
- `TESTBED_GROCY_ADMIN_PASSWORD`
  Default: `admin`
- `TESTBED_GROCY_CLI`
  Default: `grocy`
- `TESTBED_GROCY_MCP_BIN`
  Default: `grocy-mcp`
- `TESTBED_MANAGE_ENV`
  Default: enabled

Provider-backed runs:

- `OPENAI_API_KEY`
- `TESTBED_OPENAI_MODEL`
- `ANTHROPIC_API_KEY`
- `TESTBED_ANTHROPIC_MODEL`
- `TESTBED_OPENAI_COMPAT_BASE_URL`
- `TESTBED_OPENAI_COMPAT_API_KEY`
- `TESTBED_OPENAI_COMPAT_MODEL`

## Scenario artifacts

- `fixtures/`
  Frozen assets such as receipts, pantry illustrations, and recipe HTML snapshots
- `scenarios/*.json`
  Scenario manifests
- `scenarios/golden-items/`
  Expected normalized extraction JSON used in deterministic runs
- `scenarios/confirmations/`
  Explicit ambiguity-resolution decisions
- `scenarios/expected/`
  Expected final Grocy state assertions
- `prompts/`
  Provider-neutral extraction prompts

## Notes

- The disposable testbed does not depend on a real long-lived Grocy API key. Instead, the runner logs into the demo Grocy frontend with disposable admin credentials and exposes a fixed local testbed key through an auth shim so the real CLI and MCP surfaces still operate in API-key mode.
- PR mode is deterministic only.
- Nightly and release mode can add provider-backed extraction runs on top of the same seeded Grocy state and scenario manifests.

