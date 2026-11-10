"""OAuth 2.0 / 2.1 RFC 8414 metadata discovery, PKCE verification, and token endpoints."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import base64
import binascii
import hashlib
import html
import os
import secrets
import time
import urllib.parse
from datetime import datetime
from typing import Any, Dict, Optional

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.core.database import (
    get_token_client,
    revoke_token,
    save_token,
    verify_token,
)
from ai_mcp_gateway.core.state import state
from ai_mcp_gateway.utils.config import (
    CLIENT_ID,
    CLIENT_SECRET,
    get_config,
    load_or_create_client_secret,
)

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
_load_or_create_client_secret = load_or_create_client_secret
router: APIRouter = APIRouter()
security: HTTPBearer = HTTPBearer(auto_error=False)
AUTH_CODES: Dict[str, Dict[str, Any]] = {}

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def is_allowed_redirect_uri(redirect_uri: str) -> bool:
    """Validate that redirect_uri targets localhost or an allowed AI provider domain."""
    if not redirect_uri:
        return False
    try:
        parsed = urllib.parse.urlparse(redirect_uri)
    except ValueError:
        return False

    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if not host or "\r" in redirect_uri or "\n" in redirect_uri:
        return False

    cfg = get_config()
    allowed_local = set(cfg.auth.allowed_local_redirect_hosts)
    if host in allowed_local:
        return scheme in ("http", "https")

    if scheme != "https":
        return False

    extra_hosts = [
        h.strip().lower()
        for h in os.environ.get("MCP_ALLOWED_REDIRECT_HOSTS", "").split(",")
        if h.strip()
    ]
    allowed_suffixes = tuple(cfg.auth.allowed_redirect_domains) + tuple(extra_hosts)
    return any(host == dom or host.endswith(f".{dom}") for dom in allowed_suffixes)


def get_base_url(request: Request) -> str:
    """Resolve authoritative external Base URL supporting direct, Funnel, and proxy calls."""
    proto = request.headers.get("x-forwarded-proto")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if proto and host:
        return f"{proto}://{host}".rstrip("/")

    if state.public_url and not any(loc in state.public_url for loc in ("localhost", "127.0.0.1")):
        return state.public_url.rstrip("/")

    return str(request.base_url).rstrip("/")


def verify_pkce(code_verifier: str, code_challenge: str, method: str) -> bool:
    """Verify PKCE code_verifier per RFC 7636 using fail-closed, timing-safe comparison."""
    if not code_verifier or not code_challenge:
        return False
    if method == "plain":
        return secrets.compare_digest(code_verifier, code_challenge)
    if method == "S256":
        try:
            digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
            computed = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
            return secrets.compare_digest(computed, code_challenge.rstrip("="))
        except UnicodeEncodeError:
            return False
    return False


@router.get("/.well-known/oauth-authorization-server")
@router.get("/mcp/.well-known/oauth-authorization-server")
@router.get("/.well-known/openid-configuration")
@router.get("/mcp/.well-known/openid-configuration")
async def oauth_metadata(request: Request) -> Dict[str, Any]:
    """Serve RFC 8414 OAuth 2.0 / OpenID Connect authorization server metadata."""
    base_url = get_base_url(request)
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
            "none",
        ],
        "scopes_supported": ["mcp"],
    }


@router.get("/.well-known/oauth-protected-resource")
@router.get("/mcp/.well-known/oauth-protected-resource")
async def oauth_protected_resource(request: Request) -> Dict[str, Any]:
    """Serve RFC 9728 OAuth protected resource metadata for MCP clients."""
    base_url = get_base_url(request)
    return {"resource": base_url, "authorization_servers": [base_url], "scopes_supported": ["mcp"]}


@router.get("/oauth/authorize")
@router.post("/oauth/authorize")
async def oauth_authorize(
    request: Request,
    response_type: str = Query("code"),
    client_id: Optional[str] = Query(None),
    redirect_uri: Optional[str] = Query(None),
    scope: Optional[str] = Query("mcp"),
    oauth_state: Optional[str] = Query(None, alias="state"),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None),
    auto_approve: Optional[str] = Query("1"),
) -> HTMLResponse:
    """Validate redirect_uri, issue an authorization code, and render consent redirect."""
    if not redirect_uri:
        return HTMLResponse("<h3>OAuth Error: Missing redirect_uri</h3>", status_code=400)

    if not is_allowed_redirect_uri(redirect_uri):
        return HTMLResponse(
            "<h3>OAuth Error: Untrusted or invalid redirect_uri</h3>", status_code=400
        )

    client_name = _infer_client_name(redirect_uri, client_id)
    auth_code = secrets.token_urlsafe(32)
    AUTH_CODES[auth_code] = {
        "client_id": client_id,
        "client_name": client_name,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method or ("S256" if code_challenge else "plain"),
        "expires_at": time.time() + get_config().session.auth_code_ttl,
    }

    delimiter = "&" if "?" in redirect_uri else "?"
    callback_url = f"{redirect_uri}{delimiter}code={auth_code}"
    if oauth_state:
        callback_url += f"&state={oauth_state}"

    return HTMLResponse(content=_render_consent_html(callback_url, client_id, scope))


@router.post("/oauth/token")
async def oauth_token(
    request: Request,
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    grant_type: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Issue or refresh OAuth Bearer access tokens."""
    cid, csec = _extract_basic_credentials(authorization, client_id, client_secret)

    if grant_type == "authorization_code":
        return _handle_authorization_code_grant(code, cid, csec, redirect_uri, code_verifier)
    if grant_type == "client_credentials":
        return _handle_client_credentials_grant(cid, csec)
    if grant_type == "refresh_token":
        return _handle_refresh_token_grant(refresh_token)

    raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")


