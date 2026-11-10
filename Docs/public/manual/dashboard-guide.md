# Web Dashboard User Guide

The Web Dashboard (`http://localhost:3000/ui`) is the local control center for `ai-mcp-gateway`. For security, it only accepts connections from localhost (`127.0.0.1`, `::1`, `localhost`) and rejects external Tailscale Funnel or reverse-proxy requests with `403 Forbidden`.

---

## 1. Top Navigation Header

The top bar remains visible across all views and provides global navigation, status monitoring, and privacy controls:

- **Sidebar Toggle Button** (top-left panel icon): Collapses or expands the left control drawer.
- **Connection Status Indicator**: Displays `ONLINE • STREAMABLE HTTP` when the live WebSocket (`/ws/ui`) is connected, or `DISCONNECTED` if the backend stops.
- **Center Mode Switcher** (3 primary views):
  1. **MCP Server**: Live AI usage telemetry, human-in-the-loop approvals, Activity Logs, and Developer Inspector.
  2. **MCP Client Hub**: Displays the number of installed external MCP servers and lets you install or manage GitHub MCP tools.
  3. **Banned IPs**: Displays the active ban count and opens the Security Shield management table.
- **MCP Endpoint Bar** (top-right):
  - **Privacy Masking**: Masks your Tailscale Funnel domain by default (`https://••••••••••••••••/mcp`) so you can share screenshots safely. Click `Show` / `Hide` to reveal or conceal the full URL.
  - **Copy**: Copies the full `mcp_url` directly to the clipboard.
- **Theme Toggle** (sun / moon icon): Switches between Dark Mode and Light Mode and persists your preference in browser `localStorage`.

---

## 2. Left Control Sidebar

### 2.1 Workspace
Controls the sandboxed root directory accessible to AI filesystem and terminal tools (`list_workspace_files`, `read_workspace_file`, `write_workspace_file`, `patch_workspace_file`, `run_command`):
- **Path Input + `Save`**: Type or paste a folder path and press `Enter` or click `Save`. If the folder does not exist, it is created automatically.
- **`Browse`**: Opens a native OS folder-picker dialog on your desktop and updates the active workspace immediately upon selection.
- All file operations are enforced through `safe_path()`, preventing directory traversal (`../`) and symlink/junction escapes outside the selected folder.

### 2.2 Access Control
Displays the active count (`X/5 Active`) and provides instant runtime toggles for all gateway capabilities:
- **`Read Files`** (`allow_read`): Enables or disables listing and reading files inside `workspace/`.
- **`Write & Patch`** (`allow_write`): Enables or disables creating, overwriting, and patching workspace files.
- **`Terminal Commands`** (`allow_bash`): Enables or disables `run_command` shell execution inside the workspace.
- **`Vision & Screenshots`** (`allow_vision`): Enables or disables `read_workspace_image`, `list_active_windows`, `switch_active_window`, `capture_window_screenshot`, and `take_desktop_screenshot`.
- **`HITL Manual Approval`** (`require_approval`): When switched `ON`, every `write_workspace_file`, `patch_workspace_file`, and `run_command` call pauses and waits for your explicit `Approve` or `Deny` click in the Pending Approvals Queue (5-minute timeout).

### 2.3 OAuth Credentials
Displays the credentials required when configuring external AI platforms:
- **`Client ID`**: Copyable OAuth client identifier (default: `local-mcp`).
- **`Client Secret`**: Masked (`••••••••••••••••••••`) by default. Click `Show` / `Hide` to inspect or `Copy` to copy the secret stored in `data/client_secret.key` (or `config/config.yaml` / environment variables).

### 2.4 Shield Protection Quick Card
Shows the number of currently banned IP addresses and includes an **`Open Banned List`** shortcut button to jump straight to the Security Shield view.

---

## 3. View 1: MCP Server Mode

### 3.1 AI Provider Telemetry Cards
Three summary cards track activity and OAuth session health for each major AI provider:
- **Google Gemini** (`Custom MCP Client`)
- **Claude AI** (`Remote Connector`)
- **ChatGPT** (`OpenAI Actions`)

