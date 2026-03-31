# Grocy MCP Home Assistant Add-on — Design Spec

**Date:** 2026-03-31
**Status:** Draft

## Overview

Create a Home Assistant add-on that runs grocy-mcp as a persistent HTTP MCP server, enabling Claude.ai and other remote MCP clients to access Grocy tools. Follows the same architecture as the ha-mcp add-on.

Two deliverables:
1. **grocy-mcp v0.1.1** — add `--path`, `--host` args and `stateless_http` support to the server
2. **grocy-mcp-addon** — new GitHub repo (`moustafattia/grocy-mcp-addon`) with the HA add-on

## Part A: grocy-mcp Server Changes

### Changes to `src/grocy_mcp/mcp/server.py`

Add two new CLI arguments to `main()` (`--transport` and `--port` already exist):

| Argument | Type | Default | Status | Description |
|----------|------|---------|--------|-------------|
| `--transport` | str | `stdio` | existing | Transport mechanism |
| `--port` | int | `8000` | existing | Port for HTTP transport |
| `--path` | str | `/mcp` | **new** | MCP endpoint URL path |
| `--host` | str | `0.0.0.0` | **new** | Bind address for HTTP transport |

When `--transport streamable-http`, pass all kwargs plus `stateless_http=True` to `server.run()`. Stateless mode is appropriate because each grocy-mcp tool call is self-contained (creates its own HTTP client via `_get_client()`), with no server-side session state needed.

```python
server.run(
    transport="streamable-http",
    host=args.host,
    port=args.port,
    path=args.path,
    stateless_http=True,
)
```

### Version Bump

- Bump `pyproject.toml` version from `0.1.0` to `0.1.1`
- Bump `fastmcp` dependency from `>=2.0` to `>=3.2.0` (required for `path` and `stateless_http` kwargs)
- Rebuild and republish to PyPI

## Part B: grocy-mcp-addon Repository

### Repository Structure

```
grocy-mcp-addon/
├── repository.yaml
├── README.md
├── grocy-mcp/
│   ├── config.yaml
│   ├── Dockerfile
│   ├── start.py
│   ├── DOCS.md
│   ├── CHANGELOG.md
│   └── translations/
│       └── en.yaml
```

### repository.yaml

```yaml
name: Grocy MCP Add-on
url: https://github.com/moustafattia/grocy-mcp-addon
maintainer: Moustafa Attia
```

### config.yaml

```yaml
name: "Grocy MCP Server"
description: "MCP server for Grocy — AI agent access to stock, shopping lists, recipes and chores"
version: "0.1.0"
slug: grocy-mcp
url: "https://github.com/moustafattia/grocy-mcp-addon"
init: false
arch:
  - aarch64
  - amd64
icon: mdi:food-variant
startup: application
boot: manual
host_network: true
options:
  grocy_url: "http://homeassistant.local:9192"
  grocy_api_key: ""
  port: 9193
  secret_path: ""
schema:
  grocy_url: str
  grocy_api_key: str
  port: int
  secret_path: str?
```

### Dockerfile (Two-Stage Build)

**Stage 1 — Builder:**
- Base: `ghcr.io/astral-sh/uv:0.11.0-python3.13-trixie-slim`
- Install `grocy-mcp==0.1.1` from PyPI into `/app/.venv` using `uv pip install`
- Pin version to prevent unexpected breakage from future releases (update with each add-on release)
- Compile bytecode (`UV_COMPILE_BYTECODE=1`)
- Cache mounts for dependency layer optimization

**Stage 2 — Runtime:**
- Base: `python:3.13-slim`
- Copy `/app/.venv` from builder
- Copy `start.py` into container
- Set PATH to activate venv
- Entry point: `CMD ["python3", "/start.py"]`

### start.py

Pure Python startup script (no bashio). Sequence:

1. **Read config** — parse `/data/options.json` for `grocy_url`, `grocy_api_key`, `port`, `secret_path`
2. **Manage secret path:**
   - If `secret_path` option is non-empty: validate with regex `^/(?!.*://)\S{7,}$` (basic format check — must start with `/`, no `://`, at least 8 chars total), use it
   - Else if `/data/secret_path.txt` exists: load persisted path
   - Else: generate `/private_<22-char-urlsafe-token>` (128-bit entropy via `secrets.token_urlsafe(16)`)
   - Persist to `/data/secret_path.txt`
3. **Startup connectivity check** — attempt `GET {grocy_url}/api/system/info` with the API key. On failure, log a warning ("Grocy not reachable at {url} — tools will fail until Grocy is available") but continue startup (Grocy may come up later).
4. **Log MCP URL** — print startup banner with full endpoint URL:
   ```
   -----------------------------------------------------------
   Grocy MCP Server is running!
   MCP endpoint: http://<hostname>:9193/private_xyz...
   -----------------------------------------------------------
   ```
5. **Set environment** — export `GROCY_URL` and `GROCY_API_KEY` as env vars (used by `load_config()` in `config.py` which reads these env vars to configure the `GrocyClient`)
6. **Start server** — import and run grocy-mcp:
   ```python
   from grocy_mcp.mcp.server import create_mcp_server

   mcp = create_mcp_server()
   mcp.run(
       transport="streamable-http",
       host="0.0.0.0",
       port=port,
       path=secret_path,
       stateless_http=True,
   )
   ```

### translations/en.yaml

```yaml
configuration:
  grocy_url:
    name: Grocy URL
    description: URL of your Grocy instance (e.g. http://homeassistant.local:9192)
  grocy_api_key:
    name: Grocy API Key
    description: API key from Grocy (Settings > Manage API keys)
  port:
    name: Port
    description: HTTP port for the MCP server
  secret_path:
    name: Secret Path
    description: >-
      Custom secret URL path (leave empty to auto-generate).
      Must start with / and be at least 8 characters.
```

## Design Decisions

- **No Docker health check** — the startup connectivity check in `start.py` validates Grocy is reachable at boot. The HA Supervisor handles add-on process restarts if the container exits. A dedicated `/health` endpoint is not needed for this use case.
- **Stateless HTTP** — each tool call is self-contained, no session state needed.
- **host_network: true** — matches ha-mcp pattern, ensures Cloudflare Tunnel can reach the server at `http://homeassistant:<port>`.

## Security

- **Secret path** — 128-bit entropy, auto-generated on first boot, persisted across restarts
- **Cloudflare Tunnel** — provides TLS termination and network isolation
- **No additional auth** — same security model as ha-mcp

## Networking

- **Port 9193** — avoids conflicts with Grocy (9192) and ha-mcp (9583)
- **Cloudflare Tunnel route** (manual config step):
  `grocy-mcp.attiamo.com` → `http://homeassistant:9193`
- **Claude.ai endpoint:** `https://grocy-mcp.attiamo.com/private_xyz...`

## Manual Post-Install Steps

1. Install the add-on in HA (Settings > Add-ons > Repositories > add `https://github.com/moustafattia/grocy-mcp-addon`)
2. Configure `grocy_url` and `grocy_api_key` in the add-on options
3. Start the add-on, copy the MCP URL from the logs
4. Add Cloudflare Tunnel route: `grocy-mcp.attiamo.com` → `http://homeassistant:9193`
5. Add to Claude.ai: Settings > Integrations > Add MCP Server > paste full URL with secret path
