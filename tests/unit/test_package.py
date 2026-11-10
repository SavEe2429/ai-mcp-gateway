"""Unit tests verifying package metadata and exports."""

import unittest

from ai_mcp_gateway.main import app


class TestPackageStructure(unittest.TestCase):
    def test_package_exports(self):
        """Verify package exports FastAPI app with correct title."""
        self.assertIsNotNone(app)
        self.assertEqual(app.title, "Local AI Agent Gateway")


if __name__ == "__main__":
    unittest.main()
