# Contributing to AI Agent MCP Gateway

Thank you for your interest in contributing to `ai-mcp-gateway`. This guide explains how to set up a clean local environment, follow project standards, and submit pull requests.

## Prerequisites

- Python `3.14+`
- [`uv`](https://docs.astral.sh/uv/) package manager
- Git

## Development Setup

```bash
git clone https://github.com/SavEe2429/ai-mcp-gateway.git
cd ai-mcp-gateway
uv sync --dev
```

Install Git hooks so formatting, lint rules, and Conventional Commit messages are validated automatically:

```bash
pre-commit install --install-hooks
```

## Running Locally

```bash
# Run via console script entry point
uv run ai-mcp-gateway

# Run tests (hermetic temporary database and workspace)
uv run pytest

# Run linter
uv run ruff check src/ tests/ packaging/ templates/ .github/scripts/release/

# Build standalone Windows bundle (onedir)
uv run python packaging/build.py --mode onedir
```

## Coding Standards

1. **Package Layout**: Keep application code inside `src/ai_mcp_gateway/`, configuration in `config/config.yaml`, and tests in `tests/`. Never place runtime databases, scratch files, or personal workspace files under version control.
2. **9-Section Module Layout**: New and refactored Python modules follow `templates/python/script_template.py`.
3. **Granular Exceptions**: Catch specific exceptions (`OSError`, `ValueError`, `RuntimeError`, `sqlite3.Error`, etc.) rather than broad `except Exception:` blocks inside domain logic.
4. **Line Endings**: Use LF (`\n`) for all source, configuration, and documentation files.
5. **Security**:
   - All workspace file operations must pass through `fs.safe_path()`.
   - Dashboard routes (`/ui`, `/api/ui/*`, `/ws/ui`) must remain restricted to localhost.

## Commit Convention

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<optional-scope>): <concise summary>
```

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

Examples:
- `feat(tools): add configurable timeout for background tasks`
- `fix(auth): validate PKCE code_verifier length`
- `docs(readme): clarify Windows executable setup steps`

## Pull Request Process

1. Open or reference an issue describing the problem or feature.
2. Create a topic branch from `main` (e.g. `feat/my-improvement`).
3. Ensure `ruff`, `pytest`, and `uv lock --check` pass locally.
4. Update `CHANGELOG.md` under `## [Unreleased]` for user-facing changes.
5. Submit a Pull Request using `.github/pull_request_template.md`.
