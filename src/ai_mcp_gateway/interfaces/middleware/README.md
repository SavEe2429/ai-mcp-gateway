# Middleware Package (`src/ai_mcp_gateway/interfaces/middleware/`)

Modular HTTP security, client identification, and log-filtering middleware components.

## Contents

- `security.py`: Primary ASGI middleware (`create_security_middleware`) coordinating shield guards,
  `/sse` -> `/mcp` rewrite, stale session recovery, Bearer header validation, identity resolution,
  and developer traffic capture.
- `shield.py`: IP blacklist checks, automated malicious path/extension scanner banning, and strict
  localhost/same-origin guard for `/ui` and `/api/ui`.
- `identity.py`: Multi-provider AI client recognition (`Claude`, `ChatGPT`, `Gemini`, `Cursor`) from
  JSON-RPC payloads and HTTP headers via `ContextVar`.
- `logging_filter.py`: Uvicorn access log filter (`PollingAccessLogFilter`) suppressing noisy
  dashboard polling endpoints.
