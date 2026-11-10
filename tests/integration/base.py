"""Shared base class for integration test cases with managed TestClient lifespan."""

import atexit
import unittest

from fastapi.testclient import TestClient

from ai_mcp_gateway.main import app

_client_ctx = None
_client = None


def get_shared_client() -> TestClient:
    global _client_ctx, _client
    if _client is None:
        _client_ctx = TestClient(app)
        _client = _client_ctx.__enter__()
    return _client


@atexit.register
def _cleanup_client():
    global _client_ctx, _client
    if _client_ctx is not None:
        try:
            _client_ctx.__exit__(None, None, None)
        except Exception:
            pass
        _client_ctx = None
        _client = None


class BaseIntegrationTestCase(unittest.TestCase):
    """Base test case providing shared client across integration tests."""

    @property
    def client(self) -> TestClient:
        return get_shared_client()
