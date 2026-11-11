"""Screen capture, image encoding, and Windows desktop window inspection tools."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import base64
import ctypes
import io
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
import mss
from PIL import Image as PILImage

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.core.state import state
from ai_mcp_gateway.tools.filesystem import safe_path

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
user32 = ctypes.windll.user32 if sys.platform == "win32" else None
DEFAULT_WINDOW_MAX_SIZE: Tuple[int, int] = (1920, 1080)
DEFAULT_SCREENSHOT_MAX_SIZE: Tuple[int, int] = (1280, 1280)
DEFAULT_IMAGE_MAX_SIZE: Tuple[int, int] = (1280, 1280)
DEFAULT_WINDOW_JPEG_QUALITY: int = 85
DEFAULT_SCREENSHOT_JPEG_QUALITY: int = 80
DEFAULT_IMAGE_JPEG_QUALITY: int = 85

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.


## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
class RECT(ctypes.Structure):
    """Win32 RECT structure for DWM and GetWindowRect boundary queries."""

    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def get_accurate_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """Get accurate window bounds excluding invisible drop shadows (Windows 10/11 DWM)."""
    if sys.platform != "win32" or user32 is None:
        return 0, 0, 0, 0

    rect = RECT()
    try:
        dwmwa_extended_frame_bounds = 9
        res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(dwmwa_extended_frame_bounds),
            ctypes.byref(rect),
            ctypes.sizeof(rect),
        )
        if res == 0:
            return rect.left, rect.top, rect.right, rect.bottom
    except OSError, AttributeError, ctypes.ArgumentError:
        pass

    user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def list_open_windows() -> List[Dict[str, Any]]:
    """List all open, visible desktop windows with titles and process names."""
    if sys.platform != "win32" or user32 is None:
        return []

    windows: List[Dict[str, Any]] = []

    def _collect_window(hwnd: int) -> None:
        if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
            return
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if not title:
            return

        left, top, right, bottom = get_accurate_window_rect(hwnd)
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return

        pname, pid = _get_process_name_for_hwnd(hwnd)
        is_minimized = bool(user32.IsIconic(hwnd))

        windows.append(
            {
                "hwnd": int(hwnd),
                "title": title,
                "process_name": pname,
                "pid": pid,
                "is_minimized": is_minimized,
                "rect": {
                    "left": left,
                    "top": top,
                    "right": right,
                    "bottom": bottom,
                    "width": width,
                    "height": height,
                },
            }
        )

    wnd_enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _enum_callback(hwnd: int, _: Any) -> bool:
        _collect_window(hwnd)
        return True

    cb = wnd_enum_proc(_enum_callback)
    user32.EnumWindows(cb, 0)

    if not windows:
        try:
            hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if hdesk:
                user32.EnumDesktopWindows(hdesk, cb, 0)
                user32.CloseDesktop(hdesk)
        except OSError, AttributeError, ctypes.ArgumentError:
            pass

    return windows


def find_window(query: str | int) -> Optional[Dict[str, Any]]:
    """Find a target window by HWND, or partial match against title or process name."""
    windows = list_open_windows()
    if not windows:
        return None

    target_hwnd: Optional[int] = None
    if isinstance(query, int):
        target_hwnd = query
    elif isinstance(query, str) and (query.isdigit() or query.lower().startswith("0x")):
        try:
            target_hwnd = int(query, 16) if query.lower().startswith("0x") else int(query)
        except ValueError:
            target_hwnd = None

    if target_hwnd is not None:
        for win in windows:
            if win["hwnd"] == target_hwnd:
                return win

    query_lower = str(query).lower().strip()
    for win in windows:
        if query_lower == win["title"].lower() or query_lower == win["process_name"].lower():
            return win
    for win in windows:
        if query_lower in win["title"].lower():
            return win
    for win in windows:
        if query_lower in win["process_name"].lower():
            return win
    return None


def switch_to_window(hwnd: int) -> bool:
    """Bring the target window to the foreground, restoring it if minimized."""
    if sys.platform != "win32" or user32 is None:
        return False

    try:
        hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
            user32.CloseDesktop(hdesk)
    except OSError, AttributeError, ctypes.ArgumentError:
        pass

    sw_restore = 9
    sw_show = 5
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, sw_restore)
    else:
        user32.ShowWindow(hwnd, sw_show)

    vk_menu = 0x12
    keyeventf_keyup = 0x0002
    user32.keybd_event(vk_menu, 0, 0, 0)
    user32.keybd_event(vk_menu, 0, keyeventf_keyup, 0)

    res = user32.SetForegroundWindow(hwnd)
    return bool(res)


def capture_window_bytes(
    query: str | int, switch_focus: bool = True
) -> Tuple[bytes, Dict[str, Any]]:
    """Capture a screenshot of a specific application window."""
    if not state.allow_vision:
        raise PermissionError("สิทธิ์การจับภาพหน้าต่างถูกปิดใช้งานอยู่")

    win_info = find_window(query)
    if not win_info:
        raise ValueError(
            f"ไม่พบหน้าต่างที่ตรงกับ: '{query}' (ลองเรียก 'list_active_windows' เพื่อตรวจสอบรายชื่อหน้าต่าง)"
        )

    hwnd = win_info["hwnd"]
    if switch_focus:
        switch_to_window(hwnd)
        time.sleep(0.15)

    left, top, right, bottom = get_accurate_window_rect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        raise ValueError(f"ขนาดหน้าต่างไม่ถูกต้อง ({width}x{height})")

    win_info["rect"] = {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": width,
        "height": height,
    }

    with mss.mss() as sct:
        monitor = {"left": left, "top": top, "width": width, "height": height}
        sct_img = sct.grab(monitor)
        img = PILImage.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    img.thumbnail(DEFAULT_WINDOW_MAX_SIZE)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=DEFAULT_WINDOW_JPEG_QUALITY)
    return buffer.getvalue(), win_info


def capture_window_base64(
    query: str | int, switch_focus: bool = True
) -> Tuple[str, Dict[str, Any]]:
    """Capture a window screenshot and return Base64 payload plus window metadata."""
    raw, win_info = capture_window_bytes(query, switch_focus=switch_focus)
    return bytes_to_base64_payload(raw), win_info


def read_image_bytes(filepath: str) -> bytes:
    """Read and resize an image file inside the sandboxed workspace to JPEG bytes."""
    if not state.allow_vision:
        raise PermissionError("สิทธิ์การอ่านรูปภาพถูกปิดใช้งานอยู่")
    path = safe_path(filepath)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"ไม่พบไฟล์รูปภาพ: {filepath}")
    with PILImage.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail(DEFAULT_IMAGE_MAX_SIZE)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=DEFAULT_IMAGE_JPEG_QUALITY)
        return buffer.getvalue()


def bytes_to_base64_payload(raw: bytes) -> str:
    """Encode JPEG bytes into the gateway's Base64 transport string."""
    b64 = base64.b64encode(raw).decode("ascii")
    return f"IMAGE_BASE64_JPEG:{b64}"


