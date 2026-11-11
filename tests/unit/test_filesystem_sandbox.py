"""Unit tests for workspace directory sandboxing and traversal protection."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import ai_mcp_gateway.tools.filesystem as fs
from ai_mcp_gateway.core.state import state


class TestFilesystemSandbox(unittest.TestCase):
    def setUp(self):
        old_ws = state.workspace_dir
        self.addCleanup(state.set_workspace, old_ws)
        state.set_workspace("./workspace")

    def test_filesystem_sandbox(self):
        """Verify workspace sandboxing protects parent directories."""
        safe = fs.safe_path("sample.txt")
        self.assertTrue(safe.startswith(os.path.realpath(state.workspace_dir)))

        # Attempt directory traversal
        with self.assertRaises((ValueError, PermissionError)):
            fs.safe_path("../../outside.txt")

    def test_symlink_or_junction_escape_rejected(self):
        """Verify symlinks or Windows directory junctions pointing outside workspace are rejected (SA-04)."""
        with tempfile.TemporaryDirectory() as temp_root:
            ws_dir = Path(temp_root) / "ws"
            outside_dir = Path(temp_root) / "outside"
            ws_dir.mkdir()
            outside_dir.mkdir()
            secret_file = outside_dir / "secret.txt"
            secret_file.write_text("top-secret", encoding="utf-8")

            link_path = ws_dir / "escape_link"
            created = False
            try:
                os.symlink(str(outside_dir), str(link_path), target_is_directory=True)
                created = True
            except OSError:
                if os.name == "nt":
                    proc = subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(link_path), str(outside_dir)],
                        capture_output=True,
                        text=True,
                    )
                    created = proc.returncode == 0

            self.assertTrue(created, "Expected symlink or junction creation to succeed in test")
            old_ws = state.workspace_dir
            try:
                state.set_workspace(str(ws_dir))
                with self.assertRaises(ValueError):
                    fs.safe_path("escape_link/secret.txt")
            finally:
                state.set_workspace(old_ws)

    def test_protected_gateway_data_and_env_files_blocked(self):
        """Verify gateway data/ secrets, database, and .env files remain blocked even at repo root."""
        old_ws = state.workspace_dir
        try:
            state.set_workspace(".")
            for blocked in ("data/client_secret.key", "data/gateway.db", ".env", ".env.local"):
                with self.assertRaises(ValueError):
                    fs.safe_path(blocked)
            # Example env template remains readable
            self.assertTrue(fs.safe_path(".env.example").endswith(".env.example"))
        finally:
            state.set_workspace(old_ws)


if __name__ == "__main__":
    unittest.main()