Each card displays:
- **Total Request Counter**: Total logged tool calls attributed to that AI client.
- **Session TTL**: Remaining lifetime of the client's most recent OAuth token (7-day sliding window by default), color-coded by remaining time (green when >= 1 day, amber when < 1 day, red when expired).

### 3.2 Pending Approvals Queue (HITL)
Appears automatically whenever `HITL Manual Approval` is `ON` and an AI client triggers a write, patch, or terminal command:
- Displays the tool name, target file or command preview, and action buttons:
  - **`Approve`**: Allows the paused tool call to execute immediately.
  - **`Deny`**: Rejects the request and returns a denial message to the AI client, recording a `DENIED` audit entry.

### 3.3 Activity Log Tab
Shows persistent SQLite audit entries (`logs.length`) in real time:
- Status badge (`SUCCESS`, `ERROR`, `DENIED`)
- Detected AI client badge (`Gemini`, `Claude`, `ChatGPT`, `Cursor`, etc.)
- Tool name, condensed input parameters, timestamp, and scrollable tool output
- **`Clear Logs`**: Clears stored audit logs and resets AI usage counters across connected dashboard tabs.

### 3.4 Developer Inspector Tab
Displays live HTTP traffic hitting `/mcp` and `/oauth` endpoints (`devTraffic.length`, up to 100 recent entries in memory):
- Detected client name
- HTTP method (`POST`, `GET`, `DELETE`) and request path
- Round-trip latency in milliseconds (`ms`)
- HTTP status code (color-coded green for `< 400`, rose for `>= 400`)

---

## 4. View 2: MCP Client Hub

Use this view to turn `ai-mcp-gateway` into an **MCP Aggregator** by installing external stdio MCP servers directly from GitHub and exposing their tools to your connected AI clients.

### 4.1 Install a New MCP Server from GitHub
1. **GitHub URL**: Paste either a repository root URL (e.g. `https://github.com/owner/repo`) or a subdirectory URL (`/tree/main/src/...`).
2. **Environment (Optional)**: Enter comma-separated environment variables such as `API_KEY=xyz, PORT=8080`.
3. **Custom Command / Args (Optional Collapsible)**: Expand if the target repository uses a non-standard startup command (specify `Command` such as `uv`, `node`, or `python` and `Arguments` such as `run python src/server.py`).
4. Click **`Install & Connect`**:
   - Clones the repository under `data/mcp_servers/`.
   - Auto-detects Node.js (`package.json`, runs `npm install`, resolves `bin`/`main`) or Python (`pyproject.toml`, `requirements.txt`, or `*.py` executed via `uv run`).
   - Connects over stdio, discovers available tools, and bridges them into the gateway under `<owner>_<repo>__<tool_name>`.

### 4.2 Installed External MCP Servers List
- **`Refresh Status`**: Reloads current runtime status and discovered tool lists.
- Each installed server card displays:
  - Repository name, detected runtime (`PYTHON` / `NODE`), and source URL.
  - Live status badge (`RUNNING` or `STOPPED`).
  - **Bridged Tools**: Scrollable list of exposed tool names (hover to view each tool's description).
  - **`Start` / `Stop`**: Starts or stops the stdio subprocess and registers/unregisters its tools dynamically.
  - **`Uninstall`**: Stops the server, removes bridged tools, deletes its cloned files, and removes its database record.

---

## 5. View 3: Security Shield & Banned IPs

Protects your machine when the gateway is exposed over Tailscale Funnel:

- **Automatic Scanner Shield**: Any request probing common vulnerability paths or extensions (`.php`, `.env`, `.bak`, `/wp-`, `/wordpress`, `/vendor`, `/token.json`, etc., configurable in `config/config.yaml`) receives `404 Not Found` and triggers an automatic temporary IP ban (default: 1 hour; subsequent hits return `403 Forbidden` and increment `Hits`). Localhost addresses are never banned.
- **Manual IP Ban**: Enter an IP address in the input bar and click **`Ban IP`** (or press `Enter`) to block it immediately.
- **Banned IPs Table**: Lists each blocked `IP Address`, ban reason and `target_path`, total `Hits`, ban timestamp + minutes remaining, **`Unban`** button for a single IP, and **`Clear All Bans`** to reset the blacklist.
