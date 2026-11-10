"""Integration tests for Web Dashboard state endpoints and user action APIs."""

import io
import unittest
from contextlib import redirect_stdout

from tests.integration.base import BaseIntegrationTestCase


class TestDashboardAPI(BaseIntegrationTestCase):
    def test_ui_state_endpoint(self):
        """Verify Dashboard UI state API returns configuration, logs, and AI breakdown stats."""
        # Test HTML dashboard serving from interfaces/ui
        res_ui = self.client.get("/ui")
        self.assertEqual(res_ui.status_code, 200)
        self.assertIn("AI Agent MCP Gateway", res_ui.text)

        # Test JSON state
        res = self.client.get("/api/ui/state")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("state", data)
        self.assertIn("logs", data)
        self.assertIn("ai_usage", data)
        self.assertIn("Gemini", data["ai_usage"])
        self.assertIn("Claude", data["ai_usage"])
        self.assertIn("ChatGPT", data["ai_usage"])

    def test_user_action_endpoints(self):
        """Verify that user action endpoints update state and log user action."""
        f = io.StringIO()
        with redirect_stdout(f):
            res = self.client.post(
                "/api/ui/permissions", json={"allow_write": True, "require_approval": True}
            )
        self.assertEqual(res.status_code, 200)
        out = f.getvalue()
        self.assertIn("[User Action]", out)

    def test_developer_traffic_endpoints(self):
        """Verify developer inspector traffic querying and clearing endpoints."""
        # Query traffic
        res = self.client.get("/api/ui/dev/traffic")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("traffic", data)
        self.assertIn("sessions", data)

        # Clear traffic
        f = io.StringIO()
        with redirect_stdout(f):
            res_clear = self.client.post("/api/ui/dev/clear")
        self.assertEqual(res_clear.status_code, 200)
        self.assertEqual(res_clear.json()["status"], "ok")
        self.assertIn("[User Action]", f.getvalue())

    def test_dashboard_rejects_cross_origin_and_forwarded_requests(self):
        """Verify local dashboard routes block cross-origin CSRF and reverse-proxy forwarded traffic (SA-03, NV-01)."""
        # 1. Cross-origin browser request to /api/ui/state or /api/ui/workspace must be blocked (403)
        res_csrf_read = self.client.get(
            "/api/ui/state", headers={"Origin": "https://evil.example.com"}
        )
        self.assertEqual(res_csrf_read.status_code, 403)

        res_csrf_write = self.client.post(
            "/api/ui/workspace",
            json={"path": "C:/"},
            headers={"Origin": "https://evil.example.com"},
        )
        self.assertEqual(res_csrf_write.status_code, 403)

        # 2. Reverse-proxy X-Forwarded-For from external IP must be blocked (403)
        res_forwarded = self.client.get(
            "/api/ui/state", headers={"X-Forwarded-For": "203.0.113.42"}
        )
        self.assertEqual(res_forwarded.status_code, 403)

        # 3. Same-origin localhost Origin header must remain allowed (200)
        res_local_origin = self.client.get(
            "/api/ui/state", headers={"Origin": "http://localhost:3000"}
        )
        self.assertEqual(res_local_origin.status_code, 200)


if __name__ == "__main__":
    unittest.main()
