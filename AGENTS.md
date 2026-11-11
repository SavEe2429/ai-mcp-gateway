# AI Agent Operational Runbook

Welcome to the AI Agent MCP Gateway repository. This runbook instructs autonomous AI agents and
human contributors on how to build, test, operate, and maintain this codebase.

## Repository Overview

- Repository Name: `ai-mcp-gateway`
- Language: Python 3.14+
- Framework: FastAPI + MCP Python SDK (Streamable HTTP)
- Architecture: Standard `src/` layout (`src/ai_mcp_gateway`) with encapsulated entry points and
  interfaces

## Project Structure

- `config/`: Single Source of Truth (SSOT) configuration directory at repository root containing
  `config.yaml`.
- `src/ai_mcp_gateway/`: Core application package.
  - `cli.py`: Console command-line entrypoint (`[project.scripts]`).
  - `__main__.py`: Package module entrypoint (`python -m ai_mcp_gateway`).
  - `main.py`: FastAPI server and MCP Streamable HTTP mounting.
  - `model/`: Pydantic data models for configuration validation (`config.py`).
  - `utils/`: Utilities package containing `config.py` (dedicated loader reading and validating
    `config/config.yaml`).
  - `interfaces/`: Inbound HTTP interfaces and presentation adapters.
    - `middleware/`: Modular middleware package:
      - `logging_filter.py`: Uvicorn access log filters and scanner noise suppression.
      - `identity.py`: Multi-AI client recognition and context propagation.
      - `shield.py`: Malicious scanner detection, auto IP blacklisting, and localhost guards.
      - `security.py`: ASGI security pipeline and session recovery.
    - `ui/`: Web dashboard frontend (`index.html`) using Alpine.js and Tailwind CSS.
    - `ui_routes.py`: FastAPI routes and WebSocket endpoints for Web Dashboard state, approvals, and files.
  - `core/auth.py`: OAuth 2.0 / 2.1 RFC 8414 metadata, token issuance, and PKCE.
  - `core/database.py`: SQLite audit logging, AI provider usage counters, and session tracking.
  - `core/instance_lock.py`: Single-instance lock file (`data/gateway.lock`) preventing concurrent gateway runs.
  - `core/mcp_client_manager.py`: External MCP client manager bridging stdio MCP servers (uv/npm).
  - `core/mcp_server.py`: Low-level MCP Server protocol setup, tool declarations, and lifecycle.
  - `core/state.py`: Runtime configuration, approval workflow, and WebSocket broadcaster.
  - `core/tunnel.py`: Tailscale Funnel automation for secure external access.
  - `tools/`: MCP tool implementations (`filesystem.py`, `terminal.py`, `vision.py`).
- `packaging/`: Binary executable build scripts (`build.py`) targeting `out/ai-mcp-gateway/`.
- `tests/`: Automated test suite partitioned into `tests/unit/` and `tests/integration/`.
- `workspace/`: Sandboxed filesystem workspace for AI tools.
- `logbook/`: Append-only engineering logbook. See `logbook/README.md`.

## Key Commands

All commands use `uv` directly for cross-platform isolation and environment consistency:

### Environment Setup

```bash
uv sync --dev
```

### Running the Gateway

```bash
# Via console script entry point
uv run ai-mcp-gateway

# Or via package module execution
uv run python -m ai_mcp_gateway
```

### Running Tests

```bash
# Using pytest runner
uv run pytest

# Or using Python standard unittest runner
uv run python -m unittest discover tests
```

### Binary Packaging (PyInstaller)

```bash
# Build as directory bundle (onedir - recommended)
uv run python packaging/build.py --mode onedir

# Build as single standalone executable (onefile)
uv run python packaging/build.py --mode onefile
```

### Linting and Formatting

```bash
uv run ruff check src/ tests/ packaging/ templates/ .github/scripts/release/
```

## Security and Sandboxing Rules

1. Workspace Isolation: All filesystem operations must resolve through `fs.safe_path()` to prevent
   directory traversal outside `workspace/`.
2. Dashboard Access Restriction: Dashboard routes (`/ui`, `/api/ui`) are locked to localhost
   (`127.0.0.1`, `::1`). External access over Tailscale Funnel is rejected with 403 Forbidden.
3. Streamable HTTP Protocol: External AI clients (Google Gemini, Claude, ChatGPT) interact via
   `POST /mcp` authenticated with Bearer tokens.
