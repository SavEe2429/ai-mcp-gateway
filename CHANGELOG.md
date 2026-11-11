# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-11-11

### Added

- **Startup Workspace Selection Modal**: Opening the Web Dashboard (`/ui`) on a new gateway session
  now prompts the user with a modal (`showWorkspaceModal`) to browse, enter, or confirm the default
  `./workspace` directory before use (`state.workspace_configured`).
- **Single-Instance OS Lock File**: Added cross-platform `SingleInstanceLock`
  (`src/ai_mcp_gateway/core/instance_lock.py`) using `data/gateway.lock` (`GATEWAY_LOCK_FILE`
  override supported) to prevent two gateway processes from launching simultaneously.

### Security

- **OAuth Consent & Token Hardening**: Removed automatic `auth_code` issuance and `<meta refresh>`
  auto-redirect from `GET /oauth/authorize`; authorization now requires explicit
  `POST /oauth/authorize` consent verified against `CLIENT_SECRET`, and `/oauth/token` requires
  either valid `client_secret` or PKCE verification.
- **Filesystem Secret Protection**: Updated `safe_path()` and `list_files()` to block access to
  gateway data/secret paths (`data/`, `gateway.db`, `client_secret.key`, `gateway.lock`) and `.env`
  files (preserving `.env.example`/`.env.sample`/`.env.template`) even when `workspace_dir` points
  to the repository root.
- **Strict Bearer Header & Console Masking**: Removed `?token=` query-parameter authentication
  fallback in `/mcp` middleware and masked `CLIENT_SECRET` in the startup terminal banner.
- **Pre-Commit & CI Secret Scanning**: Added Gitleaks `v8.30.1` secret detection (`gitleaks-system`
  in `.pre-commit-config.yaml` and SHA-256-verified `gitleaks git` scan in
  `.github/workflows/ci.yml`).

### Documentation

- Added directory-level `README.md` guides across `config/`, `packaging/`, `templates/`,
  `src/ai_mcp_gateway/**`, and `tests/**`.
- Updated `README.md` and bilingual English/Thai manuals (`quick-start.md`, `dashboard-guide.md`,
  `mcp-integration.md`) for startup workspace selection, single-instance locking, and hardened OAuth
  flows.

## [1.0.0] - 2026-11-10

### Added

- MCP Streamable HTTP (`POST /mcp`) server with session recovery, `/sse` compatibility rewrite, and
  OAuth 2.0 / 2.1 (`S256` PKCE, RFC 8414 / RFC 9728 metadata discovery).
- Real-time localhost-locked Web Dashboard (`interfaces/ui/index.html`) with Server telemetry,
  Developer Traffic Inspector, HITL Manual Approval queue, External MCP Client Hub, and Security
  Shield / Banned IPs management.
- Sandboxed workspace filesystem tools (`safe_path` traversal and symlink/junction prevention),
  terminal execution with auto-backgrounding, and desktop/window vision capture tools.
- External MCP Client Manager supporting GitHub repository installation and stdio tool bridging for
  Python (`uv`) and Node.js (`npm`) servers.
- Standalone Windows `.exe` packaging (`packaging/build.py`) with frozen-runtime path separation
  (`_MEIPASS` for read-only assets, executable directory for writable `data/` and `workspace/`).
- Automated CI quality gate and multi-job GitHub Release workflow (`.github/workflows/ci.yml` and
  `.github/workflows/release.yml` building `onedir` Windows bundles), MIT `LICENSE`,
  `CONTRIBUTING.md`, `SECURITY.md`, Issue/PR templates, and dual-tier `Docs/` portal (`mkdocs.yml`).
