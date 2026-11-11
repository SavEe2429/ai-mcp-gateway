# Configuration Directory (`config/`)

Single Source of Truth (SSOT) runtime configuration for `ai-mcp-gateway`.

## Contents

- `config.yaml`: Central YAML configuration file validated at startup by Pydantic models in
  `src/ai_mcp_gateway/model/config.py` and loaded via `src/ai_mcp_gateway/utils/config.py`.

## Key Sections in `config.yaml`

- `session`: OAuth token/code TTLs, IP ban duration, developer traffic buffer size, terminal
  background timeout, and audit log limits.
- `server`: Host, port, MCP/UI paths, server metadata, Tailscale Funnel toggle, and CORS origins.
- `storage`: Paths for `data_dir`, `db_path`, `client_secret_file`, and `workspace_dir`.
- `auth`: Default `client_id`, optional `client_secret`, and allowed OAuth redirect hosts/domains.
- `security`: Localhost allowlist, scanner detection extensions/prefixes, and silenced polling log
  prefixes.

## Bundling & Overrides

In frozen PyInstaller builds (`packaging/build.py`), this directory is bundled read-only, and users
can place an external `config/config.yaml` beside the executable (or set `GATEWAY_CONFIG_PATH`) to
override defaults without rebuilding.
