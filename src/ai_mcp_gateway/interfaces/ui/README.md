# Web Dashboard UI (`src/ai_mcp_gateway/interfaces/ui/`)

Frontend assets for the localhost-restricted Control Dashboard (`/ui`).

## Contents

- `index.html`: Single-page Alpine.js + Tailwind CSS + Lucide Icons dashboard providing:
  - Startup **Select Workspace** onboarding modal (`showWorkspaceModal`)
  - Real-time AI provider telemetry cards and Session TTL tracking
  - HITL Pending Approvals Queue, Activity Log, and Developer HTTP Inspector
  - External MCP Client Hub (GitHub stdio server install/start/stop/uninstall)
  - Security Shield & Banned IPs management table

## Packaging Note

Bundled into frozen builds by `packaging/build.py` and resolved at runtime via `get_ui_index_file()`
in `src/ai_mcp_gateway/utils/config.py`.
