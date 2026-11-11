"""Built-in MCP server instance, activity telemetry, and sandboxed tool bindings."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import asyncio
from datetime import datetime
from typing import Optional

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
try:
    from mcp.server.fastmcp import FastMCP as MCPServerClass
    from mcp.server.fastmcp import Image
except ImportError:
    from mcp.server.mcpserver import Image
    from mcp.server.mcpserver import MCPServer as MCPServerClass

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
import ai_mcp_gateway.tools.filesystem as fs
import ai_mcp_gateway.tools.terminal as term
import ai_mcp_gateway.tools.vision as vis
from ai_mcp_gateway.core.database import get_ai_usage_stats, log_activity
from ai_mcp_gateway.core.mcp_client_manager import BASE_GATEWAY_INSTRUCTIONS, client_manager
from ai_mcp_gateway.core.state import state
from ai_mcp_gateway.interfaces.middleware import current_client_var
from ai_mcp_gateway.utils.config import get_config

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
_CFG = get_config()

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.

## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
mcp = MCPServerClass(
    name=_CFG.server.mcp_server_name,
    title=_CFG.server.mcp_server_title,
    description=_CFG.server.mcp_server_description,
    instructions=BASE_GATEWAY_INSTRUCTIONS,
)
client_manager.set_mcp_server(mcp)


async def record_and_broadcast_log(
    tool_name: str,
    params: str,
    status: str,
    result: str,
    client_name: Optional[str] = None,
) -> None:
    """Persist a tool invocation to SQLite and broadcast it to dashboard WebSockets."""
    chosen_client = (
        client_name
        or current_client_var.get()
        or getattr(state, "last_active_ai", "Gemini")
        or "Gemini"
    )
    now_dt = datetime.now()
    timestamp_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    time_prefix = now_dt.strftime("%H:%M:%S")

    await asyncio.to_thread(
        log_activity,
        tool_name,
        params,
        status,
        result,
        client_name=chosen_client,
        timestamp=timestamp_str,
    )
    ai_stats = await asyncio.to_thread(get_ai_usage_stats)
    log_entry = {
        "id": int(now_dt.timestamp() * 1000),
        "tool_name": tool_name,
        "params": params,
        "status": status,
        "result": result,
        "client_name": chosen_client,
        "timestamp": timestamp_str,
    }
    await state.broadcast("log", {"entry": log_entry, "ai_usage": ai_stats})

    clean_params = params.replace("\r", "").replace("\n", " ").strip()
    if len(clean_params) > 70:
        clean_params = clean_params[:67] + "..."
    print(f"[{time_prefix}] [AI Action] [{chosen_client}] {tool_name}({clean_params}) -> {status}")


@mcp.tool()
async def list_workspace_files(subdir: str = "") -> str:
    """List all files and directories in the local workspace."""
    try:
        res = await asyncio.to_thread(fs.list_files, subdir)
        await record_and_broadcast_log("list_files", subdir or ".", "SUCCESS", res[:300])
        return res
    except (OSError, ValueError, RuntimeError) as err:
        await record_and_broadcast_log("list_files", subdir, "ERROR", str(err))
        return f"Error: {err}"


@mcp.tool()
async def read_workspace_file(filepath: str) -> str:
    """Read the full content of a file from the workspace."""
    try:
        res = await asyncio.to_thread(fs.read_file, filepath)
        await record_and_broadcast_log("read_file", filepath, "SUCCESS", f"Read {len(res)} chars")
        return res
    except (OSError, ValueError, RuntimeError) as err:
        await record_and_broadcast_log("read_file", filepath, "ERROR", str(err))
        return f"Error: {err}"


@mcp.tool()
async def write_workspace_file(filepath: str, content: str) -> str:
    """Write, save, or overwrite a file in the workspace directory."""
    try:
        approved = await state.request_approval(
            "write_file", f"File: {filepath}\n\n{content[:1000]}"
        )
        if not approved:
            await record_and_broadcast_log(
                "write_file", filepath, "DENIED", "User rejected file write"
            )
            return "Error: Denied by user"
        res = await asyncio.to_thread(fs.write_file, filepath, content)
        await record_and_broadcast_log("write_file", filepath, "SUCCESS", res)
        return res
    except (OSError, ValueError, RuntimeError) as err:
        await record_and_broadcast_log("write_file", filepath, "ERROR", str(err))
        return f"Error: {err}"


@mcp.tool()
async def patch_workspace_file(filepath: str, search_block: str, replace_block: str) -> str:
    """Partially modify a file in the workspace by replacing search_block with replace_block."""
    try:
        diff_preview = (
            f"File: {filepath}\n--- SEARCH ---\n{search_block}\n+++ REPLACE +++\n{replace_block}"
        )
        approved = await state.request_approval("patch_file", diff_preview)
        if not approved:
            await record_and_broadcast_log("patch_file", filepath, "DENIED", "User rejected patch")
            return "Error: Denied by user"
        res = await asyncio.to_thread(fs.patch_file, filepath, search_block, replace_block)
        await record_and_broadcast_log("patch_file", filepath, "SUCCESS", res)
        return res
    except (OSError, ValueError, RuntimeError) as err:
        await record_and_broadcast_log("patch_file", filepath, "ERROR", str(err))
        return f"Error: {err}"


@mcp.tool()
async def run_command(command: str) -> str:
    """Execute a shell command inside the configured workspace directory."""
    approved = await state.request_approval(
        "run_command", f"Command: {command}\nWorkspace: {state.workspace_dir}"
    )
    if not approved:
        await record_and_broadcast_log("run_command", command, "DENIED", "User rejected command")
        return "Error: Denied by user"

    res = await term.execute_bash(command)
    await record_and_broadcast_log("run_command", command, "SUCCESS", res[:500])
    return res


@mcp.tool()
async def check_task_status(task_id: str) -> str:
    """Check the real-time status and recent logs of a background command task."""
    res = term.check_task_status(task_id)
    await record_and_broadcast_log("check_task_status", f"task_id: {task_id}", "SUCCESS", res[:500])
    return res


@mcp.tool()
async def kill_task(task_id: str) -> str:
    """Terminate a running background command task."""
    res = term.kill_task(task_id)
    await record_and_broadcast_log("kill_task", f"task_id: {task_id}", "SUCCESS", res)
    return res


@mcp.tool()
async def read_workspace_image(
    filepath: str, mode: str = "auto"
) -> list[Image | str] | Image | str:
    """Load an image file from the workspace ('auto', 'image', or 'text' Base64 mode)."""
    try:
        raw_bytes = await asyncio.to_thread(vis.read_image_bytes, filepath)
        return await _format_image_response(
            tool_name="read_image",
            target_label=filepath,
            raw_bytes=raw_bytes,
            mode=mode,
            summary_prefix="Sent Image",
        )
    except (OSError, ValueError, RuntimeError) as err:
        await record_and_broadcast_log("read_image", filepath, "ERROR", str(err))
        return f"Error: {err}"


@mcp.tool()
async def list_active_windows() -> str:
    """List open desktop application windows with their titles, HWNDs, and process names."""
    try:
        windows = await asyncio.to_thread(vis.list_open_windows)
        if not windows:
            return "No open desktop application windows found."

        lines = [f"Found {len(windows)} open windows:"]
        for win in windows:
            min_tag = " [MINIMIZED]" if win["is_minimized"] else ""
            proc_tag = f" ({win['process_name']})" if win["process_name"] else ""
            lines.append(
                f"- HWND: {win['hwnd']} | Process: {proc_tag.strip() or 'N/A'} "
                f'| Title: "{win["title"]}"{min_tag}'
            )

        res = "\n".join(lines)
        await record_and_broadcast_log(
            "list_windows", "all", "SUCCESS", f"{len(windows)} windows found"
        )
        return res
    except (OSError, RuntimeError, ValueError) as err:
        await record_and_broadcast_log("list_windows", "all", "ERROR", str(err))
        return f"Error: {err}"


@mcp.tool()
async def switch_active_window(window_query: str) -> str:
    """Bring a specific application window to the foreground by HWND, title, or process."""
    try:
        win = await asyncio.to_thread(vis.find_window, window_query)
        if not win:
            return (
                f"Error: No window matching '{window_query}' "
                "(call list_active_windows to inspect open windows)."
            )

        ok = await asyncio.to_thread(vis.switch_to_window, win["hwnd"])
        status = "succeeded" if ok else "dispatched"
        msg = (
            f"Switched to window '{win['title']}' "
            f"(Process: {win['process_name']}, HWND: {win['hwnd']}) [{status}]"
        )
        await record_and_broadcast_log("switch_window", window_query, "SUCCESS", msg)
        return msg
    except (OSError, RuntimeError, ValueError) as err:
        await record_and_broadcast_log("switch_window", window_query, "ERROR", str(err))
        return f"Error: {err}"


@mcp.tool()
async def capture_window_screenshot(
    window_query: str, mode: str = "auto"
) -> list[Image | str] | Image | str:
    """Capture a screenshot cropped strictly to a specific application window."""
    try:
        raw_bytes, win_info = await asyncio.to_thread(
            vis.capture_window_bytes, window_query, switch_focus=True
        )
        summary = (
            f"Window '{win_info['title']}' "
            f"({win_info['rect']['width']}x{win_info['rect']['height']})"
        )
        return await _format_image_response(
            tool_name="capture_window",
            target_label=window_query,
            raw_bytes=raw_bytes,
            mode=mode,
            summary_prefix=summary,
        )
    except (OSError, RuntimeError, ValueError) as err:
        await record_and_broadcast_log("capture_window", window_query, "ERROR", str(err))
        return f"Error: {err}"


@mcp.tool()
async def take_desktop_screenshot(
    mode: str = "auto", window_query: Optional[str] = None
) -> list[Image | str] | Image | str:
    """Capture a live screenshot of the desktop or a specific window."""
    try:
        if window_query:
            return await capture_window_screenshot(window_query=window_query, mode=mode)

        raw_bytes = await asyncio.to_thread(vis.take_screenshot_bytes)
        return await _format_image_response(
            tool_name="take_screenshot",
            target_label="Desktop",
            raw_bytes=raw_bytes,
            mode=mode,
            summary_prefix="Sent Screenshot",
        )
    except (OSError, RuntimeError, ValueError) as err:
        await record_and_broadcast_log("take_screenshot", "Desktop Screen", "ERROR", str(err))
        return f"Error: {err}"


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
async def _format_image_response(
    tool_name: str,
    target_label: str,
    raw_bytes: bytes,
    mode: str,
    summary_prefix: str,
) -> list[Image | str] | Image | str:
    """Format image bytes according to MCP delivery mode and record audit telemetry."""
    img_obj = Image(data=raw_bytes, format="jpeg")
    if mode == "image":
        await record_and_broadcast_log(
            tool_name,
            f"{target_label} [image]",
            "SUCCESS",
            f"{summary_prefix} ({len(raw_bytes)} bytes)",
        )
        return img_obj

    b64_payload = vis.bytes_to_base64_payload(raw_bytes)
    if mode == "text":
        await record_and_broadcast_log(
            tool_name,
            f"{target_label} [text]",
            "SUCCESS",
            f"{summary_prefix} Base64 ({len(b64_payload)} chars)",
        )
        return b64_payload

    await record_and_broadcast_log(
        tool_name,
        f"{target_label} [auto]",
        "SUCCESS",
        f"{summary_prefix} Image + Base64 Fallback ({len(raw_bytes)} bytes)",
    )
    return [img_obj, b64_payload]


## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Exposed as library module imported by main.py.
