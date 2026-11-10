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


if __name__ == "__main__":
    unittest.main()
