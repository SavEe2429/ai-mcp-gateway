"""Binary packaging script for AI Agent MCP Gateway using PyInstaller."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import argparse
import os
import sys
from pathlib import Path
from typing import List

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
# PyInstaller is imported lazily in run_packaging to provide a clean error message.

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
# Standalone packaging script does not import application runtime modules.

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
PACKAGE_NAME: str = "ai-mcp-gateway"
ENTRY_POINT: Path = ROOT_DIR / "src" / "ai_mcp_gateway" / "cli.py"
DIST_DIR: Path = ROOT_DIR / "out" / PACKAGE_NAME
BUILD_DIR: Path = ROOT_DIR / "build" / PACKAGE_NAME
HIDDEN_IMPORTS: tuple[str, ...] = (
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "mcp.server.fastmcp",
    "mcp.server.mcpserver",
    "mcp.server.transport_security",
    "mss",
    "PIL",
    "yaml",
)

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def run_packaging(mode: str = "onedir") -> None:
    """Compile the application into a standalone binary distribution."""
    try:
        import PyInstaller.__main__
    except ImportError:
        print("PyInstaller is not installed. Install via: uv sync --dev")
        sys.exit(1)

    print(f"Building {PACKAGE_NAME} in mode: {mode}...")
    args: List[str] = [
        str(ENTRY_POINT),
        f"--name={PACKAGE_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--paths={ROOT_DIR / 'src'}",
        "--clean",
        "--noconfirm",
    ]

    for hidden in HIDDEN_IMPORTS:
        args.append(f"--hidden-import={hidden}")

    ui_dir = ROOT_DIR / "src" / "ai_mcp_gateway" / "interfaces" / "ui"
    if ui_dir.exists():
        args.append(f"--add-data={ui_dir}{os.pathsep}ai_mcp_gateway/interfaces/ui")

    config_dir = ROOT_DIR / "config"
    if config_dir.exists():
        args.append(f"--add-data={config_dir}{os.pathsep}config")

    args.append("--onefile" if mode == "onefile" else "--onedir")

    print(f"Destination: {DIST_DIR}")
    PyInstaller.__main__.run(args)
    print(f"Successfully packaged {PACKAGE_NAME} into {DIST_DIR}")


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
def _parse_args() -> argparse.Namespace:
    """Parse CLI packaging options."""
    parser = argparse.ArgumentParser(description="Build binary packages")
    parser.add_argument(
        "--mode",
        choices=["onedir", "onefile"],
        default="onedir",
        help="Packaging mode: 'onedir' (directory bundle) or 'onefile' (single executable)",
    )
    return parser.parse_args()


## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
if __name__ == "__main__":
    cli_args = _parse_args()
    run_packaging(cli_args.mode)
