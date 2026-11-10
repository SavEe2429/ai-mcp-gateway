"""Security and protocol negotiation ASGI middleware pipeline."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
from fastapi import Request
from fastapi.responses import JSONResponse

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.core.database import get_token_client, save_token, verify_token
from ai_mcp_gateway.core.state import state
from ai_mcp_gateway.interfaces.middleware.identity import (
    current_client_var,
    detect_ai_provider,
    extract_identity_from_payload,
)
from ai_mcp_gateway.interfaces.middleware.shield import (
    check_ip_blacklist,
    check_localhost_dashboard_guard,
    check_scanner_shield,
)

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
# No module-level constants required.

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def create_security_middleware(mcp_server: Any = None) -> Callable:
    """Create the security and protocol negotiation HTTP middleware."""

    async def security_middleware(request: Request, call_next: Callable):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        client_host = request.client.host if request.client else ""

        guard_resp = (
            check_ip_blacklist(client_host)
            or check_scanner_shield(path, client_host)
            or check_localhost_dashboard_guard(path, request)
        )
        if guard_resp:
            return guard_resp

        if path == "/sse" or path.startswith("/sse/"):
            request.scope["path"] = "/mcp"
            path = "/mcp"

        sess_id = _recover_mcp_session_if_expired(request, path, mcp_server)

        token, auth_error_resp = _verify_mcp_bearer_token(request, path)
        if auth_error_resp:
            return auth_error_resp

        detected_client, parsed_body = await _inspect_mcp_post_identity(
            request, path, sess_id, client_host, token
        )
        ai_name, detection_source = _resolve_ai_identity(
            request, detected_client, token, sess_id, client_host
        )

        if path.startswith("/mcp") or path.startswith("/oauth"):
            _log_ai_request(request, path, ai_name, client_host)

        token_ctx = current_client_var.set(ai_name)
        start_time = time.time()
        try:
            response = await call_next(request)
            resp_sess_id = response.headers.get("mcp-session-id")
            if resp_sess_id and ai_name:
                state.register_client(
                    resp_sess_id, ai_name, source=detection_source, host=client_host
                )

            if path.startswith("/mcp") or path.startswith("/oauth"):
                await _record_dev_traffic(
                    request,
                    path,
                    response.status_code,
                    start_time,
                    ai_name,
                    detection_source,
                    parsed_body,
                )
            return response
        finally:
            current_client_var.reset(token_ctx)

    return security_middleware


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
def _recover_mcp_session_if_expired(request: Request, path: str, mcp_server: Any) -> Optional[str]:
    """Strip stale mcp-session-id headers when the session no longer exists."""
    sess_id = request.headers.get("mcp-session-id")
    if path.startswith("/mcp") and sess_id and mcp_server:
        mgr = getattr(mcp_server, "session_manager", None)
        if mgr and hasattr(mgr, "_server_instances") and sess_id not in mgr._server_instances:
            print(
                f"[Session Recovery] Resetting expired session ({sess_id[:8]}...) to create a fresh session"
            )
            request.scope["headers"] = [
                (k, v)
                for k, v in request.scope.get("headers", [])
                if k.lower() != b"mcp-session-id"
            ]
            return None
    return sess_id


def _verify_mcp_bearer_token(
    request: Request, path: str
) -> tuple[Optional[str], Optional[JSONResponse]]:
    """Validate OAuth Bearer token for /mcp requests and handle DELETE termination."""
    if not path.startswith("/mcp"):
        return None, None

    token: Optional[str] = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    elif "token" in request.query_params:
        token = request.query_params.get("token")

    if not token:
        pub_url = state.public_url.rstrip("/") if state.public_url else "http://localhost:3000"
        headers = {
            "WWW-Authenticate": f'Bearer resource_metadata="{pub_url}/.well-known/oauth-protected-resource"'
        }
        return None, JSONResponse(
            status_code=401, content={"error": "Missing Bearer token"}, headers=headers
        )

    if not verify_token(token):
        return token, JSONResponse(
            status_code=403,
            content={"error": "Invalid or expired token"},
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    if request.method == "DELETE":
        return token, JSONResponse(status_code=200, content={"status": "session terminated"})

    return token, None


async def _inspect_mcp_post_identity(
    request: Request,
    path: str,
    sess_id: Optional[str],
    client_host: str,
    token: Optional[str],
) -> tuple[Optional[str], Any]:
    """Parse POST /mcp JSON-RPC payload to identify the connecting AI client."""
    detected_client: Optional[str] = None
    parsed_body: Any = None
    if not (path.startswith("/mcp") and request.method == "POST"):
        return detected_client, parsed_body

    try:
        body_bytes = await request.body()
        if body_bytes:
            payload = json.loads(body_bytes.decode("utf-8", errors="replace"))
            parsed_body = payload
            raw_client, source_label, method_name = extract_identity_from_payload(payload)
            if raw_client:
                detected_client = raw_client
                if sess_id:
                    state.register_client(
                        sess_id, detected_client, source=source_label, host=client_host
                    )
                if client_host:
                    state.register_client(
                        client_host, detected_client, source=source_label, host=client_host
                    )
                if token:
                    save_token(token, client_name=detected_client)
                print(f"[MCP Protocol] Identified client: {detected_client} (via {source_label})")
                if method_name == "initialize":
                    print(
                        f"[Raw MCP Handshake Payload]\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n"
                    )
    except json.JSONDecodeError, UnicodeDecodeError, ValueError, RuntimeError:
        pass
    return detected_client, parsed_body


def _resolve_ai_identity(
    request: Request,
    detected_client: Optional[str],
    token: Optional[str],
    sess_id: Optional[str],
    client_host: str,
) -> tuple[str, str]:
    """Resolve authoritative AI identity across payload, token, session cache, and headers."""
    ai_name = detected_client
    detection_source = "MCP Payload" if detected_client else ""

    if not ai_name and token:
        ai_name = get_token_client(token)
        if ai_name:
            detection_source = "OAuth Token"

    if not ai_name and sess_id and sess_id in state.session_ai_clients:
        ai_name = state.session_ai_clients[sess_id]
        detection_source = "Session Cache"

    if not ai_name and client_host and client_host in state.session_ai_clients:
        ai_name = state.session_ai_clients[client_host]
        detection_source = "IP Cache"

    if not ai_name:
        ai_name = detect_ai_provider(request)
        detection_source = "HTTP Headers"

    if sess_id:
        state.register_client(sess_id, ai_name, source=detection_source, host=client_host)
    if client_host:
        state.register_client(client_host, ai_name, source=detection_source, host=client_host)

    return ai_name, detection_source


def _log_ai_request(request: Request, path: str, ai_name: str, client_host: str) -> None:
    """Print formatted AI HTTP request line to console."""
    auth_header = request.headers.get("Authorization", "")
    has_auth = (
        "Bearer"
        if auth_header.startswith("Bearer ")
        else ("No Auth" if not auth_header else "Other Auth")
    )
    time_prefix = datetime.now().strftime("%H:%M:%S")
    print(
        f"[{time_prefix}] [AI Request] [{ai_name}] {request.method} {path} [{has_auth}] (From {client_host or 'unknown'})"
    )


async def _record_dev_traffic(
    request: Request,
    path: str,
    status_code: int,
    start_time: float,
    ai_name: str,
    detection_source: str,
    parsed_body: Any,
) -> None:
    """Sanitize authorization headers and broadcast developer traffic telemetry."""
    latency_ms = round((time.time() - start_time) * 1000, 2)
    sanitized_headers: Dict[str, str] = {}
    for key, value in request.headers.items():
        if key.lower() == "authorization" and value.startswith("Bearer "):
            token_part = value.split(" ", 1)[1]
            sanitized_headers[key] = (
                f"Bearer {token_part[:6]}...{token_part[-4:]}"
                if len(token_part) > 10
                else "Bearer ***"
            )
        else:
            sanitized_headers[key] = value

    traffic_item = {
        "id": int(time.time() * 1000),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "client_name": ai_name,
        "detection_source": detection_source,
        "method": request.method,
        "path": path,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "headers": sanitized_headers,
        "payload": parsed_body,
    }
    state.add_dev_traffic(traffic_item)
    await state.broadcast("dev_traffic", traffic_item)


## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Security middleware factory module only.
