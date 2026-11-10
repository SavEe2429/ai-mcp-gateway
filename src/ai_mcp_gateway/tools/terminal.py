"""Terminal execution tool with automatic background task transition."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import asyncio
import os
import time
import uuid
from typing import Any, Dict, List

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.core.state import state
from ai_mcp_gateway.utils.config import get_config

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
BACKGROUND_TASKS: Dict[str, Dict[str, Any]] = {}
MAX_BACKGROUND_TASKS: int = 50
MAX_STREAM_BYTES: int = 2 * 1024 * 1024

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def decode_output(data: bytes) -> str:
    """Decode process byte streams to UTF-8 with Windows CP874 fallback."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp874", errors="replace")


async def execute_bash(command: str) -> str:
    """Execute terminal command with automatic background transition upon timeout."""
    if not state.allow_bash:
        return "Error: สิทธิ์การรันคำสั่ง Terminal ถูกปิดใช้งานอยู่"

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=state.workspace_dir,
            env=env,
        )

        stdout_chunks: List[bytes] = []
        stderr_chunks: List[bytes] = []

        stream_readers = asyncio.gather(
            _read_stream_into_chunks(proc.stdout, stdout_chunks),
            _read_stream_into_chunks(proc.stderr, stderr_chunks),
            proc.wait(),
        )

        cfg = get_config()
        wait_seconds = float(cfg.session.terminal_timeout)

        try:
            await asyncio.wait_for(asyncio.shield(stream_readers), timeout=wait_seconds)

            out_text = decode_output(b"".join(stdout_chunks)).strip()
            err_text = decode_output(b"".join(stderr_chunks)).strip()

            result = []
            if out_text:
                result.append(f"[STDOUT]\n{out_text}")
            if err_text:
                result.append(f"[STDERR]\n{err_text}")
            result.append(f"[Exit Code: {proc.returncode}]")

            return "\n\n".join(result)

        except asyncio.TimeoutError:
            _prune_background_tasks()
            task_id = f"task_{uuid.uuid4().hex[:6]}"
            start_time = time.time()

            BACKGROUND_TASKS[task_id] = {
                "task_id": task_id,
                "command": command,
                "pid": proc.pid,
                "process": proc,
                "stream_readers": stream_readers,
                "stdout_chunks": stdout_chunks,
                "stderr_chunks": stderr_chunks,
                "start_time": start_time,
            }

            return (
                f"[Auto-Background] คำสั่งทำงานเกิน {int(wait_seconds)} วินาที (1 นาที) "
                f"ระบบได้สลับคำสั่งนี้ไปทำงานเบื้องหลังอัตโนมัติเรียบร้อยแล้ว\n"
                f"- Task ID: {task_id}\n"
                f"- PID: {proc.pid}\n"
                f"- Command: {command}\n\n"
                f"คุณสามารถตรวจสอบผลลัพธ์หรือสถานะล่าสุดได้โดยเรียกเครื่องมือ: `check_task_status(task_id='{task_id}')`\n"
                f"หรือหากต้องการยกเลิกคำสั่ง ให้เรียก: `kill_task(task_id='{task_id}')`"
            )

    except (OSError, ValueError, RuntimeError) as err:
        return f"Error: {err}"


def check_task_status(task_id: str) -> str:
    """Check running or completed status and collected logs of a background task."""
    task = BACKGROUND_TASKS.get(task_id)
    if not task:
        return f"Error: ไม่พบ Task ID '{task_id}' ในระบบ"

    proc: asyncio.subprocess.Process = task["process"]
    is_running = proc.returncode is None
    elapsed = int(time.time() - task["start_time"])

    out_text = decode_output(b"".join(task["stdout_chunks"])).strip()
    err_text = decode_output(b"".join(task["stderr_chunks"])).strip()

    status_str = "RUNNING (กำลังทำงาน)" if is_running else "COMPLETED (เสร็จสิ้น)"
    result = [
        f"Task ID: {task_id}",
        f"Command: {task['command']}",
        f"PID: {task['pid']}",
        f"Status: {status_str}",
        f"Elapsed Time: {elapsed} วินาที",
    ]

    if not is_running:
        result.append(f"Exit Code: {proc.returncode}")

    if out_text:
        result.append(f"\n[STDOUT]\n{out_text}")
    if err_text:
        result.append(f"\n[STDERR]\n{err_text}")

    return "\n".join(result)


def kill_task(task_id: str) -> str:
    """Terminate and cancel a running background task."""
    task = BACKGROUND_TASKS.get(task_id)
    if not task:
        return f"Error: ไม่พบ Task ID '{task_id}' ในระบบ"

    proc: asyncio.subprocess.Process = task["process"]
    if proc.returncode is not None:
        return f"Task ID '{task_id}' สิ้นสุดการทำงานไปแล้ว (Exit Code: {proc.returncode})"

    try:
        proc.kill()
        return f"Task ID '{task_id}' (PID: {task['pid']}) ถูกสั่งยุติการทำงาน (KILLED) เรียบร้อยแล้ว"
    except ProcessLookupError:
        return f"Task ID '{task_id}' สิ้นสุดการทำงานไปแล้ว"
    except (OSError, RuntimeError) as err:
        return f"Error ไม่สามารถหยุด Task ได้: {err}"


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
def _prune_background_tasks(max_tasks: int = MAX_BACKGROUND_TASKS) -> None:
    """Prune oldest completed tasks to keep memory bounded."""
    if len(BACKGROUND_TASKS) < max_tasks:
        return

    completed = [tid for tid, t in BACKGROUND_TASKS.items() if t["process"].returncode is not None]
    completed.sort(key=lambda tid: BACKGROUND_TASKS[tid].get("start_time", 0))

    for tid in completed:
        if len(BACKGROUND_TASKS) <= max_tasks:
            break
        BACKGROUND_TASKS.pop(tid, None)


async def _read_stream_into_chunks(stream: asyncio.StreamReader, chunks: List[bytes]) -> None:
    """Read a byte stream continuously in background until EOF, respecting maximum buffer bounds."""
    total_bytes = 0
    truncated = False

    while True:
        data = await stream.read(4096)
        if not data:
            break
        total_bytes += len(data)
        if total_bytes <= MAX_STREAM_BYTES:
            chunks.append(data)
        elif not truncated:
            truncated = True
            chunks.append(b"\n[...Output capped at 2MB limit to prevent memory exhaustion...]\n")


## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Terminal execution tool module only.
