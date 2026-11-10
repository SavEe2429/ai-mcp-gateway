"""Pydantic models for validating config/config.yaml (Single Source of Truth)."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
from typing import List, Optional

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
from pydantic import BaseModel, Field

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
# No local application imports required.

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
# No module-level constants required.

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.


## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
class SessionConfig(BaseModel):
    """Session, token lifetimes, and timeout configuration."""

    ttl: int = Field(
        default=604800,
        ge=1,
        description="OAuth access token lifetime in seconds (e.g. 604800 = 7 days)",
    )
    auth_code_ttl: int = Field(
        default=3600,
        ge=1,
        description="OAuth 2.0 authorization code lifetime in seconds",
    )
    refresh_token_ttl: int = Field(
        default=2592000,
        ge=1,
        description="Refresh token lifetime in seconds (e.g. 2592000 = 30 days)",
    )
    ip_ban_duration: int = Field(
        default=3600,
        ge=0,
        description="Temporary ban duration for detected scanners in seconds (e.g. 3600 = 1 hour)",
    )
    dev_traffic_max_items: int = Field(
        default=100,
        ge=1,
        description="Max entries stored in developer telemetry memory buffer",
    )
    terminal_timeout: float = Field(
        default=60.0,
        gt=0,
        description="Terminal sync wait timeout in seconds before auto-backgrounding (default: 60.0 = 1 minute)",
    )
    audit_log_limit: int = Field(
        default=50,
        ge=1,
        description="Default limit for recent audit log queries",
    )


class ServerConfig(BaseModel):
    """HTTP Server, ports, CORS, and network configuration."""

    host: str = Field(default="0.0.0.0", description="Server listening host")
    port: int = Field(default=3000, ge=1, le=65535, description="Server listening port")
    mcp_path: str = Field(default="/mcp", description="Streamable HTTP MCP endpoint route")
    ui_path: str = Field(default="/ui", description="Web Dashboard route")
    title: str = Field(default="Local AI Agent Gateway", description="FastAPI app title")
    mcp_server_name: str = Field(default="Local-Agent-Bridge", description="FastMCP server name")
    mcp_server_title: str = Field(
        default="Local Computer Agent Gateway", description="FastMCP server title"
    )
    mcp_server_description: str = Field(
        default=(
            "Bridge to access, create, edit files, execute terminal commands, "
            "and take desktop screenshots on the user's local PC."
        ),
        description="FastMCP server description",
    )
    enable_tailscale_funnel: bool = Field(
        default=True, description="Enable automatic Tailscale Funnel port sharing"
    )
    allowed_cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )


class StorageConfig(BaseModel):
    """Storage directory and file path configurations."""

    data_dir: str = Field(default="data", description="Data directory relative to project root")
    db_path: str = Field(
        default="data/gateway.db",
        description="SQLite database file path relative to project root",
    )
    client_secret_file: str = Field(
        default="data/client_secret.key",
        description="OAuth client secret key file path",
    )
    workspace_dir: str = Field(
        default="workspace", description="Default sandbox workspace directory"
    )


class AuthConfig(BaseModel):
    """OAuth and client credentials configuration."""

    client_id: str = Field(default="local-mcp", description="OAuth Client ID")
    client_secret: Optional[str] = Field(
        default="",
        description="Optional static client secret; empty string generates random key",
    )
    allowed_redirect_domains: List[str] = Field(
        default_factory=lambda: [
            "claude.ai",
            "anthropic.com",
            "chatgpt.com",
            "openai.com",
            "google.com",
            "googleapis.com",
            "googleusercontent.com",
            "gemini.google.com",
        ],
        description="Allowed domain suffixes for OAuth redirect callbacks",
    )
    allowed_local_redirect_hosts: List[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "::1"],
        description="Allowed localhost hostnames for OAuth redirects",
    )


class SecurityConfig(BaseModel):
    """Security rules, host whitelist, and scanner detection patterns."""

    allowed_local_hosts: List[str] = Field(
        default_factory=lambda: ["127.0.0.1", "::1", "localhost", "testclient"],
        description="Whitelisted hostnames permitted to access local dashboard",
    )
    scanner_extensions: List[str] = Field(
        default_factory=lambda: [
            ".php",
            ".bak",
            ".old",
            ".save",
            ".orig",
            ".yml",
            ".yaml",
            ".env",
            ".config",
            ".xml",
            ".ini",
            "~",
        ],
        description="File extensions that trigger immediate scanner auto-ban",
    )
    scanner_prefixes: List[str] = Field(
        default_factory=lambda: [
            "/wp-",
            "/wordpress",
            "/vendor",
            "/sites",
            "/storage",
            "/token.json",
            "/auth.json",
            "/wgetrc",
            "/user_secrets",
            "/store",
            "/src/auth",
            "/web/auth",
            "/www/auth",
            "/ws-config",
        ],
        description="URL path prefixes that trigger immediate scanner auto-ban",
    )
    silenced_log_prefixes: List[str] = Field(
        default_factory=lambda: [
            "/api/ui/state",
            "/api/ui/files",
            "/api/ui/dev",
            "/ws/ui",
            "/favicon.ico",
        ],
        description="URL paths excluded from Uvicorn access logging noise",
    )


class GatewayConfig(BaseModel):
    """Root configuration model uniting and validating all domains from config/config.yaml."""

    session: SessionConfig = Field(default_factory=SessionConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
# Exposed through Pydantic configuration model classes above.

## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Schema definition module only.