def check_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """FastAPI dependency verifying Bearer token validity."""
    if not credentials or not verify_token(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing access token"
        )
    return credentials.credentials


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
def _infer_client_name(redirect_uri: str, client_id: Optional[str]) -> str:
    """Infer standard AI provider label from redirect_uri or client_id."""
    redirect_uri_lower = (redirect_uri or "").lower()
    client_id_lower = (client_id or "").lower()
    if any(k in redirect_uri_lower or k in client_id_lower for k in ("claude", "anthropic")):
        return "Claude"
    if any(k in redirect_uri_lower or k in client_id_lower for k in ("chatgpt", "openai", "gpt")):
        return "ChatGPT"
    if any(
        k in redirect_uri_lower or k in client_id_lower for k in ("google", "gemini", "aistudio")
    ):
        return "Gemini"
    if client_id and client_id != CLIENT_ID:
        return client_id
    return "Gemini"


def _render_consent_html(callback_url: str, client_id: Optional[str], scope: Optional[str]) -> str:
    """Render auto-redirecting OAuth authorization page."""
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Authorize MCP Gateway</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <meta http-equiv="refresh" content="2;url={html.escape(callback_url)}">
</head>
<body class="bg-slate-950 text-slate-100 flex items-center justify-center min-h-screen p-4 font-sans">
  <div class="bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-md w-full shadow-2xl text-center">
    <h1 class="text-xl font-bold text-white mb-2">Authorize Local MCP Gateway</h1>
    <p class="text-xs text-slate-400 mb-6 leading-relaxed">
      Connecting your AI client securely to the local MCP server...
    </p>
    <div class="bg-slate-950 border border-slate-800 rounded-xl p-3 text-left text-xs mb-6 space-y-1.5 font-mono">
      <div class="flex justify-between text-slate-400">
        <span>Client ID:</span>
        <span class="text-emerald-400">{html.escape(client_id or CLIENT_ID)}</span>
      </div>
      <div class="flex justify-between text-slate-400">
        <span>Scope:</span>
        <span class="text-cyan-400">{html.escape(scope or "mcp")}</span>
      </div>
    </div>
    <a href="{html.escape(callback_url)}"
       class="block w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-medium text-sm transition shadow-lg shadow-emerald-600/30">
      Continue (Authorize)
    </a>
    <p class="text-[11px] text-slate-500 mt-3">Redirecting automatically in 2 seconds...</p>
  </div>
