# Project Delivery Roadmap

## Completed: v1.0.0 Public Launch & Windows Binary Release

- Modularized ASGI routes, built-in MCP tools, and external MCP client bridging.
- Shipped Windows `onedir` binary bundles (`ai-mcp-gateway-windows-x64.zip`) via automated GitHub
  Releases.
- Enforced hermetic tests, 9-section Python module structure, and Conventional Commits.

## Completed: v1.1.0 Security Hardening & Startup UX

- Hardened OAuth 2.1 consent (`POST /oauth/authorize` requiring `CLIENT_SECRET`), closed `/oauth/token`
  empty PKCE/secret bypass, rejected `?token=` query-parameter auth, and masked console secrets.
- Blocked gateway `data/` (`gateway.db`, `client_secret.key`, `gateway.lock`) and `.env` secrets in
  `safe_path()`.
- Added startup Workspace Selection modal in `/ui` and OS-enforced `SingleInstanceLock`
  (`data/gateway.lock`).
- Integrated `gitleaks` (`v8.30.1`) into `.pre-commit-config.yaml` and `.github/workflows/ci.yml`, plus
  added directory-level `README.md` guides across all packages.

## Upcoming Milestone: v1.2.0 Cross-Platform & Runtime Enhancements

- Cross-platform standalone binaries for Linux and macOS (`#2`).
- Dedicated frozen-runtime unit test coverage in `tests/unit/test_config.py` (`#3`).
- Optional desktop system tray launcher and runtime configuration editor in Web Dashboard.
