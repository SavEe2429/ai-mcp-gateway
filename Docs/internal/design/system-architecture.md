# System Architecture Design

## Overview

`ai-mcp-gateway` is a modular local MCP Streamable HTTP bridge exposing sandboxed workspace tools,
terminal execution, desktop/window capture, and external stdio MCP integrations to remote AI
assistants over HTTPS (Tailscale Funnel) with OAuth 2.1 + PKCE security.

## Topology Diagram

```text
                +------------------------------------------------+
                |   Web AI Assistants (Gemini / Claude / ChatGPT)|
                +-----------------------+------------------------+
                                        |
                          Tailscale Funnel (HTTPS)
                                        |
                                        v
+------------------------------------------------------------------------+
|                            ai-mcp-gateway                              |
|                                                                        |
|  +--------------------+   +--------------------+   +----------------+  |
|  | ASGI Security      |   | Streamable HTTP    |   | Localhost      |  |
|  | Middleware         |-->| MCP Router (/mcp)  |   | Web Dashboard  |  |
|  | (Shield/Auth/ID)   |   | (core/mcp_server)  |   | (ui_routes.py) |  |
|  +--------------------+   +---------+----------+   +--------+-------+  |
|                                     |                       |          |
|                                     v                       |          |
|                        +-------------------------+          |          |
|                        | Built-in & External     |          |          |
|                        | MCP Tools               |<---------+          |
|                        | (fs/term/vis + stdio)   |                     |
|                        +------------+------------+                     |
|                                     |                                  |
|                    +----------------+----------------+                 |
|                    v                                 v                 |
|       +-------------------------+       +-------------------------+    |
|       | Sandboxed Workspace     |       | SQLite Runtime Store    |    |
|       | (workspace/)            |       | (data/gateway.db)       |    |
|       +-------------------------+       +-------------------------+    |
+------------------------------------------------------------------------+
```

## Module Boundaries

- `src/ai_mcp_gateway/cli.py` and `__main__.py`: Encapsulated CLI and module entry points.
- `src/ai_mcp_gateway/main.py`: FastAPI ASGI composition root, lifespan manager, single-instance
  lock acquisition, masked startup banner, and Uvicorn runner.
- `src/ai_mcp_gateway/core/instance_lock.py`: Cross-platform OS-enforced non-blocking file lock
  (`data/gateway.lock`) preventing concurrent duplicate gateway processes.
- `src/ai_mcp_gateway/core/mcp_server.py`: Built-in `FastMCP`/`MCPServer` instance and tool
  bindings.
- `src/ai_mcp_gateway/core/mcp_client_manager.py`: External GitHub MCP installer and stdio client
  bridge.
- `src/ai_mcp_gateway/core/auth.py`: RFC 8414 / RFC 9728 OAuth metadata, manual secret-verified
  `/oauth/authorize` consent form, PKCE (`S256`), and non-bypassable `/oauth/token` issuance.
- `src/ai_mcp_gateway/core/database.py`: SQLite WAL persistence for OAuth tokens, audit logs, IP
  bans, and external MCP configs.
- `src/ai_mcp_gateway/core/state.py`: Shared runtime state, approval futures, IP blacklist cache,
  and WebSocket broadcaster.
- `src/ai_mcp_gateway/core/tunnel.py`: Tailscale Funnel startup and teardown automation.
- `src/ai_mcp_gateway/interfaces/ui_routes.py` & `interfaces/ui/index.html`: Localhost-only Web
  Dashboard routes and SPA frontend.
- `src/ai_mcp_gateway/interfaces/middleware/`: Modular security shield, identity resolver, logging
  filter, and ASGI pipeline.
- `src/ai_mcp_gateway/model/config.py` & `utils/config.py`: Pydantic SSOT configuration schema and
  frozen-binary path resolution.
- `src/ai_mcp_gateway/tools/`: Sandboxed `filesystem.py`, `terminal.py`, and `vision.py` tools.