</body>
</html>
"""


def _extract_basic_credentials(
    authorization: Optional[str],
    client_id: Optional[str],
    client_secret: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """Decode HTTP Basic Auth credentials when provided."""
    cid, csec = client_id, client_secret
    if authorization and authorization.startswith("Basic "):
        try:
            raw = base64.b64decode(authorization.split(" ")[1]).decode("utf-8")
            if ":" in raw:
                cid, csec = raw.split(":", 1)
        except binascii.Error, UnicodeDecodeError, IndexError:
            pass
    return cid, csec


def _handle_authorization_code_grant(
    code: Optional[str],
    cid: Optional[str],
    csec: Optional[str],
    redirect_uri: Optional[str],
    code_verifier: Optional[str],
) -> Dict[str, Any]:
    """Validate authorization code, PKCE, and client credentials before issuing token."""
    if not code or code not in AUTH_CODES:
        raise HTTPException(status_code=400, detail="Invalid or expired authorization code")

    code_info = AUTH_CODES.pop(code)
    if time.time() > code_info["expires_at"]:
        raise HTTPException(status_code=400, detail="Authorization code expired")

    expected_cid = code_info.get("client_id")
    if expected_cid and cid and cid != expected_cid:
        raise HTTPException(status_code=400, detail="Mismatched client_id for authorization code")

    expected_redirect = code_info.get("redirect_uri")
    if expected_redirect and redirect_uri and redirect_uri != expected_redirect:
        raise HTTPException(
            status_code=400, detail="Mismatched redirect_uri for authorization code"
        )

    saved_challenge = code_info.get("code_challenge")
    if saved_challenge:
        if not code_verifier:
            raise HTTPException(status_code=400, detail="Missing code_verifier for PKCE")
        method = code_info.get("code_challenge_method", "S256")
        if not verify_pkce(code_verifier, saved_challenge, method):
            raise HTTPException(status_code=400, detail="PKCE verification failed")

    if csec and not secrets.compare_digest(csec, CLIENT_SECRET):
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    client_name = code_info.get("client_name", "Gemini")
    access_token = secrets.token_hex(32)
    save_token(access_token, client_name=client_name)
    time_prefix = datetime.now().strftime("%H:%M:%S")
    print(f"[{time_prefix}] [AI Auth] [{client_name}] Access token issued via authorization_code")
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": get_config().session.ttl,
        "refresh_token": access_token,
        "scope": "mcp",
    }


def _handle_client_credentials_grant(cid: Optional[str], csec: Optional[str]) -> Dict[str, Any]:
    """Validate client_credentials grant and issue a Bearer access token."""
    if cid == CLIENT_ID and csec and secrets.compare_digest(csec, CLIENT_SECRET):
        token = secrets.token_hex(32)
        client_name = "Gemini"
        save_token(token, client_name=client_name)
        time_prefix = datetime.now().strftime("%H:%M:%S")
        print(
            f"[{time_prefix}] [AI Auth] [{client_name}] Access token issued via client_credentials"
        )
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": get_config().session.ttl,
            "refresh_token": token,
            "scope": "mcp",
        }
    raise HTTPException(status_code=401, detail="Invalid client credentials")


def _handle_refresh_token_grant(refresh_token: Optional[str]) -> Dict[str, Any]:
    """Rotate a valid refresh token and issue a fresh Bearer access token."""
    if refresh_token and verify_token(refresh_token):
        client_name = get_token_client(refresh_token) or "Gemini"
        revoke_token(refresh_token)
        new_token = secrets.token_hex(32)
        save_token(new_token, client_name=client_name)
        time_prefix = datetime.now().strftime("%H:%M:%S")
        print(f"[{time_prefix}] [AI Auth] [{client_name}] Access token refreshed")
        return {
            "access_token": new_token,
            "token_type": "Bearer",
            "expires_in": get_config().session.ttl,
            "refresh_token": new_token,
            "scope": "mcp",
        }
    raise HTTPException(status_code=401, detail="Invalid refresh token")


## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# OAuth router module only.
