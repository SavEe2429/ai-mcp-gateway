"""Cross-platform single-instance OS file lock preventing duplicate gateway processes."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import os
import sys
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Optional

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.utils.config import get_lock_file

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
WIN_LOCK_OFFSET: int = 4096
METADATA_WIDTH: int = 256

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.


## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
class InstanceAlreadyRunningError(RuntimeError):
    """Raised when another AI MCP Gateway process already holds the single-instance lock."""

    def __init__(self, lock_path: Path, details: str = "") -> None:
        self.lock_path = lock_path
        self.details = details
        msg = f"Another AI MCP Gateway instance is already running (lock: {lock_path})"
        if details:
            msg = f"{msg} [{details}]"
        super().__init__(msg)


class SingleInstanceLock:
    """Manage an OS-enforced exclusive non-blocking lock file for the gateway process."""

    def __init__(self, lock_path: Optional[Path] = None) -> None:
        self.lock_path: Path = (lock_path or get_lock_file()).resolve()
        self._fd: Optional[int] = None

    def acquire(self, port: Optional[int] = None) -> None:
        """Acquire the exclusive process lock or raise InstanceAlreadyRunningError."""
        if self._fd is not None:
            return

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_RDWR
        fd = os.open(self.lock_path, flags, 0o600)
        try:
            if sys.platform == "win32":
                # Lock a dedicated byte beyond metadata so other processes can still read the PID.
                os.lseek(fd, WIN_LOCK_OFFSET, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as err:
            details = self._read_lock_details(fd)
            os.close(fd)
            raise InstanceAlreadyRunningError(self.lock_path, details=details) from err

        self._fd = fd
        self._write_metadata(port=port)

    def release(self) -> None:
        """Release the OS lock and remove the lock file if held."""
        if self._fd is None:
            return

        fd = self._fd
        self._fd = None
        try:
            if sys.platform == "win32":
                os.lseek(fd, WIN_LOCK_OFFSET, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

        try:
            self.lock_path.unlink(missing_ok=True)
        except OSError:
            pass

    def __enter__(self) -> "SingleInstanceLock":
        self.acquire()
        return self

    def __exit__(
        self,
        _exc_type: Optional[type[BaseException]],
        _exc_val: Optional[BaseException],
        _exc_tb: Optional[TracebackType],
    ) -> None:
        self.release()

    def _write_metadata(self, port: Optional[int] = None) -> None:
        """Write current PID and startup metadata at offset 0 without touching the lock byte."""
        if self._fd is None:
            return
        lines = [
            f"pid={os.getpid()}",
            f"started_at={datetime.now().isoformat(timespec='seconds')}",
        ]
        if port is not None:
            lines.append(f"port={port}")
        raw_payload = ("\n".join(lines) + "\n").encode("utf-8")
        padded = raw_payload[:METADATA_WIDTH].ljust(METADATA_WIDTH, b" ")
        try:
            os.lseek(self._fd, 0, os.SEEK_SET)
            os.write(self._fd, padded)
        except OSError:
            pass

    @staticmethod
    def _read_lock_details(fd: int) -> str:
        """Read existing lock metadata in one line for diagnostics."""
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            raw = os.read(fd, METADATA_WIDTH).decode("utf-8", errors="replace")
            parts = [line.strip() for line in raw.splitlines() if line.strip()]
            return ", ".join(parts)
        except OSError:
            return ""


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
# Exposed via SingleInstanceLock and InstanceAlreadyRunningError above.

## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Instance lock module only.
