# AI Agent MCP Gateway

> Language / ภาษา: **English** ([Docs](Docs/public/en/index.md)) |
> **[ภาษาไทย](Docs/public/th/index.md)**

[![CI Quality Gate](https://github.com/SavEe2429/ai-mcp-gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/SavEe2429/ai-mcp-gateway/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A secure local Model Context Protocol (MCP) gateway that exposes sandboxed tools (workspace files,
terminal commands, desktop/window capture, and bridged external stdio MCP servers) exclusively to
supported web-based AI assistants (**Anthropic Claude**, **Google Gemini**, and **OpenAI ChatGPT**) over
**MCP Streamable HTTP** and **Tailscale Funnel**.

---

## Supported AI Assistants

`ai-mcp-gateway` is designed, optimized, and verified **exclusively** for the following 3 major web AI platforms:

| AI Assistant | Supported Environment | Authentication Protocol |
| :--- | :--- | :--- |
| **Anthropic Claude** | [Claude.ai](https://claude.ai) (Web & Projects) | MCP Streamable HTTP + OAuth 2.0 / 2.1 (PKCE) |
| **Google Gemini** | [Google Gemini](https://gemini.google.com) (Web & Extensions / Custom Apps) | MCP Streamable HTTP + OAuth 2.0 / 2.1 (PKCE) |
| **OpenAI ChatGPT** | [ChatGPT](https://chatgpt.com) (Web & Custom GPTs) | MCP Streamable HTTP + OAuth 2.0 / 2.1 (PKCE) |

> [!IMPORTANT]
> **Strict Compatibility Scope:**
> This gateway officially supports **only Anthropic Claude, Google Gemini, and OpenAI ChatGPT (GPT)**. Other AI clients (such as local IDE agents like Cursor or Copilot, command-line MCP clients, or other third-party LLMs) are **not supported**. All external AI connections require public HTTPS exposure (via Tailscale Funnel) and OAuth 2.1 / Bearer token authentication.

---

## Key Capabilities

- **MCP Streamable HTTP (`POST /mcp`)**: Protocol `2024-11-05+` with automatic session recovery and
  legacy `/sse` rewrite compatibility.
- **Automated Tailscale Funnel HTTPS Exposure**: Automatically discovers your machine's MagicDNS
  hostname and opens `https://<your-node>.ts.net/mcp` without router port-forwarding or exposing
  your home IP.
- **OAuth 2.0 / 2.1 + PKCE (`S256`)**: RFC 8414 and RFC 9728 metadata discovery with per-provider
  Bearer token tracking (`Google Gemini`, `Claude AI`, `ChatGPT`).
- **Localhost-Locked Web Dashboard (`http://localhost:3000/ui`)**: Startup Workspace Selection
  prompt, real-time WebSocket audit logs, Human-in-the-Loop (HITL) approval queue, Developer HTTP
  Inspector, GitHub MCP Client Hub, and Security Shield / IP ban management.
- **Strict Sandboxing, Single-Instance Lock & Scanner Shield**: All file and terminal operations are
  confined to `workspace/` via `safe_path()` (blocking `data/` and `.env` secrets),
  `data/gateway.lock` prevents duplicate instances, and external bot probes (`.php`, `.env`,
  `/wp-*`) are auto-banned.
- **Portable Windows Bundle**: Pre-built `onedir` executable with runtime state (`data/`,
  `workspace/`, optional `config/config.yaml`) persisted cleanly beside `ai-mcp-gateway.exe`.

---

## Installation

### Option 1: Standalone Windows Executable (Recommended for End Users)

1. Download `ai-mcp-gateway-windows-x64.zip` from
   [GitHub Releases](https://github.com/SavEe2429/ai-mcp-gateway/releases).
2. Extract the archive into a writable folder (for example `C:\Tools\ai-mcp-gateway\`). Do **not**
   extract into read-only folders like `C:\Program Files\`.
3. _(For external AI access)_ Install and sign in to [Tailscale](https://tailscale.com/) with
   **MagicDNS**, **HTTPS Certificates**, and **Funnel** enabled. See the
   [Tailscale Setup Guide](Docs/public/en/manual/tailscale-setup.md).
4. Launch `ai-mcp-gateway.exe` (double-click or run from PowerShell):
   ```powershell
   .\ai-mcp-gateway.exe
   ```
5. On first launch, the gateway creates `data/gateway.db`, generates a random OAuth `client_secret`
   in `data/client_secret.key`, creates `data/gateway.lock` to prevent launching duplicate
   instances, creates `workspace/`, prints masked connection details in the terminal, and opens
   `http://localhost:3000/ui` with a startup Workspace Selection prompt.
6. _(Optional)_ Create a `config/` folder next to `ai-mcp-gateway.exe` and copy
   [config/config.yaml](config/config.yaml) there to override port, session TTL, or Tailscale
   settings without rebuilding.

### Option 2: Run from Source (`uv` + Python 3.14+)

**Prerequisites:**

- Python `3.14+`
- [`uv`](https://docs.astral.sh/uv/)
- _(Optional)_ [Tailscale CLI](https://tailscale.com/download) in `PATH` for remote HTTPS access

```bash
git clone https://github.com/SavEe2429/ai-mcp-gateway.git
cd ai-mcp-gateway
uv sync --dev

# Run via registered console script
uv run ai-mcp-gateway

# Or run as a Python module
uv run python -m ai_mcp_gateway
```

---

## How Tailscale Funnel Is Used

Supported remote AI platforms (**Anthropic Claude**, **Google Gemini**, **OpenAI ChatGPT**) require a
**valid public HTTPS endpoint** to reach your MCP server and complete OAuth 2.1 redirects.
`ai-mcp-gateway` uses **Tailscale Funnel** in `src/ai_mcp_gateway/core/tunnel.py` so you do not need a
domain name, reverse proxy, or router port-forwarding:

```text
Supported Remote AI (Claude / Gemini / ChatGPT)
   │  HTTPS (OAuth 2.1 + POST /mcp)
   ▼
Tailscale Edge (TLS Termination + MagicDNS)
   │  Adds `Tailscale-Funnel-Request` header
   ▼
Local PC -> Tailscale Daemon -> 127.0.0.1:3000 (ai-mcp-gateway)
   ├─ /mcp, /oauth/*, /.well-known/*  ──► Allowed (OAuth + Scanner Shield)
   └─ /ui, /api/ui/*                  ──► Blocked (403 Forbidden from Funnel)
```

### Automatic Startup Sequence (`start_tailscale_funnel`)

1. When `server.enable_tailscale_funnel: true` in `config/config.yaml` (default), `run_server()`
   calls `start_tailscale_funnel(port)`.
2. The gateway runs `tailscale status --json` and reads `Self.DNSName` (e.g.
   `my-pc.tailnet-abc.ts.net`).
3. It runs `tailscale funnel --bg <port>` to map public HTTPS port `443` to your local gateway port
   (`3000`).
4. The resulting endpoint `https://<your-node>.ts.net/mcp` is printed in the startup banner and
   displayed (masked by default) in the Web Dashboard header.
5. **Security Isolation:** `check_localhost_dashboard_guard` inspects `Tailscale-Funnel-Request`,
   `X-Forwarded-For`, `X-Forwarded-Host`, and the client IP so the control dashboard (`/ui`) and its
   APIs (`/api/ui/*`) remain strictly accessible from your local machine only.

> For local-only testing without Tailscale, set `server.enable_tailscale_funnel: false` in
> `config/config.yaml` and connect local clients to `http://localhost:3000/mcp`. Full prerequisites
> and ACL troubleshooting: [English Tailscale Guide](Docs/public/en/manual/tailscale-setup.md) |
> [คู่มือตั้งค่า Tailscale (ภาษาไทย)](Docs/public/th/manual/tailscale-setup.md).

---

## Typical Usage Workflow

1. **Start the Gateway**: Run `ai-mcp-gateway.exe` or `uv run ai-mcp-gateway`. Confirm the console
   shows `MCP Server Endpoint : https://<your-domain>/mcp` (`Client Secret` is masked in the
   console; view it inside `/ui`).
2. **Choose Workspace & Permissions**: When `http://localhost:3000/ui` opens, select or confirm your
   **Workspace** folder in the startup prompt, toggle **Access Control** (`Read`, `Write & Patch`,
   `Terminal`, `Vision`), and leave **HITL Manual Approval** `ON` if you want to approve every write
   or command.
3. **Copy OAuth Credentials**: Copy `Client ID` (default `local-mcp`), `Client Secret` (`Show` /
   `Copy`), and the masked **MCP Endpoint** URL from the top-right bar.
4. **Connect Your AI Assistant**: Paste the MCP URL and OAuth credentials into your supported AI
   assistant (**Anthropic Claude**, **Google Gemini**, or **OpenAI ChatGPT**) (see the
   [MCP Integration Guide](Docs/public/en/manual/mcp-integration.md)).
5. **Monitor & Manage**: Watch real-time tool calls under **Activity Log**, approve/deny pending
   commands, add extra GitHub stdio MCP servers in **MCP Client Hub**, and inspect blocked scanner
   IPs in **Banned IPs**.

---

## Developer Verification & Build

```bash
# Lint & formatting check
uv run ruff check src/ tests/ packaging/ templates/ .github/scripts/release/
uv run ruff format --check src/ tests/ packaging/ templates/ .github/scripts/release/

# Automated test suite
uv run pytest
uv run python -m unittest discover tests

# Secret leak scan (Gitleaks v8.30.1+)
gitleaks git --redact -v --no-banner .

# Build Windows standalone bundle (output in out/ai-mcp-gateway/, spec in packaging/)
uv run python packaging/build.py --mode onedir
```

---

## Documentation Index

### English (`Docs/public/en/`)

- [English Documentation Home](Docs/public/en/index.md)
- [Quick Start & Installation](Docs/public/en/manual/quick-start.md)
- [Tailscale Funnel Setup](Docs/public/en/manual/tailscale-setup.md)
- [Web Dashboard User Guide](Docs/public/en/manual/dashboard-guide.md)
- [MCP Integration Guide (Gemini / Claude / ChatGPT)](Docs/public/en/manual/mcp-integration.md)

### ภาษาไทย (`Docs/public/th/`)

- [หน้าหลักคู่มือภาษาไทย](Docs/public/th/index.md)
- [คู่มือติดตั้งและเริ่มใช้งาน](Docs/public/th/manual/quick-start.md)
- [คู่มือติดตั้งและใช้งาน Tailscale Funnel](Docs/public/th/manual/tailscale-setup.md)
- [คู่มือการใช้งาน Web Dashboard](Docs/public/th/manual/dashboard-guide.md)
- [คู่มือเชื่อมต่อ AI (Gemini / Claude / ChatGPT)](Docs/public/th/manual/mcp-integration.md)

### Engineering, Governance & Releases

- System Architecture (Internal):
  [Docs/internal/design/system-architecture.md](Docs/internal/design/system-architecture.md)
- Developer Onboarding (Internal):
  [Docs/internal/development/01.getting_started.md](Docs/internal/development/01.getting_started.md)
- Release Notes: [Docs/public/release-notes/README.md](Docs/public/release-notes/README.md) |
  [CHANGELOG.md](CHANGELOG.md)
- Contributing & Security: [CONTRIBUTING.md](CONTRIBUTING.md) | [SECURITY.md](SECURITY.md) |
  [logbook/README.md](logbook/README.md)

## License

Licensed under the [MIT License](LICENSE).
