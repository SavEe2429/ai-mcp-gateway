"""Unit tests for SQLite audit logging, token storage, and AI usage counters."""

import unittest

from ai_mcp_gateway.core.database import (
    clear_logs,
    get_ai_usage_stats,
    get_recent_logs,
    get_token_client,
    log_activity,
    save_token,
)


class TestDatabaseAndAudit(unittest.TestCase):
    def setUp(self):
        clear_logs()

    def test_database_logging_and_stats(self):
        """Verify activity logging, provider breakdown, and log clearing."""
        log_activity("list_files", ".", "SUCCESS", "ok", client_name="Gemini")
        log_activity("read_file", "test.py", "SUCCESS", "ok", client_name="Claude")
        log_activity("run_command", "dir", "SUCCESS", "ok", client_name="ChatGPT")

        recent = get_recent_logs(10)
        self.assertEqual(len(recent), 3)

        stats = get_ai_usage_stats()
        self.assertEqual(stats["Gemini"], 1)
        self.assertEqual(stats["Claude"], 1)
        self.assertEqual(stats["ChatGPT"], 1)
        self.assertEqual(stats["Total"], 3)

        # Clear logs
        clear_logs()
        cleared_stats = get_ai_usage_stats()
        self.assertEqual(cleared_stats["Total"], 0)

    def test_log_activity_timestamp(self):
        """Verify log_activity records local timestamp correctly."""
        from datetime import datetime

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_activity("list_files", ".", "SUCCESS", "ok", client_name="Gemini")
        recent = get_recent_logs(1)
        self.assertEqual(len(recent), 1)
        # Check that stored timestamp matches date and hour/minute of local time
        self.assertEqual(recent[0]["timestamp"][:16], now_str[:16])

        # Test explicit timestamp
        custom_ts = "2026-11-07 14:30:00"
        log_activity("write_file", "test.txt", "SUCCESS", "ok", timestamp=custom_ts)
        recent = get_recent_logs(1)
        self.assertEqual(recent[0]["timestamp"], custom_ts)

    def test_token_client_binding(self):
        """Verify tokens can be saved with associated client names and retrieved."""
        save_token("test-token-123", client_name="Claude")
        self.assertEqual(get_token_client("test-token-123"), "Claude")

        save_token("test-token-456", client_name="ChatGPT")
        self.assertEqual(get_token_client("test-token-456"), "ChatGPT")

    def test_token_expiration_and_revocation(self):
        """Verify tokens expire according to TTL and can be explicitly revoked (SA-05)."""
        from ai_mcp_gateway.core.database import revoke_token, verify_token

        save_token("short-lived-token", client_name="Gemini")
        self.assertTrue(verify_token("short-lived-token", max_age_seconds=3600))
        self.assertFalse(verify_token("short-lived-token", max_age_seconds=-1))

        save_token("revocable-token", client_name="Claude")
        self.assertTrue(verify_token("revocable-token"))
        revoke_token("revocable-token")
        self.assertFalse(verify_token("revocable-token"))

    def test_cleanup_expired_tokens(self):
        """Verify cleanup_expired_tokens purges expired entries."""
        from ai_mcp_gateway.core.database import cleanup_expired_tokens, verify_token

        save_token("to-be-cleaned", client_name="Gemini")
        self.assertTrue(verify_token("to-be-cleaned", max_age_seconds=3600))
        # Purge tokens older than -1 seconds (i.e. all existing)
        deleted = cleanup_expired_tokens(max_age_seconds=-1)
        self.assertGreaterEqual(deleted, 1)
        self.assertFalse(verify_token("to-be-cleaned"))


if __name__ == "__main__":
    unittest.main()
