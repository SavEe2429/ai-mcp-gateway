# MCP Integration Guide

This guide explains how external AI platforms (Google Gemini, Anthropic Claude, OpenAI ChatGPT, and MCP-compatible clients) connect to `ai-mcp-gateway`.

## Protocol Overview

`ai-mcp-gateway` implements the MCP Specification (`2024-11-05+`) over **Streamable HTTP**:
- **MCP Endpoint**: `https://<tailscale-funnel-domain>/mcp` (displayed in the top-right Endpoint bar of the [Web Dashboard](dashboard-guide.md) and in the startup console)
- **Transport**: `POST /mcp` (JSON-RPC 2.0) and `DELETE /mcp` (authenticated session termination); legacy `/sse` requests are transparently rewritten to `/mcp`
- **Session Header**: `mcp-session-id` (with automatic session recovery if a stale session ID is sent after a restart)
- **Authentication**: OAuth 2.0 / 2.1 with PKCE (`S256`) and RFC 8414 / RFC 9728 metadata discovery

## Reading Your Credentials

By default, `config/config.yaml` sets `auth.client_id: "local-mcp"` and generates a random `Client Secret` saved in `data/client_secret.key`. Both values are shown in:
- The startup terminal banner
- The **OAuth Credentials** box in the Web Dashboard sidebar (use `Show` / `Copy`)

## Provider Setup

### 1. Google Gemini (Custom Apps / Connectors)
1. Ensure Tailscale is signed in with MagicDNS and Funnel enabled so `https://<your-funnel-domain>/mcp` is reachable.
2. Create a Custom App or MCP Connector in Gemini / Google AI Studio:
   - **MCP Server URL**: `https://<your-funnel-domain>/mcp`
   - **Authentication**: OAuth 2.0
   - **Client ID**: `local-mcp` (or your configured value)
   - **Client Secret**: Copied from the Web Dashboard
   - **Authorization Endpoint**: `https://<your-funnel-domain>/oauth/authorize`
   - **Token Endpoint**: `https://<your-funnel-domain>/oauth/token`
3. Complete the auto-redirecting authorization screen. The **Google Gemini** card in the dashboard will display active usage counts and remaining Session TTL.

### 2. Anthropic Claude
1. Add a Custom MCP Connector pointing to `https://<your-funnel-domain>/mcp`.
2. Claude discovers OAuth endpoints automatically via `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server`.
3. Authorize via your browser; activity will appear under the **Claude AI** card.

### 3. OpenAI ChatGPT
1. Register a remote MCP connector using `https://<your-funnel-domain>/mcp` and complete the OAuth 2.1 + PKCE authorization flow.
2. Tool calls carrying OpenAI `_meta` metadata are automatically identified and tracked under the **ChatGPT** card.

## Built-in MCP Tools Exposed to AI Clients

Once connected, AI clients can invoke the following sandboxed tools (subject to your **Access Control** toggles in the dashboard):
- **Workspace Files**: `list_workspace_files`, `read_workspace_file`, `write_workspace_file`, `patch_workspace_file`
- **Terminal**: `run_command` (auto-backgrounds long tasks after `session.terminal_timeout`), `check_task_status`, `kill_task`
- **Vision & Windows**: `read_workspace_image`, `list_active_windows`, `switch_active_window`, `capture_window_screenshot`, `take_desktop_screenshot`
- **External Bridged Tools**: Any external MCP server added via the **MCP Client Hub** is exposed as `<owner>_<repo>__<tool_name>`.
