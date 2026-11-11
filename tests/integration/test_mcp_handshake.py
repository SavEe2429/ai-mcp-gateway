"""Integration tests for Model Context Protocol initialization and client registration."""

import secrets
import unittest

from ai_mcp_gateway.core.database import get_token_client, save_token
from ai_mcp_gateway.core.state import state
from tests.integration.base import BaseIntegrationTestCase


class TestMCPProtocol(BaseIntegrationTestCase):
    def test_mcp_initialize_handshake_detection(self):
        """Verify MCP initialize JSON-RPC payload registers the clientInfo name."""
        test_token = secrets.token_hex(32)
        save_token(test_token, client_name="Unknown")

        # Send MCP initialize payload
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "Cursor Agent",
                    "version": "0.42.0",
                },
            },
        }

        res = self.client.post(
            "/mcp",
            json=init_payload,
            headers={
                "Authorization": f"Bearer {test_token}",
            },
        )
        self.assertEqual(res.status_code, 200)
        # The middleware should detect "Cursor" and register token and client host
        self.assertEqual(get_token_client(test_token), "Cursor")
        self.assertEqual(state.session_ai_clients.get("testclient"), "Cursor")
        new_sess = res.headers.get("mcp-session-id")
        if new_sess:
            self.assertEqual(state.session_ai_clients.get(new_sess), "Cursor")

    def test_openai_tools_call_meta_detection(self):
        """Verify OpenAI tools/call containing _meta.openai/... registers ChatGPT."""
        test_token = secrets.token_hex(32)
        save_token(test_token, client_name="AI Agent")

        openai_payload = {
            "method": "tools/call",
            "params": {
                "_meta": {
                    "openai/userAgent": "Mozilla/5.0",
                    "openai/session": "v1/sample-session",
                    "io.modelcontextprotocol/clientInfo": {
                        "name": "openai-mcp",
                        "version": "1.0.0",
                    },
                },
                "name": "run_command",
                "arguments": {"command": "cd"},
            },
            "jsonrpc": "2.0",
            "id": 0,
        }

        self.client.post(
            "/mcp",
            json=openai_payload,
            headers={
                "Authorization": f"Bearer {test_token}",
            },
        )
        # Should detect "ChatGPT" from openai-mcp and _meta regardless of MCP tool response
        self.assertEqual(get_token_client(test_token), "ChatGPT")
        self.assertEqual(state.session_ai_clients.get("testclient"), "ChatGPT")

    def test_mcp_delete_requires_bearer_token(self):
        """Verify DELETE /mcp enforces Bearer token authentication before terminating session (SA-05)."""
        unauth_res = self.client.delete("/mcp")
        self.assertEqual(unauth_res.status_code, 401)

        test_token = secrets.token_hex(32)
        save_token(test_token, client_name="Claude")
        auth_res = self.client.delete("/mcp", headers={"Authorization": f"Bearer {test_token}"})
        self.assertEqual(auth_res.status_code, 200)

    def test_mcp_rejects_query_param_bearer_token(self):
        """Verify /mcp rejects ?token= query parameter fallback and requires Authorization header."""
        test_token = secrets.token_hex(32)
        save_token(test_token, client_name="Claude")
        res = self.client.delete(f"/mcp?token={test_token}")
        self.assertEqual(res.status_code, 401)

    def test_mcp_rejects_payload_too_large(self):
        """Verify POST /mcp with Content-Length exceeding 16MB is rejected with 413 Payload Too Large."""
        res = self.client.post(
            "/mcp",
            content=b"test",
            headers={
                "Content-Length": str(20 * 1024 * 1024),  # 20MB
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(res.status_code, 413)
        self.assertIn("Payload Too Large", res.json()["error"])


if __name__ == "__main__":
    unittest.main()
