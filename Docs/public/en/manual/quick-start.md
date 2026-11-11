# Quick Start & Installation Guide

> Language: **English** | [ภาษาไทย](../../th/manual/quick-start.md)

This guide walks you through installing, configuring, and running `ai-mcp-gateway`.

---

## Option A: Windows Standalone Executable (Recommended for End Users)

1. Download `ai-mcp-gateway-windows-x64.zip` from the
   [GitHub Releases](https://github.com/SavEe2429/ai-mcp-gateway/releases) page.
2. Extract the archive to a writable directory such as `C:\Tools\ai-mcp-gateway\`.
   - Do **not** place it under `C:\Program Files\` because the gateway creates runtime folders
     beside `ai-mcp-gateway.exe`.
3. _(Recommended for Gemini / Claude / ChatGPT)_ Ensure **Tailscale** is installed, signed in, and
   configured with MagicDNS + HTTPS + Funnel enabled. See
   [Tailscale Funnel Setup](tailscale-setup.md).
4. Start the gateway by double-clicking `ai-mcp-gateway.exe` or running it in PowerShell:
   ```powershell
   cd C:\Tools\ai-mcp-gateway
   .\ai-mcp-gateway.exe
   ```
5. On startup, the gateway prints a connection banner in the terminal:
   ```text
   =================================================================
   AI Agent MCP Gateway Starting
   Local Web Dashboard : http://localhost:3000/ui
   Active Workspace    : C:\Tools\ai-mcp-gateway\workspace
   MCP Server Endpoint : https://<your-machine>.ts.net/mcp
   Client ID           : local-mcp
   Client Secret       : ************xxxx (view full secret in /ui)
   =================================================================
   ```
   Your default browser opens `http://localhost:3000/ui` automatically with a **Startup Workspace
   Selection** prompt, and four runtime paths are managed next to the `.exe`:
   - `data/gateway.db`: SQLite database storing OAuth tokens, audit logs, IP bans, and installed
     external MCP servers.
   - `data/client_secret.key`: Auto-generated high-entropy OAuth client secret.
   - `data/gateway.lock`: OS-enforced single-instance lock file preventing two gateway processes
     from running simultaneously (overridable via `GATEWAY_LOCK_FILE`).
   - `workspace/`: Sandboxed directory accessible to AI filesystem and terminal tools.

---

## Option B: Run from Source (`uv` + Python 3.14+)

### Prerequisites

- Python `3.14` or newer
- [`uv`](https://docs.astral.sh/uv/) package manager
- _(Optional)_ [Tailscale CLI](https://tailscale.com/download) available in your system `PATH`

### Setup & Launch

```bash
git clone https://github.com/SavEe2429/ai-mcp-gateway.git
cd ai-mcp-gateway
uv sync --dev

# Launch using the registered console entrypoint
uv run ai-mcp-gateway

# Or launch via module execution
uv run python -m ai_mcp_gateway
```

---

## Customizing Configuration

Settings are governed by a Single Source of Truth schema (`config/config.yaml`) validated at startup
by Pydantic.

### Overriding Settings in `.exe` Mode

1. Create a `config/` folder next to `ai-mcp-gateway.exe`.
2. Copy [config/config.yaml](../../../../config/config.yaml) into `config/config.yaml` and edit
   values as needed.
3. Configuration lookup order (`find_config_yaml`):
   1. Explicit `GATEWAY_CONFIG_PATH` environment variable
   2. `<runtime_dir>/config/config.yaml` (beside `.exe` or repo root)
   3. `<cwd>/config/config.yaml`
   4. Default bundled configuration inside the executable

### Useful Options in `config/config.yaml`

- `server.port`: Gateway HTTP port (default: `3000`).
- `server.enable_tailscale_funnel`: Set to `true` (default) to expose `/mcp` via Tailscale Funnel,
  or `false` for local-only mode (`http://localhost:3000/mcp`).
- `session.ttl`: OAuth access token sliding lifetime in seconds (default: `604800` = 7 days).
- `session.terminal_timeout`: Seconds before `run_command` switches to background execution
  (default: `60.0`).
- `auth.client_id` / `auth.client_secret`: Override default `local-mcp` ID or specify a fixed secret
  instead of `data/client_secret.key` (also overridable via `MCP_CLIENT_ID`, `MCP_CLIENT_SECRET`, or
  `GATEWAY_SECRET_KEY`).

---

## Daily Usage Checklist

1. **Verify Endpoint**: Check the terminal banner or top-right **MCP Endpoint Bar** in
   `http://localhost:3000/ui`.
2. **Select Workspace**: Choose or confirm the target folder in the **Startup Workspace Selection**
   modal when opening `http://localhost:3000/ui` (or use **Workspace -> Browse** in the sidebar
   later).
3. **Set Permissions**: Toggle `Read Files`, `Write & Patch`, `Terminal Commands`,
   `Vision & Screenshots`, and `HITL Manual Approval` (`ON` recommended when letting remote AIs
   write files or execute shell commands).
4. **Connect AI Client**: Follow [MCP Integration Guide](mcp-integration.md) using the
   `https://<your-domain>/mcp` URL and OAuth credentials from the sidebar.
5. **Stop Cleanly**: Press `Ctrl+C` in the terminal window to gracefully shut down external stdio
   MCP child processes and close database connections.

---

## Next Steps

- [Tailscale Funnel Setup & Architecture](tailscale-setup.md)
- [Web Dashboard User Guide](dashboard-guide.md)
- [MCP Integration Guide](mcp-integration.md)
