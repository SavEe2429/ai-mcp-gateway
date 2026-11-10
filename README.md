# AI Agent MCP Gateway

[![CI Quality Gate](https://github.com/SavEe2429/ai-mcp-gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/SavEe2429/ai-mcp-gateway/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A secure local bridge exposing sandboxed tools (filesystem, terminal, window/screen capture, and external stdio MCP integrations) to external AI assistants (Google Gemini, Anthropic Claude, OpenAI ChatGPT) over Model Context Protocol (MCP) Streamable HTTP and Tailscale Funnel.

## Features

- **MCP Streamable HTTP (`POST /mcp`)**: Protocol `2024-11-05+` support with session recovery and `/sse` compatibility rewrite.
- **Multi-AI Provider Telemetry**: Detects Google Gemini, Claude, ChatGPT, and Cursor clients with live per-provider usage tracking.
- **OAuth 2.0 / 2.1 + PKCE (`S256`)**: RFC 8414 metadata discovery, authorization, and Bearer token management.
- **Local Web Dashboard (`http://localhost:3000/ui`)**: Real-time log stream, human-in-the-loop approvals, traffic inspector, IP ban shield, and external MCP client manager.
- **Sandboxed Workspace**: Path-traversal and symlink/junction escape protection confined to `workspace/`.
- **Standalone Windows Executable**: Pre-built `.exe` distribution with portable runtime data (`data/`, `workspace/`, optional `config/config.yaml`) stored alongside the binary.

## Download and Run (Windows `.exe` - End Users)

1. Download `ai-mcp-gateway-windows-x64.zip` from the [GitHub Releases](https://github.com/SavEe2429/ai-mcp-gateway/releases) page (starting at `v1.0.0`).
2. Extract the archive into a dedicated folder (for example, `C:\Tools\ai-mcp-gateway\`).
3. Double-click `ai-mcp-gateway.exe` or run it from PowerShell/Terminal:
   ```powershell
   .\ai-mcp-gateway.exe
   ```
4. The gateway creates `data/` (SQLite database & auto-generated `client_secret.key`) and `workspace/` in the same directory and opens the local dashboard at `http://localhost:3000/ui`.
5. *(Optional)* To customize settings, create `config/config.yaml` next to `ai-mcp-gateway.exe` using [config/config.yaml](config/config.yaml) as a template.

## Developer Quick Start (From Source)

### 1. Prerequisites
- Python `3.14+`
- [`uv`](https://docs.astral.sh/uv/)
- *(Optional)* [Tailscale](https://tailscale.com/) for external HTTPS Funnel access

### 2. Install Dependencies
```bash
uv sync --dev
```

### 3. Run the Gateway
```bash
# Using registered console script
uv run ai-mcp-gateway

# Or via package module execution
uv run python -m ai_mcp_gateway
```

### 4. Verify Code Quality and Tests
```bash
uv run ruff check src/ tests/ packaging/
uv run pytest
```

### 5. Build Standalone Executable Locally
```bash
# Directory bundle (onedir - recommended)
uv run python packaging/build.py --mode onedir

# Single executable (onefile)
uv run python packaging/build.py --mode onefile
```
Build outputs are generated under `out/ai-mcp-gateway/`.

## Security Notes

- The Web Dashboard (`/ui`, `/api/ui/*`, `/ws/ui`) is strictly locked to localhost (`127.0.0.1`, `::1`).
- Never commit `data/gateway.db`, `data/client_secret.key`, `.env`, or private files in `workspace/`.
- See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## Documentation & Contributing

- Documentation Portal: [Docs/public/index.md](Docs/public/index.md)
- User Quick Start: [Docs/public/manual/quick-start.md](Docs/public/manual/quick-start.md)
- Web Dashboard User Guide: [Docs/public/manual/dashboard-guide.md](Docs/public/manual/dashboard-guide.md)
- MCP Integration Guide: [Docs/public/manual/mcp-integration.md](Docs/public/manual/mcp-integration.md)
- System Architecture (Internal): [Docs/internal/design/system-architecture.md](Docs/internal/design/system-architecture.md)
- Developer Onboarding (Internal): [Docs/internal/development/01.getting_started.md](Docs/internal/development/01.getting_started.md)
- Contributing Guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Engineering Logbook Policy: [logbook/README.md](logbook/README.md)

## License

Licensed under the [MIT License](LICENSE).
