"""Security shields, IP blacklisting, scanner blocking, and localhost guards."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
from typing import Optional
from urllib.parse import urlparse

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
from fastapi import Request
from fastapi.responses import JSONResponse

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.core.state import state
from ai_mcp_gateway.utils.config import get_config

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def check_ip_blacklist(client_host: str) -> Optional[JSONResponse]:
    """Reject requests from temporarily banned scanner IPs immediately with 403."""
    if client_host and state.is_ip_blocked(client_host):
        return JSONResponse(
            status_code=403,
            content={"error": "Access denied: IP temporarily blocked due to malicious scanning"},
        )
    return None


def check_scanner_shield(path: str, client_host: str) -> Optional[JSONResponse]:
    """Detect automated bot probes targeting PHP, WordPress, secrets, or backup files."""
    cfg = get_config()
    p_lower = path.lower()
    is_scanner = any(p_lower.endswith(ext) for ext in cfg.security.scanner_extensions) or any(
        prefix in p_lower for prefix in cfg.security.scanner_prefixes
    )
    if is_scanner:
        if client_host:
            state.block_ip(
                client_host,
                duration_seconds=cfg.session.ip_ban_duration,
                reason="Malicious Bot Scanner",
                target_path=path,
            )
            print(
                f"[Security Shield] Auto-banned malicious scanner from IP: {client_host} (Target: {path})"
            )
        return JSONResponse(status_code=404, content={"error": "Not Found"})
    return None


def check_localhost_dashboard_guard(path: str, request: Request) -> Optional[JSONResponse]:
    """Restrict Web Dashboard routes (/ui, /api/ui) strictly to same-origin localhost callers."""
    if not (path.startswith("/ui") or path.startswith("/api/ui")):
        return None

    cfg = get_config()
    client_host = request.client.host if request.client else ""
    is_funnel = request.headers.get("Tailscale-Funnel-Request") is not None

    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        first_hop = xff.split(",")[0].strip()
        if first_hop not in LOCAL_HOSTS:
            return JSONResponse(
                status_code=403,
                content={"error": "Dashboard is restricted to localhost only"},
            )

    xfh = (request.headers.get("x-forwarded-host") or "").strip().lower()
    if xfh:
        xfh_host = xfh.split(":")[0].strip("[]")
        if xfh_host not in LOCAL_HOSTS:
            return JSONResponse(
                status_code=403,
                content={"error": "Dashboard is restricted to localhost only"},
            )

    if is_funnel or client_host not in cfg.security.allowed_local_hosts:
        return JSONResponse(
            status_code=403, content={"error": "Dashboard is restricted to localhost only"}
        )

    origin = (request.headers.get("origin") or "").strip()
    if origin:
        parsed_origin = urlparse(origin)
        origin_host = (parsed_origin.hostname or "").lower()
        allowed_origins = set(cfg.security.allowed_local_hosts) | {"testserver"}
        if origin_host not in allowed_origins:
            return JSONResponse(
                status_code=403,
                content={"error": "Cross-origin access to local dashboard API is forbidden"},
            )

    sec_fetch_site = (request.headers.get("sec-fetch-site") or "").strip().lower()
    if sec_fetch_site == "cross-site":
        return JSONResponse(
            status_code=403,
            content={"error": "Cross-site requests to local dashboard API are forbidden"},
        )
    return None


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Middleware security guard module only.
