"""External MCP Client Manager.

Clones, configures, and runs external MCP servers from GitHub (Python or
Node.js) via stdio transport and exposes their tools through the gateway.
"""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import asyncio
import contextlib
import json
import logging
import os
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
from mcp import ClientSession, MCPError, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, ConfigDict

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.core.database import (
    delete_external_mcp,
    get_all_external_mcps,
    get_external_mcp,
    save_external_mcp,
    update_external_mcp_status,
)
from ai_mcp_gateway.utils.config import get_data_dir

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
LOGGER: logging.Logger = logging.getLogger(__name__)
TOOL_DISCOVERY_MAX_ATTEMPTS: int = 6
TOOL_DISCOVERY_INTERVAL_SECONDS: float = 0.5
STOP_TIMEOUT_SECONDS: float = 3.0
BASE_GATEWAY_INSTRUCTIONS: str = (
    "# AI MCP Gateway System Instructions\n\n"
    "You are connected to the user's local workspace and registered MCP integrations "
    "via the Model Context Protocol (MCP).\n\n"
    "## 1. Direct Tool Execution\n"
    "- When dedicated MCP tools are available for a service or application, call those "
    "MCP tools directly instead of writing ad-hoc shell scripts.\n\n"
    "## 2. Pre-Authorized Integrations\n"
    "- Tools exposed through this gateway operate inside user-configured permissions. "
    "Only request user intervention if a tool explicitly returns an error requiring it.\n\n"
    "## 3. Action-First Execution\n"
    "- Perform requested file, workspace, or integration actions directly through the "
    "available MCP tools rather than asking the user to perform them manually.\n"
)

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.


## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
class FlexibleModel(BaseModel):
    """Pydantic model allowing arbitrary kwargs without dropping extra fields."""

    model_config = ConfigDict(extra="allow")

    def model_dump_one_level(self) -> Dict[str, Any]:
        """Return a shallow dictionary representation of stored fields."""
        return dict(self)


