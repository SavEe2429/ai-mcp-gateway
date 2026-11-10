# Security Policy

## Security Architecture

`ai-mcp-gateway` exposes local computer capabilities (sandboxed filesystem access, command execution, and desktop screenshots) over MCP Streamable HTTP. Because of this sensitivity, the project enforces strict defaults:

- **Workspace Confinement**: Filesystem operations resolve through `fs.safe_path()` to prevent path traversal and symlink/junction escapes outside `workspace/`.
- **Localhost Dashboard Lock**: Management endpoints (`/ui`, `/api/ui/*`, `/ws/ui`) reject non-localhost clients and cross-origin requests (`403 Forbidden`).
- **OAuth 2.1 + PKCE**: External MCP requests to `POST /mcp` require valid Bearer tokens.
- **Scanner Shield**: Automated vulnerability scanner probes are blocked and temporarily IP-banned.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them privately using one of the following methods:
1. **GitHub Private Vulnerability Reporting** (Security tab -> *Report a vulnerability* on the repository), if enabled.
2. Contact the repository maintainer directly via GitHub (`@SavEe2429`).

Please include:
- A description of the vulnerability and affected component/file
- Clear steps to reproduce or a minimal proof of concept
- Potential security impact and any suggested remediation

We aim to acknowledge reports within 72 hours and coordinate a fix before public disclosure.
