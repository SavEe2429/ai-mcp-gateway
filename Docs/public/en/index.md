# AI Agent MCP Gateway — English Documentation

> Language: **English** | [ภาษาไทย](../th/index.md)

Welcome to the user documentation for `ai-mcp-gateway` (`v1.0.0`), a local MCP Streamable HTTP bridge exposing sandboxed workspace tools, terminal commands, screen/window capture, and bridged stdio MCP servers to remote AI assistants over HTTPS (Tailscale Funnel) and OAuth 2.1 + PKCE.

## User Guides

- [Quick Start & Installation](manual/quick-start.md): Install from the Windows `.exe` release or run from Python source via `uv`, configure `config/config.yaml`, and verify startup.
- [Tailscale Funnel Setup & Architecture](manual/tailscale-setup.md): Learn how `ai-mcp-gateway` automates Tailscale Funnel, what Tailnet settings are required (MagicDNS, HTTPS, Funnel ACL), and how `/ui` stays isolated from external traffic.
- [Web Dashboard User Guide](manual/dashboard-guide.md): Complete walkthrough of the localhost control center (`http://localhost:3000/ui`), HITL approvals, Developer Inspector, MCP Client Hub, and Security Shield.
- [MCP Integration Guide](manual/mcp-integration.md): Step-by-step instructions for connecting Google Gemini, Anthropic Claude, OpenAI ChatGPT, and Cursor using OAuth 2.1 + PKCE.

## Additional Links

- [Release Notes Index](../release-notes/README.md)
- [Internal Engineering Documentation](../../internal/design/system-architecture.md)