class MCPClientInstance:
    """Represents a running external MCP server process and its ClientSession."""

    def __init__(self, mcp_id: str, config: Dict[str, Any]) -> None:
        self.id = mcp_id
        self.config = config
        self.session: Optional[ClientSession] = None
        self._exit_stack: Optional[contextlib.AsyncExitStack] = None
        self.task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._lock = asyncio.Lock()
        self.tools: List[Dict[str, Any]] = []
        self.is_running = False

    async def start(self) -> None:
        """Start the stdio process and initialize the MCP ClientSession."""
        async with self._lock:
            if self.is_running or (self.task and not self.task.done()):
                LOGGER.info("MCP Client [%s] is already running or starting.", self.id)
                return

            server_params = _build_stdio_params(self.config)
            LOGGER.info(
                "Starting MCP Client [%s]: %s %s",
                self.id,
                server_params.command,
                " ".join(server_params.args),
            )

            ready_event = asyncio.Event()
            start_error: List[Exception] = []

            async def _client_runner() -> None:
                self._exit_stack = contextlib.AsyncExitStack()
                try:
                    read_stream, write_stream = await self._exit_stack.enter_async_context(
                        stdio_client(server_params)
                    )
                    self.session = await self._exit_stack.enter_async_context(
                        ClientSession(read_stream, write_stream)
                    )
                    await self.session.initialize()

                    tools_result = await self._discover_tools()
                    self.tools = [
                        {
                            "name": tool.name,
                            "description": tool.description or "",
                            "inputSchema": getattr(
                                tool, "inputSchema", getattr(tool, "input_schema", {})
                            ),
                        }
                        for tool in tools_result.tools
                    ]

                    self.is_running = True
                    self._stop_event = asyncio.Event()
                    update_external_mcp_status(
                        self.id,
                        status="RUNNING",
                        tools_json=json.dumps(self.tools, ensure_ascii=False),
                        error_message="",
                    )
                    LOGGER.info(
                        "MCP Client [%s] connected with %d tools.", self.id, len(self.tools)
                    )
                    ready_event.set()
                    await self._stop_event.wait()
                except asyncio.CancelledError:
                    pass
                except (OSError, RuntimeError, ValueError, MCPError, TimeoutError) as err:
                    self.is_running = False
                    err_msg = str(err)
                    LOGGER.error("Failed to start MCP Client [%s]: %s", self.id, err_msg)
                    update_external_mcp_status(self.id, status="ERROR", error_message=err_msg)
                    start_error.append(err)
                    ready_event.set()
                finally:
                    self.is_running = False
                    if self._exit_stack:
                        try:
                            await self._exit_stack.aclose()
                        except (OSError, RuntimeError) as err:
                            LOGGER.debug("Ignoring exit stack close error for %s: %s", self.id, err)
                        self._exit_stack = None
                        self.session = None

            self.task = asyncio.create_task(_client_runner())
            await ready_event.wait()
            if start_error:
                raise start_error[0]

    async def _discover_tools(self) -> Any:
        """Query tools from the connected session with brief retry for lazy initializers."""
        assert self.session is not None
        tools_result = await self.session.list_tools()
        for attempt in range(TOOL_DISCOVERY_MAX_ATTEMPTS):
            if tools_result.tools:
                break
            LOGGER.info(
                "MCP Client [%s] waiting for external tools (attempt %d/%d)...",
                self.id,
                attempt + 1,
                TOOL_DISCOVERY_MAX_ATTEMPTS,
            )
            await asyncio.sleep(TOOL_DISCOVERY_INTERVAL_SECONDS)
            tools_result = await self.session.list_tools()
        return tools_result

    async def stop(self) -> None:
        """Stop the client session and terminate the subprocess cleanly."""
        async with self._lock:
            if not self.is_running and not self.task:
                return

            self.is_running = False
            if self._stop_event:
                self._stop_event.set()
            if self.task and not self.task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(self.task), timeout=STOP_TIMEOUT_SECONDS)
                except asyncio.TimeoutError, asyncio.CancelledError, RuntimeError:
                    self.task.cancel()
                    try:
                        await self.task
                    except asyncio.CancelledError, RuntimeError:
                        pass

            self.task = None
            self.session = None
            self._stop_event = None
            update_external_mcp_status(self.id, status="STOPPED")
            LOGGER.info("MCP Client [%s] stopped.", self.id)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Invoke a tool on the active external MCP session."""
        if not self.is_running or not self.session:
            raise RuntimeError(f"MCP Server '{self.id}' is not running.")
        return await self.session.call_tool(tool_name, arguments)


class MCPClientManager:
    """Manages lifecycle, installation, and gateway registration of external MCP servers."""

    def __init__(self, mcp_server: Any = None) -> None:
        self.mcp_server = mcp_server
        self.instances: Dict[str, MCPClientInstance] = {}
        self.mcp_dir = Path(get_data_dir()) / "mcp_servers"
        self.mcp_dir.mkdir(parents=True, exist_ok=True)
        self.tool_routes: Dict[str, Tuple[str, str]] = {}

    def set_mcp_server(self, mcp_server: Any) -> None:
        """Attach the FastMCP/MCPServer instance used to expose bridged tools."""
        self.mcp_server = mcp_server

    async def load_installed_servers(self) -> None:
        """Load and auto-start persisted external MCP servers from SQLite."""
        servers = get_all_external_mcps()
        for server_cfg in servers:
            if server_cfg.get("status") not in ("RUNNING", "INSTALLED", "STOPPED"):
                continue
            try:
                inst = MCPClientInstance(server_cfg["id"], server_cfg)
                self.instances[server_cfg["id"]] = inst
                await inst.start()
                if server_cfg.get("expose_to_server", 1):
                    self._register_tools_to_gateway(inst)
            except (OSError, RuntimeError, ValueError, MCPError, TimeoutError) as err:
                LOGGER.warning("Could not auto-start external MCP %s: %s", server_cfg["name"], err)

    async def install_from_github(
        self,
        github_url: str,
        env_vars: Optional[Dict[str, str]] = None,
        custom_command: Optional[str] = None,
        custom_args: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Clone repository from GitHub, detect runtime, save config, and start client."""
        owner, repo, subpath = _parse_github_repo_url(github_url)
        server_id = f"{owner}_{repo}".lower().replace("-", "_")
        if subpath:
            server_id += f"_{subpath.replace('/', '_')}"

        clone_dir = self.mcp_dir / f"{owner}_{repo}"
        work_dir = clone_dir / subpath if subpath else clone_dir

        if not clone_dir.exists():
            await _clone_github_repo(owner, repo, clone_dir)

        runtime, command, args = await _detect_and_prepare_runtime(
            work_dir=work_dir,
            custom_command=custom_command,
            custom_args=custom_args,
        )

        config_dict: Dict[str, Any] = {
            "id": server_id,
            "name": f"{owner}/{repo}",
            "repo_url": github_url,
            "install_path": str(work_dir),
            "runtime": runtime,
            "command": command,
            "args": args,
            "env_vars": json.dumps(env_vars or {}, ensure_ascii=False),
            "status": "INSTALLED",
            "expose_to_server": True,
        }
        save_external_mcp(config_dict)

        if server_id in self.instances:
            await self.instances[server_id].stop()

        inst = MCPClientInstance(server_id, config_dict)
        self.instances[server_id] = inst
        await inst.start()
        self._register_tools_to_gateway(inst)
        return get_external_mcp(server_id) or config_dict

    async def toggle_server(self, server_id: str, enable: bool) -> Dict[str, Any]:
        """Enable or disable an external MCP server by ID."""
        inst = self.instances.get(server_id)
        if not inst:
            mcp_info = get_external_mcp(server_id)
            if not mcp_info:
                raise ValueError(f"External MCP server not found: {server_id}")
            inst = MCPClientInstance(server_id, mcp_info)
            self.instances[server_id] = inst

        if enable:
            if not inst.is_running:
                await inst.start()
                if inst.config.get("expose_to_server", 1):
                    self._register_tools_to_gateway(inst)
        elif inst.is_running:
            self._unregister_tools_from_gateway(inst)
            await inst.stop()

        return get_external_mcp(server_id) or inst.config

    async def uninstall(self, server_id: str) -> None:
        """Stop, unregister, and remove an installed external MCP server."""
        inst = self.instances.pop(server_id, None)
        if inst:
            self._unregister_tools_from_gateway(inst)
            await inst.stop()

        mcp_info = get_external_mcp(server_id)
        if mcp_info:
            path_str = mcp_info.get("install_path")
            if path_str and os.path.exists(path_str):
                try:
                    shutil.rmtree(path_str, ignore_errors=True)
                except OSError as err:
                    LOGGER.debug("Failed to remove %s: %s", path_str, err)

        delete_external_mcp(server_id)

    async def shutdown(self) -> None:
        """Shutdown all running MCP clients on gateway termination."""
        for inst in list(self.instances.values()):
            try:
                self._unregister_tools_from_gateway(inst)
                await inst.stop()
            except (OSError, RuntimeError, MCPError) as err:
                LOGGER.warning("Error stopping external MCP %s: %s", inst.id, err)
        self.instances.clear()

    def _register_tools_to_gateway(self, instance: MCPClientInstance) -> None:
        """Register bridged tools from an external MCP instance onto the gateway server."""
        if not self.mcp_server:
            return

        clean_name = _normalize_server_prefix(instance.config.get("name", instance.id))
        inst_title = instance.config.get("name", instance.id)

        for tool_info in instance.tools:
            orig_name = tool_info["name"]
            gateway_tool_name = f"{clean_name}__{orig_name}"
            self.tool_routes[gateway_tool_name] = (instance.id, orig_name)
            desc = (f"[External: {inst_title}] {tool_info.get('description', '')}").strip()

            runner_fn = self._create_tool_runner(instance.id, orig_name)
            runner_fn.__name__ = gateway_tool_name
            runner_fn.__doc__ = desc

            try:
                if hasattr(self.mcp_server, "add_tool"):
                    self.mcp_server.add_tool(
                        runner_fn,
                        name=gateway_tool_name,
                        description=desc,
                    )
                    self._apply_original_schema(gateway_tool_name, tool_info.get("inputSchema"))
            except (RuntimeError, ValueError, TypeError) as err:
                LOGGER.warning("Error bridging tool %s: %s", gateway_tool_name, err)

        self._update_gateway_instructions()

    def _create_tool_runner(self, inst_id: str, tool_name: str):
        """Create an async proxy callable forwarding calls to the external session."""

        async def _runner(**kwargs: Any) -> str:
            inst = self.instances.get(inst_id)
            if not inst or not inst.is_running:
                return f"Error: MCP Server '{inst_id}' is offline."
            try:
                res = await inst.call_tool(tool_name, kwargs)
                return _format_tool_call_result(res)
            except (RuntimeError, ValueError, OSError, MCPError) as err:
                return f"Error executing external tool '{tool_name}': {err}"

        return _runner

    def _apply_original_schema(self, gateway_tool_name: str, orig_schema: Any) -> None:
        """Preserve the external tool's JSON inputSchema on FastMCP's tool manager."""
        tool_mgr = getattr(self.mcp_server, "_tool_manager", None)
        if not tool_mgr:
            return
        tool_obj = tool_mgr.get_tool(gateway_tool_name)
        if not tool_obj:
            return
        tool_obj.fn_metadata.arg_model = FlexibleModel
        if isinstance(orig_schema, dict) and orig_schema:
            tool_obj.parameters = orig_schema

    def _unregister_tools_from_gateway(self, instance: MCPClientInstance) -> None:
        """Remove bridged tools of a stopped or uninstalled external server."""
        if not self.mcp_server:
            return
        clean_name = _normalize_server_prefix(instance.config.get("name", instance.id))
        for tool_info in instance.tools:
            gateway_tool_name = f"{clean_name}__{tool_info['name']}"
            self.tool_routes.pop(gateway_tool_name, None)
            try:
                if hasattr(self.mcp_server, "remove_tool"):
                    self.mcp_server.remove_tool(gateway_tool_name)
            except RuntimeError, KeyError, ValueError:
                pass

        self._update_gateway_instructions()

    def _update_gateway_instructions(self) -> None:
        """Update MCP server system instructions based on currently running integrations."""
        if not self.mcp_server:
            return

        external_sections: List[str] = []
        for inst in self.instances.values():
            if not inst.is_running:
                continue
            name = inst.config.get("name", inst.id)
            clean_id = _normalize_server_prefix(name)
            external_sections.append(
                f"\n## {name} Integration (ACTIVE)\n"
                f"- Connected with {len(inst.tools)} tools using prefix `{clean_id}__*`.\n"
            )

        full_instructions = BASE_GATEWAY_INSTRUCTIONS + "".join(external_sections)
        lowlevel = getattr(self.mcp_server, "_lowlevel_server", None)
        if lowlevel and hasattr(lowlevel, "instructions"):
            lowlevel.instructions = full_instructions
        elif hasattr(self.mcp_server, "instructions"):
            try:
                self.mcp_server.instructions = full_instructions
            except AttributeError, TypeError:
                pass


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
# Exposed through the module-level `client_manager` singleton below.


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
def _normalize_server_prefix(name: str) -> str:
    """Normalize a repository or server name into an SEP-986 compliant tool prefix."""
    return name.replace("/", "_").replace("-", "_").lower()


