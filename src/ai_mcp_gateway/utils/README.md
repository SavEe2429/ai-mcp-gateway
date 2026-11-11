# Utilities Package (`src/ai_mcp_gateway/utils/`)

Shared configuration loading, path resolution, and secret management utilities.

## Contents

- `config.py`: Locates and caches validated `GatewayConfig`, distinguishes frozen PyInstaller bundle
  paths (`_MEIPASS`) from writable runtime directories, resolves `data/` / `workspace/` /
  `gateway.db` / `client_secret.key` / `gateway.lock` (supporting environment variable overrides),
  and loads or generates `CLIENT_SECRET`.
