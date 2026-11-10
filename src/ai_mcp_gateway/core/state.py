"""Shared runtime gateway state, approval workflow, IP blacklist, and WebSockets."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import asyncio
import logging
import os
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.utils.config import get_config, get_workspace_dir

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
LOGGER: logging.Logger = logging.getLogger(__name__)

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.


## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
class AppState:
    """In-memory runtime state synchronized across middleware, MCP tools, and UI."""

    def __init__(self) -> None:
        self.workspace_dir: str = os.path.abspath(get_workspace_dir())
        os.makedirs(self.workspace_dir, exist_ok=True)

        cfg = get_config()
        self.public_url: str = f"http://localhost:{cfg.server.port}"
        self.mcp_url: str = f"http://localhost:{cfg.server.port}/mcp"

        self.allow_read: bool = True
        self.allow_write: bool = True
        self.allow_bash: bool = True
        self.allow_vision: bool = True
        self.require_approval: bool = False

        self.pending_tasks: Dict[str, Dict[str, Any]] = {}
        self.ws_clients: List[WebSocket] = []
        self.session_ai_clients: Dict[str, str] = {}
        self.last_active_ai: str = "Gemini"
        self.dev_traffic_logs: List[Dict[str, Any]] = []
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.blocked_ips: Dict[str, float] = {}
        self.banned_details: Dict[str, Dict[str, Any]] = {}

    def block_ip(
        self,
        ip: str,
        duration_seconds: Optional[int] = None,
        reason: str = "Malicious Scanner",
        target_path: str = "",
    ) -> None:
        """Temporarily blacklist a non-local IP address and persist it to SQLite."""
        cfg = get_config()
        if duration_seconds is None:
            duration_seconds = cfg.session.ip_ban_duration
        if ip and ip not in cfg.security.allowed_local_hosts:
            expires_at = time.time() + duration_seconds
            self.blocked_ips[ip] = expires_at
            if ip in self.banned_details:
                self.banned_details[ip]["hit_count"] += 1
                self.banned_details[ip]["expires_at"] = expires_at
                self.banned_details[ip]["target_path"] = target_path
            else:
                self.banned_details[ip] = {
                    "ip": ip,
                    "reason": reason,
                    "target_path": target_path,
                    "banned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "expires_at": expires_at,
                    "hit_count": 1,
                }
            try:
                from ai_mcp_gateway.core.database import add_or_update_ban

                add_or_update_ban(
                    ip, reason=reason, target_path=target_path, duration_seconds=duration_seconds
                )
            except sqlite3.Error as err:
                LOGGER.debug("Failed to persist IP ban: %s", err)

    def unblock_ip(self, ip: str) -> None:
        """Remove an IP address from the runtime and database blacklists."""
        self.blocked_ips.pop(ip, None)
        self.banned_details.pop(ip, None)
        try:
            from ai_mcp_gateway.core.database import remove_ban

            remove_ban(ip)
        except sqlite3.Error as err:
            LOGGER.debug("Failed to remove IP ban: %s", err)

    def clear_all_bans(self) -> None:
        """Clear all active IP bans from memory and database."""
        self.blocked_ips.clear()
        self.banned_details.clear()
        try:
            from ai_mcp_gateway.core.database import clear_all_bans

            clear_all_bans()
        except sqlite3.Error as err:
            LOGGER.debug("Failed to clear IP bans: %s", err)

    def get_banned_ips_list(self) -> List[Dict[str, Any]]:
        """Return active banned IP records sorted by most recent ban time."""
        now = time.time()
        result = []
        for ip, detail in list(self.banned_details.items()):
            remaining = max(0, int(detail["expires_at"] - now))
            if remaining == 0 and detail["expires_at"] > 0:
                self.blocked_ips.pop(ip, None)
                self.banned_details.pop(ip, None)
                continue
            item = dict(detail)
            item["remaining_seconds"] = remaining
            result.append(item)
        return sorted(result, key=lambda x: x["banned_at"], reverse=True)

    def is_ip_blocked(self, ip: str) -> bool:
        """Return True if the given IP is currently banned."""
        cfg = get_config()
        if not ip or ip in cfg.security.allowed_local_hosts:
            return False
        now = time.time()
        expire = self.blocked_ips.get(ip)
        if expire:
            if now < expire:
                if ip in self.banned_details:
                    self.banned_details[ip]["hit_count"] += 1
                return True
            self.blocked_ips.pop(ip, None)
            self.banned_details.pop(ip, None)
        return False

    def add_dev_traffic(self, traffic_item: Dict[str, Any]) -> None:
        """Prepend an item to the bounded in-memory developer traffic buffer."""
        cfg = get_config()
        self.dev_traffic_logs.insert(0, traffic_item)
        if len(self.dev_traffic_logs) > cfg.session.dev_traffic_max_items:
            self.dev_traffic_logs = self.dev_traffic_logs[: cfg.session.dev_traffic_max_items]

    def clear_dev_traffic(self) -> None:
        """Clear the in-memory developer traffic buffer."""
        self.dev_traffic_logs.clear()

    def register_client(
        self, identifier: str, client_name: str, source: str = "Unknown", host: str = ""
    ) -> None:
        """Associate a session ID or client IP with a detected AI client provider."""
        if identifier:
            self.session_ai_clients[identifier] = client_name
            self.active_sessions[identifier] = {
                "id": identifier,
                "client_name": client_name,
                "source": source,
                "host": host,
                "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        self.last_active_ai = client_name

    def get_client(self, identifier: Optional[str] = None) -> str:
        """Look up the client provider name by session/IP identifier."""
        if identifier and identifier in self.session_ai_clients:
            return self.session_ai_clients[identifier]
        return self.last_active_ai or "AI Agent"

    def set_workspace(self, path: str) -> str:
        """Update and ensure the active sandboxed workspace directory exists."""
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            os.makedirs(abs_path, exist_ok=True)
        self.workspace_dir = abs_path
        return self.workspace_dir

    def to_dict(self, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Serialize runtime state for the dashboard state endpoint."""
        return {
            "workspace_dir": self.workspace_dir,
            "public_url": self.public_url,
            "mcp_url": getattr(self, "mcp_url", f"{self.public_url}/mcp"),
            "client_id": client_id,
            "client_secret": client_secret,
            "last_active_ai": self.last_active_ai,
            "permissions": {
                "allow_read": self.allow_read,
                "allow_write": self.allow_write,
                "allow_bash": self.allow_bash,
                "allow_vision": self.allow_vision,
                "require_approval": self.require_approval,
            },
            "pending_approvals": [v["info"] for v in self.pending_tasks.values()],
        }

    async def broadcast(self, event_type: str, data: Any) -> None:
        """Broadcast a real-time JSON event to all connected WebSocket dashboard tabs."""
        dead_clients = []
        payload = {"type": event_type, "data": data}
        for ws in self.ws_clients:
            try:
                await ws.send_json(payload)
            except WebSocketDisconnect, RuntimeError, OSError:
                dead_clients.append(ws)
        for ws in dead_clients:
            if ws in self.ws_clients:
                self.ws_clients.remove(ws)

    async def request_approval(
        self, tool_name: str, details: str, client_name: str = "AI Agent"
    ) -> bool:
        """Pause tool execution and await human approval via the Web Dashboard."""
        if not self.require_approval:
            return True

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        task_id = str(uuid.uuid4())[:8]

        task_info = {
            "id": task_id,
            "tool": tool_name,
            "details": details,
            "client_name": client_name,
        }
        self.pending_tasks[task_id] = {"future": future, "info": task_info}
        await self.broadcast("approval_requested", task_info)

        try:
            return await asyncio.wait_for(future, timeout=300.0)
        except asyncio.TimeoutError:
            return False
        finally:
            self.pending_tasks.pop(task_id, None)
            await self.broadcast("approval_resolved", {"id": task_id})

    def resolve_approval(self, task_id: str, approved: bool) -> bool:
        """Resolve a pending approval future from the dashboard UI."""
        if task_id in self.pending_tasks:
            future = self.pending_tasks[task_id]["future"]
            if not future.done():
                future.set_result(approved)
            return True
        return False


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
# Exposed through the module-level `state` singleton below.

## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
state: AppState = AppState()
