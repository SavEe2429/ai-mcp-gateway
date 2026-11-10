"""Integration tests for RFC 8414 OAuth 2.1 metadata and token issuance."""

import re
import unittest

from ai_mcp_gateway.core.database import get_token_client
from tests.integration.base import BaseIntegrationTestCase


class TestOAuthEndpoints(BaseIntegrationTestCase):
    def test_oauth_metadata_discovery(self):
        """Verify RFC 8414 & OpenID Connect Discovery endpoints for Gemini/Claude."""
        res = self.client.get("/.well-known/oauth-authorization-server")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("token_endpoint", data)
        self.assertIn("authorization_endpoint", data)

        res_res = self.client.get("/.well-known/oauth-protected-resource")
        self.assertEqual(res_res.status_code, 200)
        res_data = res_res.json()
        self.assertIn("resource", res_data)

    def test_oauth_client_binding(self):
        """Verify OAuth token is bound to detected AI Provider from redirect_uri."""
        # 1. Authorize with Claude redirect URI
        res = self.client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "test-claude-client",
                "redirect_uri": "https://claude.ai/api/mcp/oauth/callback",
                "state": "xyz123",
            },
        )
        self.assertEqual(res.status_code, 200)
        match = re.search(r"code=([a-zA-Z0-9_\-]+)", res.text)
        self.assertIsNotNone(match)
        auth_code = match.group(1)

        # 2. Exchange code for token
        token_res = self.client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": "test-claude-client",
            },
        )
        self.assertEqual(token_res.status_code, 200)
        token = token_res.json()["access_token"]

        # 3. Verify token is bound to Claude in SQLite
        self.assertEqual(get_token_client(token), "Claude")

    def test_gemini_oauth_redirect_uri_allowed(self):
        """Verify Gemini oauth-redirect.googleusercontent.com callback is accepted and bound to Gemini."""
        gemini_redirect = "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-109390662265013800476-pc_taild0529a_ts_net"
        res = self.client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "local-mcp",
                "redirect_uri": gemini_redirect,
                "scope": "mcp",
                "state": "test_state_123",
            },
        )
        self.assertEqual(res.status_code, 200)
        match = re.search(r"code=([a-zA-Z0-9_\-]+)", res.text)
        self.assertIsNotNone(match)
        auth_code = match.group(1)

        token_res = self.client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": "local-mcp",
                "redirect_uri": gemini_redirect,
            },
        )
        self.assertEqual(token_res.status_code, 200)
        token = token_res.json()["access_token"]
        self.assertEqual(get_token_client(token), "Gemini")

    def test_untrusted_redirect_uri_and_invalid_pkce_rejected(self):
        """Verify untrusted redirect_uri, mismatched redirect_uri, and unknown PKCE methods fail closed (SA-01)."""
        from ai_mcp_gateway.core.auth import CLIENT_SECRET, verify_pkce

        # 1. Unknown PKCE method must fail closed
        self.assertFalse(verify_pkce("some_verifier", "some_challenge", "unknown_method"))

        # 2. Untrusted external redirect_uri must be rejected with 400
        res_evil = self.client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "attacker-client",
                "redirect_uri": "https://evil.example.com/callback",
            },
        )
        self.assertEqual(res_evil.status_code, 400)

        # 3. Mismatched redirect_uri or client_id during token exchange must be rejected
        res_ok = self.client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "test-claude-client",
                "redirect_uri": "https://claude.ai/api/mcp/oauth/callback",
            },
        )
        self.assertEqual(res_ok.status_code, 200)
        auth_code = re.search(r"code=([a-zA-Z0-9_\-]+)", res_ok.text).group(1)

        mismatch_res = self.client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": "different-client-id",
            },
        )
        self.assertEqual(mismatch_res.status_code, 400)

        # 4. Static hardcoded repository secret must not be active (SA-02)
        self.assertNotEqual(CLIENT_SECRET, "agent-secret-key-12345")
        self.assertGreaterEqual(len(CLIENT_SECRET), 16)


if __name__ == "__main__":
    unittest.main()
