"""AI Client identity detection, extraction, and context propagation."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import contextvars
from typing import Any, Optional, Tuple

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
from fastapi import Request

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.core.state import state

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
current_client_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_client_name", default="Gemini"
)

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def extract_client_name(raw_name: str) -> str:
    """Normalize raw client name from clientInfo or headers into standard provider name."""
    if not raw_name:
        return "AI Agent"
    name_lower = raw_name.lower().strip()
    if any(k in name_lower for k in ("claude", "anthropic")):
        return "Claude"
    if any(k in name_lower for k in ("gemini", "google", "aistudio")):
        return "Gemini"
    if any(k in name_lower for k in ("chatgpt", "openai", "gpt")):
        return "ChatGPT"
    if "cursor" in name_lower:
        return "Cursor"
    if "antigravity" in name_lower:
        return "Antigravity"
    if name_lower in ("mcp", "mcp-client", "mcp_client"):
        return "Gemini"
    return raw_name


def detect_ai_provider(request: Request) -> str:
    """Infer AI provider from request headers, session cache, or client IP."""
    ua = (request.headers.get("user-agent") or "").lower()
    referer = (request.headers.get("referer") or "").lower()
    origin = (request.headers.get("origin") or "").lower()
    all_headers_str = " ".join(f"{k.lower()}:{v.lower()}" for k, v in request.headers.items())

    if any(k in ua or k in referer or k in origin for k in ("claude", "anthropic")):
        return "Claude"
    if (
        any(k in ua or k in referer or k in origin for k in ("chatgpt", "openai", "gpt"))
        or "openai" in all_headers_str
    ):
        return "ChatGPT"
    if any(k in ua or k in referer or k in origin for k in ("google", "gemini")):
        return "Gemini"
    if "cursor" in ua or "cursor" in all_headers_str:
        return "Cursor"

    client_ip = request.client.host if request.client else ""
    if client_ip.startswith("66.249.") or client_ip.startswith("192.178."):
        return "Gemini"

    sess_id = request.headers.get("mcp-session-id")
    if sess_id and sess_id in state.session_ai_clients:
        return state.session_ai_clients[sess_id]

    local_ips = {"127.0.0.1", "::1", "localhost"}
    if client_ip and client_ip not in local_ips and client_ip in state.session_ai_clients:
        return state.session_ai_clients[client_ip]
    return getattr(state, "last_active_ai", "Gemini") or "Gemini"


def extract_identity_from_payload(
    payload: Any,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Inspect JSON-RPC payload to extract (client_name, source_label, method_name)."""
    msgs = payload if isinstance(payload, list) else [payload]
    for msg in msgs:
        if not isinstance(msg, dict):
            continue
        method = msg.get("method", "")
        params = msg.get("params") or {}
        raw_client_name = ""
        source_label = "MCP Handshake"

        if isinstance(params, dict) and "_meta" in params:
            meta = params.get("_meta") or {}
            if isinstance(meta, dict):
                mcp_client_info = meta.get("io.modelcontextprotocol/clientInfo") or {}
                if isinstance(mcp_client_info, dict) and mcp_client_info.get("name"):
                    raw_client_name = mcp_client_info.get("name")
                    source_label = "OpenAI Meta ClientInfo"
                elif any(k.startswith("openai/") or "openai" in k.lower() for k in meta.keys()):
                    raw_client_name = "ChatGPT"
                    source_label = "OpenAI Meta Headers"

        if not raw_client_name and isinstance(params, dict) and "clientInfo" in params:
            client_info = params.get("clientInfo") or {}
            if isinstance(client_info, dict) and client_info.get("name"):
                raw_client_name = client_info.get("name")
                source_label = "MCP Handshake"

        if raw_client_name:
            return extract_client_name(raw_client_name), source_label, method

    return None, None, None


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Middleware identity helper module only.
