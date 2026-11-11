"""Unit tests verifying package metadata and exports."""

import unittest

from ai_mcp_gateway.main import _mask_secret, app


class TestPackageStructure(unittest.TestCase):
    def test_package_exports(self):
        """Verify package exports FastAPI app with correct title."""
        self.assertIsNotNone(app)
        self.assertEqual(app.title, "Local AI Agent Gateway")

    def test_mask_secret_redacts_prefix(self):
        """Verify console startup secret masking hides all but last 4 characters."""
        masked = _mask_secret("super-secret-value-1234")
        self.assertTrue(masked.endswith("1234"))
        self.assertNotIn("super-secret", masked)
        self.assertEqual(_mask_secret("abcd"), "****")
        self.assertEqual(_mask_secret(""), "(not set)")


if __name__ == "__main__":
    unittest.main()