def _format_tool_call_result(res: Any) -> str:
    """Convert an MCP CallToolResult into a readable text response."""
    parts: List[str] = []
    for content in getattr(res, "content", []):
        if hasattr(content, "text"):
            parts.append(content.text)
        else:
            parts.append(str(content))
    return "\n".join(parts) if parts else str(res)


def _build_stdio_params(config: Dict[str, Any]) -> StdioServerParameters:
    """Build StdioServerParameters from a persisted external MCP configuration."""
    command = config.get("command", "")
    args_str = config.get("args", "")
    install_path = config.get("install_path", "")
    env_vars_raw = config.get("env_vars", "{}")

    try:
        extra_env = json.loads(env_vars_raw) if isinstance(env_vars_raw, str) else env_vars_raw
    except json.JSONDecodeError:
        extra_env = {}

    env = os.environ.copy()
    if isinstance(extra_env, dict):
        for key, value in extra_env.items():
            env[str(key)] = str(value)

    args = [arg.strip() for arg in args_str.split() if arg.strip()] if args_str else []
    return StdioServerParameters(
        command=command,
        args=args,
        env=env,
        cwd=install_path if os.path.exists(install_path) else None,
    )


def _parse_github_repo_url(github_url: str) -> Tuple[str, str, str]:
    """Extract (owner, repo, subpath) from a GitHub repository URL."""
    parsed = urlparse(github_url.strip())
    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(path_parts) < 2:
        raise ValueError(
            f"Invalid GitHub URL: {github_url}. Must be in format https://github.com/owner/repo"
        )
    owner = path_parts[0]
    repo = path_parts[1].replace(".git", "")
    subpath = "/".join(path_parts[4:]) if len(path_parts) > 4 and path_parts[2] == "tree" else ""
    return owner, repo, subpath


