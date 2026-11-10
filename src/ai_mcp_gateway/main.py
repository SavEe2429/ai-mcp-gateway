"""FastAPI ASGI composition root and Uvicorn server launcher for AI Agent MCP Gateway."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import asyncio
import contextlib
import logging
import sqlite3
import sys
import webbrowser
from typing import AsyncIterator

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp import MCPError

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.core.auth import router as auth_router
from ai_mcp_gateway.core.database import cleanup_expired_tokens, init_db
from ai_mcp_gateway.core.mcp_client_manager import client_manager
from ai_mcp_gateway.core.mcp_server import mcp, record_and_broadcast_log
from ai_mcp_gateway.core.state import state
from ai_mcp_gateway.core.tunnel import start_tailscale_funnel
from ai_mcp_gateway.interfaces.middleware import (
    PollingAccessLogFilter,
    create_security_middleware,
)
from ai_mcp_gateway.interfaces.ui_routes import ui_router
from ai_mcp_gateway.utils.config import CLIENT_ID, CLIENT_SECRET, get_config

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
LOGGER: logging.Logger = logging.getLogger(__name__)
__all__ = ["PollingAccessLogFilter", "app", "mcp", "record_and_broadcast_log", "run_server"]

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
@contextlib.asynccontextmanager
async def lifespan(_fastapi_app: FastAPI) -> AsyncIterator[None]:
    """Manage startup housekeeping, access log filtering, and external MCP clients."""
    try:
        cleanup_expired_tokens()
    except sqlite3.Error as err:
        LOGGER.debug("Token cleanup skipped during startup: %s", err)

    access_logger = logging.getLogger("uvicorn.access")
    polling_filter = PollingAccessLogFilter()
    access_logger.addFilter(polling_filter)
    for handler in access_logger.handlers:
        handler.addFilter(polling_filter)

    client_manager.set_mcp_server(mcp)

    async def _start_clients_in_background() -> None:
        try:
            await client_manager.load_installed_servers()
        except (OSError, RuntimeError, ValueError, MCPError, sqlite3.Error) as err:
            LOGGER.warning("MCP Client Manager startup error: %s", err)

    try:
        if hasattr(mcp, "session_manager") and hasattr(mcp.session_manager, "run"):
            async with mcp.session_manager.run():
                bg_task = asyncio.create_task(_start_clients_in_background())
                try:
                    yield
                finally:
                    bg_task.cancel()
        else:
            bg_task = asyncio.create_task(_start_clients_in_background())
            try:
                yield
            finally:
                bg_task.cancel()
    finally:
        try:
            await client_manager.shutdown()
        except (OSError, RuntimeError, MCPError) as err:
            LOGGER.debug("Ignoring shutdown error for external MCP clients: %s", err)


def create_app() -> FastAPI:
    """Construct and configure the FastAPI gateway application."""
    _configure_windows_console_utf8()
    init_db()
    cfg = get_config()

    fastapi_app = FastAPI(title=cfg.server.title, lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.server.allowed_cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    fastapi_app.include_router(auth_router)
    fastapi_app.include_router(ui_router)
    fastapi_app.middleware("http")(create_security_middleware(mcp_server=mcp))
    _mount_mcp_streamable_http(fastapi_app)
    return fastapi_app


def run_server() -> None:
    """Initialize Tailscale Funnel (if enabled) and start the Uvicorn ASGI server."""
    server_cfg = get_config().server
    port = server_cfg.port
    host = server_cfg.host
    if server_cfg.enable_tailscale_funnel:
        state.mcp_url = start_tailscale_funnel(port)
    else:
        state.mcp_url = f"http://localhost:{port}{server_cfg.mcp_path}"

    dashboard_url = f"http://localhost:{port}/ui"
    print("=" * 65)
    print("AI Agent MCP Gateway Starting")
    print(f"Local Web Dashboard : {dashboard_url}")
    print(f"Active Workspace    : {state.workspace_dir}")
    print(f"MCP Server Endpoint : {state.mcp_url}")
    print(f"Client ID           : {CLIENT_ID}")
    print(f"Client Secret       : {CLIENT_SECRET}")
    print("=" * 65)

    webbrowser.open(dashboard_url)
    uvicorn.run(app, host=host, port=port, log_config=_build_uvicorn_log_config())


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
def _configure_windows_console_utf8() -> None:
    """Force UTF-8 stdout/stderr encoding on Windows consoles when supported."""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except OSError, ValueError, AttributeError:
                pass


def _mount_mcp_streamable_http(fastapi_app: FastAPI) -> None:
    """Mount Streamable HTTP (/mcp) routes onto the FastAPI application."""
    try:
        from mcp.server.transport_security import TransportSecuritySettings

        transport_sec = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    except ImportError:
        transport_sec = None

    if not hasattr(mcp, "streamable_http_app"):
        return
    try:
        streamable_app = mcp.streamable_http_app(
            streamable_http_path="/mcp",
            transport_security=transport_sec,
            session_idle_timeout=None,
        )
        for route in streamable_app.routes:
            fastapi_app.routes.append(route)
    except (RuntimeError, ValueError, TypeError) as err:
        LOGGER.error("MCP Streamable HTTP Init Error: %s", err)


def _build_uvicorn_log_config() -> dict:
    """Build Uvicorn logging config with polling filter and local timestamps."""
    log_config = uvicorn.config.LOGGING_CONFIG.copy()
    log_config.setdefault("filters", {})["polling_filter"] = {"()": PollingAccessLogFilter}
    if "access" in log_config.get("handlers", {}):
        log_config["handlers"]["access"]["filters"] = ["polling_filter"]

    formatters = log_config.get("formatters", {})
    if "default" in formatters:
        formatters["default"]["fmt"] = "[%(asctime)s] %(levelprefix)s %(message)s"
        formatters["default"]["datefmt"] = "%H:%M:%S"
    if "access" in formatters:
        formatters["access"]["fmt"] = (
            '[%(asctime)s] %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
        )
        formatters["access"]["datefmt"] = "%H:%M:%S"
    return log_config


## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
app: FastAPI = create_app()

if __name__ == "__main__":
    run_server()
