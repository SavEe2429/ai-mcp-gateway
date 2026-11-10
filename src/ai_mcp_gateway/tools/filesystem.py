"""Sandboxed workspace filesystem operations with path-traversal protection."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import os

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.core.state import state

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
IGNORED_WORKSPACE_DIRS = frozenset(
    {".git", ".venv", "__pycache__", "node_modules", ".idea", ".vscode"}
)

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def safe_path(target_path: str) -> str:
    """Resolve real path and verify it stays strictly within state.workspace_dir."""
    base = os.path.realpath(state.workspace_dir)
    full_path = os.path.realpath(os.path.join(base, target_path))
    if os.path.commonpath([base, full_path]) != base:
        raise ValueError(f"Access denied: ไม่อนุญาตให้เข้าถึงไฟล์นอก Workspace ({target_path})")
    return full_path


def list_files(subdir: str = "") -> str:
    """List files inside the sandboxed workspace directory."""
    if not state.allow_read:
        return "Error: สิทธิ์การอ่านไฟล์ถูกปิดใช้งานอยู่"
    target = safe_path(subdir)
    if not os.path.exists(target):
        return f"Error: ไม่พบโฟลเดอร์ {subdir}"

    entries = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in IGNORED_WORKSPACE_DIRS]
        rel_root = os.path.relpath(root, state.workspace_dir)
        for filename in files:
            rel_file = os.path.join(rel_root, filename) if rel_root != "." else filename
            entries.append(rel_file)
    return "\n".join(entries) if entries else "โฟลเดอร์ว่างเปล่า"


def read_file(filepath: str) -> str:
    """Read UTF-8 content of a file inside the sandboxed workspace."""
    if not state.allow_read:
        return "Error: สิทธิ์การอ่านไฟล์ถูกปิดใช้งานอยู่"
    path = safe_path(filepath)
    if not os.path.isfile(path):
        return f"Error: ไม่พบไฟล์ {filepath}"
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def write_file(filepath: str, content: str) -> str:
    """Create or overwrite a file inside the sandboxed workspace."""
    if not state.allow_write:
        return "Error: สิทธิ์การเขียนไฟล์ถูกปิดใช้งานอยู่"
    path = safe_path(filepath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return f"บันทึกไฟล์ {filepath} สำเร็จ ({len(content)} ตัวอักษร)"


def patch_file(filepath: str, search_block: str, replace_block: str) -> str:
    """Replace the first occurrence of search_block with replace_block in a file."""
    if not state.allow_write:
        return "Error: สิทธิ์การแก้ไขไฟล์ถูกปิดใช้งานอยู่"
    path = safe_path(filepath)
    if not os.path.isfile(path):
        return f"Error: ไม่พบไฟล์ {filepath}"

    with open(path, "r", encoding="utf-8") as handle:
        content = handle.read()

    if search_block not in content:
        return "Error: ไม่พบบล็อกข้อความที่ต้องการแก้ไขในไฟล์ โปรดตรวจสอบเนื้อหาไฟล์อีกครั้ง"

    new_content = content.replace(search_block, replace_block, 1)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(new_content)
    return f"แก้ไขไฟล์ {filepath} เฉพาะจุดสำเร็จ"


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Filesystem tool module only.
