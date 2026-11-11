# Tools Package (`src/ai_mcp_gateway/tools/`)

Sandboxed local capabilities exposed to AI clients through `src/ai_mcp_gateway/core/mcp_server.py`.

## Contents

- `filesystem.py`: Sandboxed directory listing, UTF-8 reading, writing, and single-block patching
  enforced by `safe_path()` (prevents traversal, symlink/junction escapes, and access to gateway
  `data/` secrets or `.env` files).
- `terminal.py`: Asynchronous subprocess execution (`execute_bash`) inside `state.workspace_dir`
  with automatic background transition after `session.terminal_timeout`, plus `check_task_status`
  and `kill_task`.
- `vision.py`: Workspace image reading (`read_image_bytes`), Windows desktop/window enumeration and
  switching, and cropped window or full-desktop JPEG capture (`mss` + `Pillow`).
