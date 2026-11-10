"""Unit tests for log filtering suppressing repetitive polling noise."""

import logging
import unittest

from ai_mcp_gateway.main import PollingAccessLogFilter


class TestLoggingFilters(unittest.TestCase):
    def test_polling_access_log_filter(self):
        """Verify that polling and static endpoints are silenced while user actions pass."""
        log_filter = PollingAccessLogFilter()
        logger = logging.getLogger("test.uvicorn.access")

        # Polling requests must be filtered (return False)
        rec_poll_state = logger.makeRecord(
            "test.uvicorn.access",
            logging.INFO,
            "main.py",
            1,
            "%s - %s %s %s %d",
            ("127.0.0.1", "GET", "/api/ui/state", "1.1", 200),
            None,
        )
        rec_poll_files = logger.makeRecord(
            "test.uvicorn.access",
            logging.INFO,
            "main.py",
            1,
            "%s - %s %s %s %d",
            ("127.0.0.1", "GET", "/api/ui/files", "1.1", 200),
            None,
        )
        self.assertFalse(log_filter.filter(rec_poll_state))
        self.assertFalse(log_filter.filter(rec_poll_files))

        # User actions and AI requests must pass (return True)
        rec_user_action = logger.makeRecord(
            "test.uvicorn.access",
            logging.INFO,
            "main.py",
            1,
            "%s - %s %s %s %d",
            ("127.0.0.1", "POST", "/api/ui/workspace", "1.1", 200),
            None,
        )
        rec_ai_action = logger.makeRecord(
            "test.uvicorn.access",
            logging.INFO,
            "main.py",
            1,
            "%s - %s %s %s %d",
            ("127.0.0.1", "POST", "/mcp", "1.1", 200),
            None,
        )
        self.assertTrue(log_filter.filter(rec_user_action))
        self.assertTrue(log_filter.filter(rec_ai_action))

    def test_client_name_extraction(self):
        """Verify client normalization maps GPT/OpenAI, Claude, and Gemini correctly."""
        from ai_mcp_gateway.interfaces.middleware import extract_client_name

        self.assertEqual("ChatGPT", extract_client_name("gpt"))
        self.assertEqual("ChatGPT", extract_client_name("gpt-4o"))
        self.assertEqual("ChatGPT", extract_client_name("Custom-GPT"))
        self.assertEqual("ChatGPT", extract_client_name("OpenAI Client"))
        self.assertEqual("Claude", extract_client_name("Claude Desktop"))
        self.assertEqual("Gemini", extract_client_name("Google Gemini"))
        self.assertEqual("Cursor", extract_client_name("Cursor Agent"))
        self.assertEqual("AI Agent", extract_client_name(""))

    def test_scanner_noise_filtered(self):
        """Verify vulnerability scanner probe requests are silenced from access log."""
        log_filter = PollingAccessLogFilter()
        logger = logging.getLogger("test.uvicorn.access")

        rec_wp = logger.makeRecord(
            "test.uvicorn.access",
            logging.INFO,
            "main.py",
            1,
            "%s - %s %s %s %d",
            ("195.178.110.94", "GET", "/wp-config.php", "1.1", 404),
            None,
        )
        rec_secrets = logger.makeRecord(
            "test.uvicorn.access",
            logging.INFO,
            "main.py",
            1,
            "%s - %s %s %s %d",
            ("195.178.110.94", "GET", "/user_secrets.yml", "1.1", 404),
            None,
        )
        self.assertFalse(log_filter.filter(rec_wp))
        self.assertFalse(log_filter.filter(rec_secrets))


if __name__ == "__main__":
    unittest.main()
