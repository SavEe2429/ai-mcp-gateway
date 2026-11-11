"""Integration tests for IP ban management and external MCP client APIs."""

import unittest

from tests.integration.base import BaseIntegrationTestCase


class TestMCPClientAndBans(BaseIntegrationTestCase):
    """Verify security ban endpoints and external MCP client listing."""

    def test_banned_ips_api(self):
        """Verify manual IP ban, listing, and unban workflow."""
        res = self.client.post(
            "/api/ui/security/ban", json={"ip": "192.168.1.99", "duration": 3600}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(any(b["ip"] == "192.168.1.99" for b in data["bans"]))

        get_res = self.client.get("/api/ui/security/bans")
        self.assertEqual(get_res.status_code, 200)
        self.assertTrue(any(b["ip"] == "192.168.1.99" for b in get_res.json()["bans"]))

        unban_res = self.client.post("/api/ui/security/unban", json={"ip": "192.168.1.99"})
        self.assertEqual(unban_res.status_code, 200)
        self.assertFalse(any(b["ip"] == "192.168.1.99" for b in unban_res.json()["bans"]))

    def test_external_mcp_clients_api(self):
        """Verify external MCP client list endpoint returns servers key."""
        res = self.client.get("/api/ui/mcp-clients")
        self.assertEqual(res.status_code, 200)
        self.assertIn("servers", res.json())

    def test_parse_github_repo_url_security_validation(self):
        """Verify GitHub URL parsing rejects untrusted domains and injection names."""
        from ai_mcp_gateway.core.mcp_client_manager import _parse_github_repo_url

        owner, repo, subpath = _parse_github_repo_url("https://github.com/foo/bar.git")
        self.assertEqual((owner, repo, subpath), ("foo", "bar", ""))

        with self.assertRaises(ValueError):
            _parse_github_repo_url("https://evil.com/foo/bar")

        with self.assertRaises(ValueError):
            _parse_github_repo_url("https://github.com/-flag/repo")

        with self.assertRaises(ValueError):
            _parse_github_repo_url("https://github.com/owner/--upload-pack")

    def test_state_restores_banned_ips_from_db(self):
        """Verify AppState restores persisted IP bans from SQLite upon startup."""
        from ai_mcp_gateway.core.database import add_or_update_ban
        from ai_mcp_gateway.core.state import state

        test_ip = "198.51.100.42"
        add_or_update_ban(test_ip, reason="Bot Probe", duration_seconds=1200)

        # Clear in-memory state
        state.blocked_ips.pop(test_ip, None)
        state.banned_details.pop(test_ip, None)
        self.assertFalse(state.is_ip_blocked(test_ip))

        # Restore from DB
        state.load_banned_ips_from_db()
        self.assertTrue(state.is_ip_blocked(test_ip))
        self.assertIn(test_ip, state.banned_details)
        self.assertEqual(state.banned_details[test_ip]["reason"], "Bot Probe")


if __name__ == "__main__":
    unittest.main()
