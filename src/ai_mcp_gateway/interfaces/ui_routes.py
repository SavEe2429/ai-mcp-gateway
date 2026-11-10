"""Localhost-restricted Web Dashboard and Management API router."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import asyncio
import os
import sqlite3
from typing import Any, Dict

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from mcp import MCPError

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
import ai_mcp_gateway.tools.filesystem as fs
from ai_mcp_gateway.core.database import (
    clear_logs,
    get_active_client_connections,
    get_ai_usage_stats,
    get_all_external_mcps,
    get_recent_logs,
)
from ai_mcp_gateway.core.mcp_client_manager import client_manager
from ai_mcp_gateway.core.state import state
from ai_mcp_gateway.utils.config import (
    CLIENT_ID,
    CLIENT_SECRET,
    get_config,
    get_ui_index_file,
)

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
LOCAL_WS_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
ui_router: APIRouter = APIRouter()

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
@ui_router.get("/")
async def root_redirect() -> RedirectResponse:
    """Redirect root requests to the local Web Dashboard."""
    return RedirectResponse(url="/ui")


@ui_router.get("/ui")
async def serve_dashboard() -> FileResponse:
    """Serve the single-page Web Dashboard HTML interface."""
    return FileResponse(get_ui_index_file())


@ui_router.get("/api/ui/state")
async def get_ui_state() -> Dict[str, Any]:
    """Return current gateway state, recent audit logs, AI usage stats, and clients."""
    cfg = get_config()
    return {
        "state": state.to_dict(CLIENT_ID, CLIENT_SECRET),
        "logs": get_recent_logs(cfg.session.audit_log_limit),
        "ai_usage": get_ai_usage_stats(),
        "client_connections": get_active_client_connections(),
    }


@ui_router.post("/api/ui/logs/clear")
async def clear_logs_endpoint() -> Dict[str, Any]:
    """Clear stored activity logs and notify connected dashboard clients."""
    clear_logs()
    ai_usage = get_ai_usage_stats()
    await state.broadcast("logs_cleared", {"ai_usage": ai_usage})
    print("[User Action] Activity logs cleared")
    return {"status": "ok", "success": True, "ai_usage": ai_usage}


@ui_router.get("/api/ui/dev/traffic")
async def get_dev_traffic() -> Dict[str, Any]:
    """Return in-memory developer traffic logs and active MCP sessions."""
    return {
        "traffic": state.dev_traffic_logs,
        "sessions": list(state.active_sessions.values()),
    }


@ui_router.post("/api/ui/dev/clear")
async def clear_dev_traffic_endpoint() -> Dict[str, Any]:
    """Clear the developer traffic inspector buffer."""
    state.clear_dev_traffic()
    await state.broadcast("dev_traffic_cleared", {})
    print("[User Action] Developer traffic logs cleared")
    return {"status": "ok", "success": True}


@ui_router.get("/api/ui/files")
async def get_workspace_files() -> Dict[str, Any]:
    """List files inside the active workspace directory."""
    try:
        raw = fs.list_files("")
        files = (
            []
            if raw in ("โฟลเดอร์ว่างเปล่า", "ไม่พบไฟล์") or raw.startswith("Error:")
            else raw.splitlines()
        )
        return {"files": files}
    except OSError, ValueError:
        return {"files": []}


@ui_router.post("/api/ui/workspace")
async def update_workspace(payload: Dict[str, Any]) -> Dict[str, str]:
    """Update the active workspace directory path."""
    new_path = str(payload.get("path", "")).strip()
    if new_path:
        state.set_workspace(new_path)
        await state.broadcast("state_updated", state.to_dict(CLIENT_ID, CLIENT_SECRET))
        print(f"[User Action] Workspace changed to: {state.workspace_dir}")
    return {"workspace_dir": state.workspace_dir}


@ui_router.post("/api/ui/browse")
async def browse_folder_dialog() -> Dict[str, Any]:
    """Open a native OS folder picker dialog for selecting the workspace directory."""
    selected_path = await asyncio.to_thread(_open_folder_picker_dialog)
    if selected_path:
        norm_path = os.path.normpath(selected_path)
        state.set_workspace(norm_path)
        await state.broadcast("state_updated", state.to_dict(CLIENT_ID, CLIENT_SECRET))
        print(f"[User Action] Workspace browsed and selected: {state.workspace_dir}")
        return {"path": state.workspace_dir}
    return {"path": None}


@ui_router.post("/api/ui/permissions")
async def update_permissions(payload: Dict[str, Any]) -> Dict[str, str]:
    """Update runtime tool permissions and approval requirement toggles."""
    changed = []
    for key in ("allow_read", "allow_write", "allow_bash", "allow_vision", "require_approval"):
        if key in payload:
            val = bool(payload[key])
            if getattr(state, key, None) != val:
                setattr(state, key, val)
                changed.append(f"{key}={val}")

    await state.broadcast("state_updated", state.to_dict(CLIENT_ID, CLIENT_SECRET))
    if changed:
        print(f"[User Action] Permissions updated: {', '.join(changed)}")
    return {"status": "ok"}


@ui_router.get("/api/ui/security/bans")
async def get_banned_ips() -> Dict[str, Any]:
    """List currently banned IP addresses."""
    return {"bans": state.get_banned_ips_list()}


@ui_router.post("/api/ui/security/ban")
async def manual_ban_ip(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Manually ban an IP address for a given duration in seconds."""
    ip = str(payload.get("ip", "")).strip()
    reason = str(payload.get("reason", "Manual Ban by User")).strip()
    duration = int(payload.get("duration", 3600))
    if ip:
        state.block_ip(ip, duration_seconds=duration, reason=reason, target_path="MANUAL")
        await state.broadcast("ip_banned", {"ip": ip, "reason": reason})
        print(f"[User Action] Manually banned IP: {ip} for {duration}s")
        return {"status": "ok", "bans": state.get_banned_ips_list()}
    return {"status": "error", "message": "Invalid IP"}