def read_image_base64(filepath: str) -> str:
    """Read a workspace image file and return its Base64 payload."""
    raw = read_image_bytes(filepath)
    return bytes_to_base64_payload(raw)


def take_screenshot_bytes() -> bytes:
    """Capture the primary desktop monitor as JPEG bytes."""
    if not state.allow_vision:
        raise PermissionError("สิทธิ์การแคปหน้าจอถูกปิดใช้งานอยู่")
    with mss.mss() as sct:
        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        sct_img = sct.grab(monitor)
        img = PILImage.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        img.thumbnail(DEFAULT_SCREENSHOT_MAX_SIZE)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=DEFAULT_SCREENSHOT_JPEG_QUALITY)
        return buffer.getvalue()


def take_screenshot_base64() -> str:
    """Capture the primary desktop monitor and return its Base64 payload."""
    raw = take_screenshot_bytes()
    return bytes_to_base64_payload(raw)


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
def _get_process_name_for_hwnd(hwnd: int) -> Tuple[str, int]:
    """Retrieve executable name and PID for a window handle on Windows."""
    if sys.platform != "win32" or user32 is None:
        return "", 0

    try:
        import win32api
        import win32process

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid <= 0:
            return "", pid
        process_query_limited = 0x1000
        hproc = win32api.OpenProcess(process_query_limited, False, pid)
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_ulong(1024)
            if ctypes.windll.kernel32.QueryFullProcessImageNameW(
                int(hproc), 0, buf, ctypes.byref(size)
            ):
                return os.path.basename(buf.value), pid
        finally:
            win32api.CloseHandle(hproc)
    except ImportError, OSError, ValueError, RuntimeError:
        pass
    return "", 0


## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Vision and screen-capture tool module only.
