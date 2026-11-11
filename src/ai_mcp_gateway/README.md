# `ai_mcp_gateway` Package (`src/ai_mcp_gateway/`)

Core Python package for AI Agent MCP Gateway.

## Top-Level Modules & Subpackages

- `cli.py`: Registered console script entry point (`ai-mcp-gateway`) with
  `multiprocessing.freeze_support()`.
- `__main__.py`: Module execution entry point (`python -m ai_mcp_gateway`).
- `main.py`: FastAPI composition root, lifespan manager, MCP Streamable HTTP mount (`/mcp`),
  single-instance lock acquisition, and Uvicorn launcher.
- [`core/`](core/README.md): Auth/OAuth, SQLite database, runtime state, single-instance lock, MCP
  server & aggregator client manager, and Tailscale Funnel automation.
- [`interfaces/`](interfaces/README.md): Inbound HTTP routes, ASGI security middleware pipeline, and
  Web Dashboard frontend.
- [`model/`](model/README.md): Pydantic configuration validation schemas.
- [`tools/`](tools/README.md): Sandboxed filesystem, terminal execution, and desktop/window vision
  tools.
- [`utils/`](utils/README.md): Configuration discovery, path resolution, and secret management
  helpers.
