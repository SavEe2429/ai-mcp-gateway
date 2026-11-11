# Core Package (`src/ai_mcp_gateway/core/`)

Core runtime, security, persistence, and protocol orchestration modules.

## Contents

- `auth.py`: RFC 8414 / RFC 9728 OAuth metadata endpoints, manual secret-verified `/oauth/authorize`
  consent flow, PKCE (`S256`/`plain`), and `/oauth/token` grants (`authorization_code`,
  `client_credentials`, `refresh_token`).
- `database.py`: SQLite persistence layer (`data/gateway.db`) for OAuth tokens, audit logs, banned
  IPs, AI usage stats, and external MCP server registrations.
- `instance_lock.py`: Cross-platform OS-enforced non-blocking lock (`data/gateway.lock`) preventing
  concurrent duplicate gateway processes.
- `mcp_client_manager.py`: GitHub MCP installer and stdio subprocess aggregator bridging external
  MCP tools into the gateway.
- `mcp_server.py`: FastMCP server instance, activity logging/WebSocket broadcasting, and MCP tool
  definitions.
- `state.py`: In-memory `AppState` singleton for workspace selection, runtime permission toggles,
  HITL approvals, IP bans, and WebSocket clients.
- `tunnel.py`: Tailscale MagicDNS discovery and Funnel lifecycle helpers (`start_tailscale_funnel`,
  `stop_tailscale_funnel`).
