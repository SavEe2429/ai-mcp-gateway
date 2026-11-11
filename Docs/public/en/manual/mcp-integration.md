# MCP Integration Guide

> Language: **English** | [ภาษาไทย](../../th/manual/mcp-integration.md)

This guide explains how external AI platforms (Google Gemini, Anthropic Claude, OpenAI ChatGPT, and MCP-compatible clients) connect to `ai-mcp-gateway`.

---

## 1. Protocol & Discovery Endpoints

`ai-mcp-gateway` implements the MCP Specification (`2024-11-05+`) over **Streamable HTTP**:

- **MCP Endpoint**: `https://<your-funnel-domain>/mcp` (displayed in the top-right Endpoint bar of the [Web Dashboard](dashboard-guide.md) and in the startup console).
- **Transport**: `POST /mcp` (JSON-RPC 2.0) and `DELETE /mcp` (session termination); legacy `/sse` requests are transparently rewritten to `/mcp`.
- **Session Recovery**: If an AI client sends a stale `mcp-session-id` after the gateway restarts, the middleware automatically triggers transparent re-initialization so sessions recover cleanly.
- **OAuth 2.0 / 2.1 Discovery (RFC 8414 & RFC 9728)**:
  - `GET /.well-known/oauth-protected-resource`
  - `GET /.well-known/oauth-authorization-server`
  - `GET /oauth/authorize` (PKCE `S256` supported)
  - `POST /oauth/token` (`authorization_code`, `refresh_token`, and `client_credentials`)

---

## 2. Finding Your Credentials

By default, `config/config.yaml` sets `auth.client_id: "local-mcp"` and generates a random secret stored in `data/client_secret.key`. Both values are visible in:
1. The startup terminal banner
2. The **OAuth Credentials** panel in the Web Dashboard sidebar (`http://localhost:3000/ui`) — click `Show` / `Copy`

*(Allowed OAuth redirect domains include `claude.ai`, `anthropic.com`, `chatgpt.com`, `openai.com`, `google.com`, `googleapis.com`, `googleusercontent.com`, `gemini.google.com`, plus `localhost` / `127.0.0.1`.)*

---

## 3. Connecting AI Clients

### Google Gemini (Custom Apps / Connectors)
1. Ensure Tailscale Funnel is active so `https://<your-funnel-domain>/mcp` is reachable (see [Tailscale Setup](tailscale-setup.md)).
2. Create a Custom App or MCP Connector in Gemini / Google AI Studio:
   - **MCP Server URL**: `https://<your-funnel-domain>/mcp`
   - **Authentication**: OAuth 2.0
   - **Client ID**: `local-mcp` (or your configured value)
   - **Client Secret**: Copied from the Web Dashboard
   - **Authorization Endpoint**: `https://<your-funnel-domain>/oauth/authorize`
   - **Token Endpoint**: `https://<your-funnel-domain>/oauth/token`
3. Complete the authorization redirect in your browser. The **Google Gemini** telemetry card will begin tracking request counts and Session TTL.

### Anthropic Claude
1. Add a Custom MCP Connector pointing to `https://<your-funnel-domain>/mcp`.
2. Claude discovers OAuth endpoints automatically via `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server`.
3. Provide your `Client ID` and `Client Secret` if prompted, authorize via browser, and monitor calls under the **Claude AI** card.

### OpenAI ChatGPT
1. Register a remote MCP connector using `https://<your-funnel-domain>/mcp` and complete the OAuth 2.1 + PKCE authorization flow.
2. Tool calls carrying OpenAI `_meta` metadata are automatically identified and tracked under the **ChatGPT** card.

### Local Clients (Cursor / Same-Machine Testing)
- If running locally without Tailscale (`enable_tailscale_funnel: false`), point your MCP client to `http://localhost:3000/mcp`.
- You can obtain a Bearer token locally via the OAuth endpoints (`/oauth/authorize` + `/oauth/token` or `client_credentials` grant with `Client ID` and `Client Secret`).

---

## 4. Built-in & Bridged MCP Tools

Once connected, AI clients can invoke the following tools (governed by your **Access Control** toggles and optional **HITL Manual Approval**):

- **Workspace Files** (`allow_read` / `allow_write`):
  - `list_workspace_files`, `read_workspace_file`, `write_workspace_file`, `patch_workspace_file`
- **Terminal Execution** (`allow_bash`):
  - `run_command` (auto-backgrounds long-running commands after `session.terminal_timeout`), `check_task_status`, `kill_task`
- **Vision & Window Capture** (`allow_vision`):
  - `read_workspace_image`, `list_active_windows`, `switch_active_window`, `capture_window_screenshot`, `take_desktop_screenshot`
- **External Bridged Tools**:
  - Any external GitHub MCP server installed via **MCP Client Hub** is exposed automatically as `<owner>_<repo>__<tool_name>`.
