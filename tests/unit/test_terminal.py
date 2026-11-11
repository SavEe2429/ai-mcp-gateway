"""Unit tests for terminal execution and auto-backgrounding functionality."""

import asyncio
import re
import sys
import unittest

import ai_mcp_gateway.tools.terminal as term
from ai_mcp_gateway.core.state import state
from ai_mcp_gateway.utils.config import get_config


class TestTerminalAutoBackground(unittest.IsolatedAsyncioTestCase):
    """Test terminal command execution and background transition."""

    async def asyncSetUp(self):
        state.allow_bash = True

    async def test_fast_command_runs_synchronously(self):
        """Verify fast commands complete and return output synchronously."""
        cmd = "echo HELLO_FAST_TASK"
        res = await term.execute_bash(cmd)
        self.assertIn("HELLO_FAST_TASK", res)
        self.assertIn("[Exit Code: 0]", res)

    async def test_slow_command_auto_backgrounds(self):
        """Verify long-running commands automatically transition to background tasks."""
        # Temporarily set timeout to 0.5s for this test
        cfg = get_config()
        original_timeout = cfg.session.terminal_timeout
        cfg.session.terminal_timeout = 0.5

        try:
            # Command sleeps for 2 seconds (exceeds 0.5s timeout)
            python_exe = sys.executable
            cmd = f'"{python_exe}" -c "import time; time.sleep(2); print(\'DONE_AFTER_2S\')"'
            res = await term.execute_bash(cmd)

            # Must return Auto-Background notice with Task ID
            self.assertIn("[Auto-Background]", res)
            self.assertIn("Task ID: task_", res)

            # Extract task ID
            match = re.search(r"Task ID:\s+(task_[a-zA-Z0-9]+)", res)
            self.assertIsNotNone(match)
            task_id = match.group(1)

            # Check status while running
            status_running = term.check_task_status(task_id)
            self.assertIn(task_id, status_running)

            # Wait for it to complete in background
            await asyncio.sleep(2.0)

            # Check status after completion
            status_done = term.check_task_status(task_id)
            self.assertIn("COMPLETED", status_done)
            self.assertIn("DONE_AFTER_2S", status_done)

        finally:
            cfg.session.terminal_timeout = original_timeout

    async def test_kill_running_background_task(self):
        """Verify background task can be terminated using kill_task."""
        cfg = get_config()
        original_timeout = cfg.session.terminal_timeout
        cfg.session.terminal_timeout = 0.5

        try:
            python_exe = sys.executable
            cmd = f'"{python_exe}" -c "import time; time.sleep(10)"'
            res = await term.execute_bash(cmd)

            match = re.search(r"Task ID:\s+(task_[a-zA-Z0-9]+)", res)
            self.assertIsNotNone(match)
            task_id = match.group(1)

            # Kill the task
            kill_res = term.kill_task(task_id)
            self.assertIn("KILLED", kill_res)

        finally:
            cfg.session.terminal_timeout = original_timeout

    def test_prune_background_tasks(self):
        """Verify _prune_background_tasks limits memory by evicting completed tasks."""
        from unittest.mock import MagicMock

        term.BACKGROUND_TASKS.clear()
        # Add 10 mock completed tasks
        for i in range(10):
            proc_mock = MagicMock()
            proc_mock.returncode = 0
            term.BACKGROUND_TASKS[f"task_{i}"] = {
                "process": proc_mock,
                "start_time": float(i),
            }

        term._prune_background_tasks(max_tasks=5)
        self.assertEqual(len(term.BACKGROUND_TASKS), 5)
        # Oldest tasks 0..4 should have been pruned
        self.assertNotIn("task_0", term.BACKGROUND_TASKS)
        self.assertIn("task_9", term.BACKGROUND_TASKS)

    async def test_sensitive_env_vars_filtered_from_subprocess(self):
        """Verify sensitive secrets and tokens are redacted from subprocess environment."""
        import os

        os.environ["MCP_CLIENT_SECRET"] = "super-secret-mcp-key"
        os.environ["GATEWAY_SECRET_KEY"] = "super-secret-gateway-key"
        os.environ["GITHUB_TOKEN"] = "ghp_secrettoken123"
        try:
            python_exe = sys.executable
            code = (
                "import os, json; "
                "keys = [k for k in ('MCP_CLIENT_SECRET', 'GATEWAY_SECRET_KEY', 'GITHUB_TOKEN') if k in os.environ]; "
                "print('LEAKED_KEYS:' + json.dumps(keys))"
            )
            cmd = f'"{python_exe}" -c "{code}"'
            res = await term.execute_bash(cmd)
            self.assertIn("LEAKED_KEYS:[]", res)
        finally:
            os.environ.pop("MCP_CLIENT_SECRET", None)
            os.environ.pop("GATEWAY_SECRET_KEY", None)
            os.environ.pop("GITHUB_TOKEN", None)


if __name__ == "__main__":
    unittest.main()
