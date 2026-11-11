# Interfaces Package (`src/ai_mcp_gateway/interfaces/`)

Inbound HTTP/WebSocket presentation layer and localhost-locked Web Dashboard.

## Contents

- `ui_routes.py`: Localhost-restricted FastAPI router serving `/ui`, `/api/ui/*` management APIs,
  and `/ws/ui` live WebSocket updates.
- [`middleware/`](middleware/README.md): Modular ASGI security pipeline, IP/scanner shield, AI
  client identity tracking, and polling log filter.
- [`ui/`](ui/README.md): Single-page Web Dashboard HTML/Alpine.js/Tailwind frontend.
