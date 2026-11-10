# User Quick Start Guide

## Option A: Windows Directory Bundle (Recommended for End Users)

1. Download `ai-mcp-gateway-windows-x64.zip` from the [GitHub Releases](https://github.com/SavEe2429/ai-mcp-gateway/releases) page (starting at `v1.0.0`).
2. Extract the archive into a dedicated writable folder (for example `C:\Tools\ai-mcp-gateway\`).
3. Double-click `ai-mcp-gateway.exe` or run it from PowerShell:
   ```powershell
   .\ai-mcp-gateway.exe
   ```
4. On startup, the gateway prints your connection summary in the console, creates runtime folders beside the `.exe`, and opens the local dashboard:
   - `data/gateway.db`: SQLite database for OAuth tokens, audit logs, IP bans, and external MCP configs.
   - `data/client_secret.key`: Auto-generated high-entropy OAuth client secret.
   - `workspace/`: Sandboxed folder accessible to AI file and terminal tools.
5. Your browser opens the Web Dashboard at `http://localhost:3000/ui`.

### Customizing Configuration with `.exe`
To override default settings without rebuilding the executable:
1. Create a `config/` folder next to `ai-mcp-gateway.exe`.
2. Copy [config/config.yaml](../../../config/config.yaml) into `config/config.yaml` and adjust settings such as `server.port`, `server.enable_tailscale_funnel`, or `session.ttl`.

---

## Option B: Running from Source (`uv`)

```bash
git clone https://github.com/SavEe2429/ai-mcp-gateway.git
cd ai-mcp-gateway
uv sync --dev
uv run ai-mcp-gateway
```

---

## Next Steps

- Learn every button, toggle, tab, and security feature in the [Web Dashboard User Guide](dashboard-guide.md).
- Connect Google Gemini, Claude, or ChatGPT by following the [MCP Integration Guide](mcp-integration.md).
