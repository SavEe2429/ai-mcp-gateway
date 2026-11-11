# Security Policy

## Security Architecture

`ai-mcp-gateway` exposes local computer capabilities (sandboxed filesystem access, command
execution, and desktop screenshots) over MCP Streamable HTTP. Because of this sensitivity, the
project enforces strict defaults:

- **Workspace Confinement & Secret Protection**: Filesystem operations resolve through
  `fs.safe_path()` to prevent path traversal, symlink/junction escapes outside `workspace/`, and
  reads of gateway runtime secrets (`data/client_secret.key`, `data/gateway.db`, `data/gateway.lock`)
  or `.env` files.
- **Localhost Dashboard Lock**: Management endpoints (`/ui`, `/api/ui/*`, `/ws/ui`) reject
  non-localhost clients and cross-origin requests (`403 Forbidden`).
- **OAuth 2.1 Consent & Token Enforcement**: `/oauth/authorize` requires manual `CLIENT_SECRET`
  verification (no auto-approve), `/oauth/token` requires valid `client_secret` or PKCE
  verification, `POST /mcp` accepts tokens only via `Authorization: Bearer` headers, and startup
  console output masks `CLIENT_SECRET`.
- **Single-Instance Lock**: `data/gateway.lock` enforces one active gateway process per runtime
  storage directory.
- **Automated Secret Scanning**: Gitleaks (`v8.30.1`) runs in `.pre-commit-config.yaml`
  (`gitleaks-system`) and `.github/workflows/ci.yml` to block committed credentials.
- **Scanner Shield**: Automated vulnerability scanner probes are blocked and temporarily IP-banned.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them privately using one of the following methods:

1. **GitHub Private Vulnerability Reporting** (Security tab -> _Report a vulnerability_ on the
   repository), if enabled.
2. Contact the repository maintainer directly via GitHub (`@SavEe2429`).

Please include:

- A description of the vulnerability and affected component/file
- Clear steps to reproduce or a minimal proof of concept
- Potential security impact and any suggested remediation

We aim to acknowledge reports within 72 hours and coordinate a fix before public disclosure.
