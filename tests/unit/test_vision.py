"""Unit tests for vision and window management tools."""

import sys
import unittest
from unittest.mock import MagicMock, patch

import ai_mcp_gateway.tools.vision as vis
from ai_mcp_gateway.core.state import state


class TestVisionWindowManagement(unittest.TestCase):
    def setUp(self):
        state.allow_vision = True

    def test_find_window_by_hwnd(self):
        """Verify find_window matches by integer HWND or hex string."""
        mock_windows = [
            {
                "hwnd": 12345,
                "title": "Process Monitor - Sysinternals",
                "process_name": "Procmon64.exe",
                "pid": 9999,
                "is_minimized": False,
                "rect": {
                    "left": 0,
                    "top": 0,
                    "right": 800,
                    "bottom": 600,
                    "width": 800,
                    "height": 600,
                },
            },
            {
                "hwnd": 67890,
                "title": "Visual Studio Code",
                "process_name": "Code.exe",
                "pid": 8888,
                "is_minimized": True,
                "rect": {
                    "left": 100,
                    "top": 100,
                    "right": 900,
                    "bottom": 700,
                    "width": 800,
                    "height": 600,
                },
            },
        ]

        with patch("ai_mcp_gateway.tools.vision.list_open_windows", return_value=mock_windows):
            # Test match by integer HWND
            w1 = vis.find_window(12345)
            self.assertIsNotNone(w1)
            self.assertEqual(w1["hwnd"], 12345)

            # Test match by string HWND
            w2 = vis.find_window("12345")
            self.assertIsNotNone(w2)
            self.assertEqual(w2["hwnd"], 12345)

            # Test match by hex HWND
            w3 = vis.find_window(hex(12345))
            self.assertIsNotNone(w3)
            self.assertEqual(w3["hwnd"], 12345)

    def test_find_window_by_title_and_process_substring(self):
        """Verify find_window matches case-insensitive substrings like 'ProcMon'."""
        mock_windows = [
            {
                "hwnd": 12345,
                "title": "Process Monitor - Sysinternals: www.sysinternals.com",
                "process_name": "Procmon64.exe",
                "pid": 9999,
                "is_minimized": False,
                "rect": {
                    "left": 0,
                    "top": 0,
                    "right": 800,
                    "bottom": 600,
                    "width": 800,
                    "height": 600,
                },
            }
        ]

        with patch("ai_mcp_gateway.tools.vision.list_open_windows", return_value=mock_windows):
            # Partial title match
            self.assertEqual(vis.find_window("process monitor")["hwnd"], 12345)
            self.assertEqual(vis.find_window("Sysinternals")["hwnd"], 12345)

            # Process name match
            self.assertEqual(vis.find_window("procmon")["hwnd"], 12345)
            self.assertEqual(vis.find_window("procmon64.exe")["hwnd"], 12345)

            # Non-existent
            self.assertIsNone(vis.find_window("NonExistentWindow12345"))

    def test_switch_to_window(self):
        """Verify switch_to_window calls Win32 APIs when on Windows."""
        if sys.platform != "win32":
            return

        with patch("ai_mcp_gateway.tools.vision.user32") as mock_user32:
            mock_user32.IsIconic.return_value = 1
            mock_user32.SetForegroundWindow.return_value = 1
            mock_user32.ShowWindow.return_value = 1

            ret = vis.switch_to_window(12345)
            self.assertTrue(ret)
            mock_user32.ShowWindow.assert_called_with(12345, 9)  # SW_RESTORE
            mock_user32.SetForegroundWindow.assert_called_with(12345)

    def test_capture_window_bytes_disallowed(self):
        """Verify permission error is raised when allow_vision is False."""
        state.allow_vision = False
        with self.assertRaises(PermissionError):
            vis.capture_window_bytes("ProcMon")

    def test_capture_window_not_found(self):
        """Verify ValueError is raised if target window cannot be found."""
        with patch("ai_mcp_gateway.tools.vision.find_window", return_value=None):
            with self.assertRaises(ValueError):
                vis.capture_window_bytes("NonExistentWindow")

    def test_capture_window_success_mock(self):
        """Verify successful window capture returns JPEG bytes and updated window dict."""
        mock_win = {
            "hwnd": 12345,
            "title": "Process Monitor",
            "process_name": "procmon.exe",
            "pid": 1111,
            "is_minimized": False,
            "rect": {
                "left": 10,
                "top": 10,
                "right": 500,
                "bottom": 400,
                "width": 490,
                "height": 390,
            },
        }

        mock_mss_instance = MagicMock()
        mock_sct_img = MagicMock()
        mock_sct_img.size = (490, 390)
        # 490 * 390 * 4 bytes
        mock_sct_img.bgra = b"\x00" * (490 * 390 * 4)
        mock_mss_instance.__enter__.return_value.grab.return_value = mock_sct_img

        with (
            patch("ai_mcp_gateway.tools.vision.find_window", return_value=mock_win),
            patch("ai_mcp_gateway.tools.vision.switch_to_window", return_value=True),
            patch(
                "ai_mcp_gateway.tools.vision.get_accurate_window_rect",
                return_value=(10, 10, 500, 400),
            ),
            patch("mss.mss", return_value=mock_mss_instance),
            patch("time.sleep"),
        ):
            raw_bytes, win_info = vis.capture_window_bytes("ProcMon", switch_focus=True)
            self.assertIsInstance(raw_bytes, bytes)
            self.assertGreater(len(raw_bytes), 0)
            self.assertEqual(win_info["hwnd"], 12345)


if __name__ == "__main__":
    unittest.main()
