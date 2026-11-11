# Integration Tests (`tests/integration/`)

End-to-end HTTP and middleware tests using a shared FastAPI `TestClient` lifespan.

## Contents

- `base.py`: `BaseIntegrationTestCase` managing the shared `TestClient(app)` instance.
- `test_dashboard_api.py`: `/ui`, `/api/ui/state`, workspace confirmation flow, user permission
  toggles, developer traffic endpoints, and cross-origin / `X-Forwarded-For` `403` guards.
- `test_mcp_client_and_bans.py`: External MCP Server hub endpoints and manual IP ban/unban APIs.
- `test_mcp_handshake.py`: JSON-RPC `initialize` / `tools/call` AI client detection, `DELETE /mcp`
  auth enforcement, and rejection of `?token=` query-parameter auth.
- `test_oauth_flow.py`: RFC 8414/9728 metadata discovery, manual `POST /oauth/authorize` consent
  with `CLIENT_SECRET`, PKCE `S256` verification, and rejection of unauthenticated token exchange.