@ui_router.post("/api/ui/security/unban")
async def unban_ip_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Remove an IP address from the active blacklist."""
    ip = str(payload.get("ip", "")).strip()
    if ip:
        state.unblock_ip(ip)
        await state.broadcast("ip_unbanned", {"ip": ip})
        print(f"[User Action] Unbanned IP: {ip}")
        return {"status": "ok", "bans": state.get_banned_ips_list()}
    return {"status": "error", "message": "Invalid IP"}


@ui_router.post("/api/ui/security/bans/clear")
async def clear_all_bans_endpoint() -> Dict[str, Any]:
    """Clear all active IP bans."""
    state.clear_all_bans()
    await state.broadcast("bans_cleared", {})
    print("[User Action] Cleared all banned IPs")
    return {"status": "ok", "bans": []}


@ui_router.get("/api/ui/mcp-clients")
async def list_mcp_clients() -> Dict[str, Any]:
    """List installed external MCP servers and their live runtime status."""
    servers = get_all_external_mcps()
    for server in servers:
        inst = client_manager.instances.get(server["id"])
        if inst:
            server["is_running"] = inst.is_running
            server["live_tools"] = inst.tools
    return {"servers": servers}


@ui_router.post("/api/ui/mcp-clients/install")
async def install_mcp_client(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Install and start an external MCP server from a GitHub repository URL."""
    github_url = str(payload.get("url", "")).strip()
    env_vars = payload.get("env_vars", {})
    custom_command = str(payload.get("command", "")).strip()
    custom_args = str(payload.get("args", "")).strip()
    if not github_url:
        return {"status": "error", "message": "Missing GitHub repository URL"}

    try:
        server_info = await client_manager.install_from_github(
            github_url,
            env_vars=env_vars,
            custom_command=custom_command,
            custom_args=custom_args,
        )
        await state.broadcast("mcp_clients_updated", {})
        return {"status": "ok", "server": server_info}
    except (ValueError, RuntimeError, OSError, MCPError, sqlite3.Error) as err:
        return {"status": "error", "message": str(err)}


@ui_router.post("/api/ui/mcp-clients/toggle")
async def toggle_mcp_client(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Start or stop a registered external MCP server."""
    server_id = str(payload.get("id", ""))
    enable = bool(payload.get("enable", True))
    try:
        updated = await client_manager.toggle_server(server_id, enable)
        await state.broadcast("mcp_clients_updated", {})
        return {"status": "ok", "server": updated}
    except (ValueError, RuntimeError, OSError, MCPError, sqlite3.Error) as err:
        return {"status": "error", "message": str(err)}


@ui_router.delete("/api/ui/mcp-clients/{server_id}")
async def uninstall_mcp_client(server_id: str) -> Dict[str, Any]:
    """Uninstall and remove an external MCP server."""
    try:
        await client_manager.uninstall(server_id)
        await state.broadcast("mcp_clients_updated", {})
        return {"status": "ok"}
    except (ValueError, RuntimeError, OSError, MCPError, sqlite3.Error) as err:
        return {"status": "error", "message": str(err)}


@ui_router.post("/api/ui/approve")
async def approve_task_endpoint(payload: Dict[str, Any]) -> Dict[str, str]:
    """Resolve a pending human-in-the-loop approval request."""
    task_id = payload.get("task_id")
    approved = bool(payload.get("approved", False))
    state.resolve_approval(task_id, approved)
    decision = "APPROVED" if approved else "DENIED"
    print(f"[User Action] Approval task {task_id[:8] if task_id else ''} -> {decision}")
    return {"status": "resolved"}


@ui_router.websocket("/ws/ui")
async def dashboard_websocket(websocket: WebSocket) -> None:
    """Serve live dashboard updates over localhost-only WebSockets."""
    client_host = websocket.client.host if websocket.client else ""
    if client_host not in LOCAL_WS_HOSTS:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    state.ws_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in state.ws_clients:
            state.ws_clients.remove(websocket)


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
def _open_folder_picker_dialog() -> str:
    """Launch a blocking native Tkinter folder selection dialog."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    selected = filedialog.askdirectory(
        initialdir=state.workspace_dir,
        title="Select Workspace Folder",
    )
    root.destroy()
    return selected


## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Exported via `ui_router` for inclusion in main FastAPI app.
