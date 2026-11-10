"""Tailscale Funnel tunnel automation for exposing the local MCP endpoint."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import json
import logging
import subprocess
from typing import Optional

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.core.state import state
from ai_mcp_gateway.utils.config import get_config

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
LOGGER: logging.Logger = logging.getLogger(__name__)

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def start_tailscale_funnel(port: Optional[int] = None) -> str:
    """Query Tailscale MagicDNS name and start a background Funnel to the target port."""
    if port is None:
        port = get_config().server.port

    fallback_url = f"http://localhost:{port}/mcp"
    try:
        status_proc = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        if status_proc.returncode != 0:
            print("[Tailscale] Unable to query status; verify Tailscale client is running.")
            return f"http://localhost:{port}/sse"

        data = json.loads(status_proc.stdout)
        dns_name = data.get("Self", {}).get("DNSName", "").rstrip(".")
        if not dns_name:
            print("[Tailscale] DNSName unavailable; verify MagicDNS is enabled.")
            return f"http://localhost:{port}/sse"

        funnel_proc = subprocess.run(
            ["tailscale", "funnel", "--bg", str(port)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if funnel_proc.returncode == 0:
            public_url = f"https://{dns_name}"
            mcp_url = f"{public_url}/mcp"
            state.public_url = public_url
            state.mcp_url = mcp_url
            return mcp_url

        err_msg = funnel_proc.stderr.strip() or funnel_proc.stdout.strip()
        print(f"[Tailscale Funnel Error] {err_msg}")
        return fallback_url
    except FileNotFoundError:
        print("[Tailscale] 'tailscale' executable not found in PATH.")
        return fallback_url
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as err:
        LOGGER.warning("Tailscale setup error: %s", err)
        print(f"[Tailscale Error] {err}")
        return fallback_url


def stop_tailscale_funnel(port: Optional[int] = None) -> None:
    """Stop Tailscale Funnel on the configured port."""
    if port is None:
        port = get_config().server.port
    try:
        subprocess.run(
            ["tailscale", "funnel", str(port), "off"],
            capture_output=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError) as err:
        LOGGER.debug("Ignoring Tailscale stop error: %s", err)


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Module exposes library functions only.
