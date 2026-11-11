"""Unit tests for single-instance OS file lock and duplicate launch prevention."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_mcp_gateway.core.instance_lock import InstanceAlreadyRunningError, SingleInstanceLock
from ai_mcp_gateway.main import run_server


class TestSingleInstanceLock(unittest.TestCase):
    def test_single_instance_lock_prevents_concurrent_acquire(self):
        """Verify second SingleInstanceLock fails while first lock is held and succeeds after release."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_path = Path(tmp_dir) / "gateway.lock"
            lock1 = SingleInstanceLock(lock_path=lock_path)
            lock2 = SingleInstanceLock(lock_path=lock_path)

            lock1.acquire(port=3000)
            self.assertTrue(lock_path.is_file())
            try:
                with self.assertRaises(InstanceAlreadyRunningError) as ctx:
                    lock2.acquire(port=3000)
                self.assertIn(f"pid={os.getpid()}", ctx.exception.details)
            finally:
                lock1.release()

            self.assertFalse(lock_path.exists())
            lock2.acquire(port=3000)
            lock2.release()
            self.assertFalse(lock_path.exists())

    def test_run_server_exits_when_lock_already_held(self):
        """Verify run_server exits cleanly with code 1 when another instance holds the lock."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_path = Path(tmp_dir) / "gateway.lock"
            active_lock = SingleInstanceLock(lock_path=lock_path)
            active_lock.acquire(port=3000)
            try:
                with patch.dict(os.environ, {"GATEWAY_LOCK_FILE": str(lock_path)}):
                    with self.assertRaises(SystemExit) as ctx:
                        run_server()
                self.assertEqual(ctx.exception.code, 1)
            finally:
                active_lock.release()


if __name__ == "__main__":
    unittest.main()
