# Test Suite (`tests/`)

Automated unit and integration tests for `ai-mcp-gateway`.

## Structure

- `__init__.py`: Configures hermetic temporary storage paths (`GATEWAY_DATA_DIR`, `GATEWAY_DB_PATH`,
  `GATEWAY_WORKSPACE_DIR`, `GATEWAY_CLIENT_SECRET_FILE`) so tests never mutate live `data/` or
  `workspace/` files.
- [`unit/`](unit/README.md): Isolated unit tests for config, SQLite database, filesystem sandbox,
  single-instance lock, logging filter, terminal execution, vision tools, and package exports.
- [`integration/`](integration/README.md): FastAPI `TestClient` integration tests covering OAuth
  2.1, MCP handshakes, Dashboard APIs, localhost guards, external MCP client management, and IP
  bans.

## Running Tests

```bash
uv run pytest
uv run python -m unittest discover tests
```
