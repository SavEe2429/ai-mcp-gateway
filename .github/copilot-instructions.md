# AI Assistant & GitHub Copilot Operational Instructions

This document instructs AI assistants, GitHub Copilot, and automated agents working on the ai-mcp-gateway repository.

## 1. Project Purpose & Architecture

- Repository Name: `ai-mcp-gateway`
- Language & Runtime: Python 3.14+ (pinned in `.python-version` and `pyproject.toml`)
- Frameworks: FastAPI + Model Context Protocol (MCP) Streamable HTTP SDK
- Architecture: Standard `src/` layout (`src/ai_mcp_gateway`) with clean presentation adapters and encapsulated entry points.

## 2. Mandatory Architectural Boundaries

1. Clean Root Policy: Never place executable scripts, loose test files, or UI asset directories in the repository root. All application code belongs in `src/ai_mcp_gateway/`.
2. Encapsulated Entry Points: Console entry points reside at `cli.py`, module entry point at `__main__.py`, and ASGI app at `main.py`.
3. Presentation Interfaces: Web frontend assets reside in `src/ai_mcp_gateway/interfaces/ui/` and inbound ASGI middleware resides in `src/ai_mcp_gateway/interfaces/middleware/`.
4. Runtime State & Database Isolation: The SQLite database belongs strictly in `data/gateway.db`. Never write `*.db` files to the project root. `data/` is excluded from version control in `.gitignore`.
5. Filesystem Workspace Isolation: File operations executed by MCP tools must validate paths through `fs.safe_path()` to prevent traversal outside `workspace/`.
6. Native Package-Manager Runner: Always run commands through the `uv` native runner: `uv run <command>`. Never reference virtual environment paths directly (such as `.venv/Scripts/python.exe`).

## 3. Code Standards & Patterns

- 9-Section Source Template: When authoring new Python modules, follow the standardized 9-section structure outlined in `templates/python/script_template.py`.
- Strict LF Line Endings: All source code, configs, and documentation must use LF (`\n`). CRLF is rejected.
- Granular Exception Handling: Avoid blind catch-all `except Exception:` in domain subroutines. Catch specific errors (`OSError`, `ValueError`, `KeyError`) and reserve outer catch-all handlers exclusively for top-level ASGI middleware or CLI wrappers.
- No Emojis in Documentation: Technical markdown documentation, commits, and logs must be formal and maintain zero emojis.

## 4. Verification & Testing

Always verify modifications before completion:
- Linter: `uv run ruff check src/ tests/`
- Unit & Integration Tests: `uv run pytest`
- Package Build: `uv build`
- Append-Only Logbook: Document non-trivial changes in `logbook/current.md`.