async def _clone_github_repo(owner: str, repo: str, clone_dir: Path) -> None:
    """Shallow-clone a GitHub repository into clone_dir."""
    repo_clone_url = f"https://github.com/{owner}/{repo}.git"
    proc = await asyncio.create_subprocess_exec(
        "git",
        "clone",
        "--depth",
        "1",
        repo_clone_url,
        str(clone_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Git clone failed: {stderr.decode(errors='replace')}")


async def _detect_and_prepare_runtime(
    work_dir: Path,
    custom_command: Optional[str],
    custom_args: Optional[str],
) -> Tuple[str, str, str]:
    """Detect Node.js or Python runtime and return (runtime, command, args)."""
    command = (custom_command or "").strip()
    args = (custom_args or "").strip()
    if command:
        return "python", command, args

    package_json = work_dir / "package.json"
    pyproject = work_dir / "pyproject.toml"
    requirements = work_dir / "requirements.txt"

    if package_json.exists():
        return await _prepare_node_runtime(work_dir, package_json)
    if pyproject.exists() or requirements.exists() or any(work_dir.glob("*.py")):
        return _prepare_python_runtime(work_dir, pyproject)
    return "python", "uv", f"run --directory {work_dir} python main.py"


async def _prepare_node_runtime(work_dir: Path, package_json: Path) -> Tuple[str, str, str]:
    """Install Node.js dependencies and resolve the server entrypoint."""
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        npm_install = await asyncio.create_subprocess_exec(
            npm_cmd,
            "install",
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await npm_install.communicate()
    except OSError as err:
        LOGGER.warning("npm install error in %s: %s", work_dir, err)

    try:
        pkg_data = json.loads(package_json.read_text(encoding="utf-8"))
        bin_field = pkg_data.get("bin")
        first_bin = next(iter(bin_field.values())) if isinstance(bin_field, dict) else bin_field
        if isinstance(first_bin, str) and (work_dir / first_bin).exists():
            return "node", "node", str(work_dir / first_bin)
        main_file = pkg_data.get("main", "index.js")
        return "node", "node", str(work_dir / main_file)
    except OSError, json.JSONDecodeError, StopIteration:
        return "node", "node", str(work_dir / "index.js")


def _prepare_python_runtime(work_dir: Path, pyproject: Path) -> Tuple[str, str, str]:
    """Resolve Python entrypoint command for a cloned MCP server."""
    if pyproject.exists():
        try:
            pyproj_data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            scripts = pyproj_data.get("project", {}).get("scripts", {})
            if scripts:
                script_name = next(iter(scripts.keys()))
                return "python", "uv", f"run --directory {work_dir} {script_name}"
        except OSError, tomllib.TOMLDecodeError, StopIteration:
            pass

    for candidate in ("src/server.py", "server.py", "main.py", "src/main.py", "__main__.py"):
        if (work_dir / candidate).exists():
            return "python", "uv", f"run --directory {work_dir} python {candidate}"

    py_files = [p for p in work_dir.glob("*.py") if p.name not in ("install.py", "setup.py")]
    target_file = py_files[0].name if py_files else "main.py"
    return "python", "uv", f"run --directory {work_dir} python {target_file}"


## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
client_manager: MCPClientManager = MCPClientManager()
