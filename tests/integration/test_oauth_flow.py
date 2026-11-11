"""Integration tests for RFC 8414 OAuth 2.1 metadata and token issuance."""

import base64
import hashlib
import re
import unittest
from urllib.parse import parse_qs, urlparse

from ai_mcp_gateway.core.auth import CLIENT_SECRET, verify_pkce
from ai_mcp_gateway.core.database import get_token_client
from tests.integration.base import BaseIntegrationTestCase


class TestOAuthEndpoints(BaseIntegrationTestCase):
    def _authorize_and_get_code(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        """Submit explicit consent POST with valid CLIENT_SECRET and extract auth code."""
        form_data = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "mcp",
            "client_secret": CLIENT_SECRET,
        }
        if state:
            form_data["state"] = state
        if code_challenge:
            form_data["code_challenge"] = code_challenge
            form_data["code_challenge_method"] = code_challenge_method or "S256"

        res = self.client.post("/oauth/authorize", data=form_data, follow_redirects=False)
        self.assertEqual(res.status_code, 303)
        location = res.headers.get("location", "")
        self.assertTrue(location.startswith(redirect_uri))
        parsed_query = parse_qs(urlparse(location).query)
        self.assertIn("code", parsed_query)
        return parsed_query["code"][0]

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

    def test_oauth_authorize_get_requires_manual_consent_and_secret(self):
        """Verify GET /oauth/authorize does not auto-approve and POST rejects wrong secret."""
        res_get = self.client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "test-claude-client",
                "redirect_uri": "https://claude.ai/api/mcp/oauth/callback",
                "state": "xyz123",
            },
        )
        self.assertEqual(res_get.status_code, 200)
        self.assertNotIn('http-equiv="refresh"', res_get.text.lower())
        self.assertIsNone(re.search(r"code=[a-zA-Z0-9_\-]{10,}", res_get.text))

        res_bad_post = self.client.post(
            "/oauth/authorize",
            data={
                "response_type": "code",
                "client_id": "test-claude-client",
                "redirect_uri": "https://claude.ai/api/mcp/oauth/callback",
                "client_secret": "wrong-secret",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_bad_post.status_code, 403)

    def test_oauth_client_binding_with_secret(self):
        """Verify OAuth token with client_secret is bound to detected AI Provider."""
        auth_code = self._authorize_and_get_code(
            client_id="test-claude-client",
            redirect_uri="https://claude.ai/api/mcp/oauth/callback",
            state="xyz123",
        )

        # Missing both PKCE and client_secret must be rejected (401)
        no_auth_res = self.client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": "test-claude-client",
            },
        )
        self.assertEqual(no_auth_res.status_code, 401)

        # Fresh code exchanged with valid client_secret must succeed
        auth_code = self._authorize_and_get_code(
            client_id="test-claude-client",
            redirect_uri="https://claude.ai/api/mcp/oauth/callback",
            state="xyz123",
        )
        token_res = self.client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": "test-claude-client",
                "client_secret": CLIENT_SECRET,
            },
        )
        self.assertEqual(token_res.status_code, 200)
        token = token_res.json()["access_token"]
        self.assertEqual(get_token_client(token), "Claude")

    def test_oauth_pkce_public_client_allowed_without_token_secret(self):
        """Verify public PKCE S256 clients can exchange token without client_secret on /oauth/token."""
        verifier = "test-pkce-verifier-with-sufficient-entropy-0123456789"
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
            .decode("ascii")
            .rstrip("=")
        )
        gemini_redirect = "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-109390662265013800476-pc_taild0529a_ts_net"
        auth_code = self._authorize_and_get_code(
            client_id="local-mcp",
            redirect_uri=gemini_redirect,
            state="test_state_123",
            code_challenge=challenge,
            code_challenge_method="S256",
        )

        token_res = self.client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": "local-mcp",
                "redirect_uri": gemini_redirect,
                "code_verifier": verifier,
            },
        )
        self.assertEqual(token_res.status_code, 200)
        token = token_res.json()["access_token"]
        self.assertEqual(get_token_client(token), "Gemini")

    def test_untrusted_redirect_uri_and_invalid_pkce_rejected(self):
        """Verify untrusted redirect_uri, mismatched redirect_uri, and unknown PKCE methods fail closed (SA-01)."""
        self.assertFalse(verify_pkce("some_verifier", "some_challenge", "unknown_method"))

        res_evil = self.client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "attacker-client",
                "redirect_uri": "https://evil.example.com/callback",
            },
        )
        self.assertEqual(res_evil.status_code, 400)

        auth_code = self._authorize_and_get_code(
            client_id="test-claude-client",
            redirect_uri="https://claude.ai/api/mcp/oauth/callback",
        )
        mismatch_res = self.client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": "different-client-id",
                "client_secret": CLIENT_SECRET,
            },
        )
        self.assertEqual(mismatch_res.status_code, 400)

        self.assertNotEqual(CLIENT_SECRET, "agent-secret-key-12345")
        self.assertGreaterEqual(len(CLIENT_SECRET), 16)


if __name__ == "__main__":
    unittest.main()
