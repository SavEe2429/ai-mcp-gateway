"""Unit tests for config validation via Pydantic model and loader utility."""

import os
import tempfile
import unittest
from pathlib import Path

import yaml
from pydantic import ValidationError

from ai_mcp_gateway.model.config import (
    GatewayConfig,
)
from ai_mcp_gateway.utils.config import (
    get_config,
    get_data_dir,
    get_db_path,
    get_workspace_dir,
    load_and_validate_config,
)


class TestConfigModelAndValidation(unittest.TestCase):
    """Test YAML schema validation and constraints enforcement."""

    def test_pydantic_model_defaults(self):
        """Verify default values when instantiated without parameters."""
        cfg = GatewayConfig()
        self.assertEqual(cfg.session.ttl, 604800)
        self.assertEqual(cfg.session.auth_code_ttl, 3600)
        self.assertEqual(cfg.session.terminal_timeout, 60.0)
        self.assertEqual(cfg.server.port, 3000)
        self.assertEqual(cfg.server.host, "0.0.0.0")
        self.assertEqual(cfg.auth.client_id, "local-mcp")
        self.assertEqual(cfg.storage.workspace_dir, "workspace")
        self.assertIn(".php", cfg.security.scanner_extensions)

    def test_validate_real_config_yaml(self):
        """Verify that root config/config.yaml passes validation completely."""
        cfg = load_and_validate_config()
        self.assertIsInstance(cfg, GatewayConfig)
        self.assertEqual(cfg.session.ttl, 604800)
        self.assertEqual(cfg.server.port, 3000)
        self.assertIn("claude.ai", cfg.auth.allowed_redirect_domains)

    def test_validation_fails_on_invalid_port(self):
        """Verify validation rejects invalid port numbers (fail-fast rule)."""
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            yaml.dump({"server": {"port": 99999}}, f)  # Port out of 1-65535 range
            temp_path = f.name
        try:
            with self.assertRaises(ValidationError):
                load_and_validate_config(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_validation_fails_on_invalid_session_ttl(self):
        """Verify validation rejects invalid session TTL values (e.g. negative or 0)."""
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            yaml.dump({"session": {"ttl": -10}}, f)  # ge=1 required
            temp_path = f.name
        try:
            with self.assertRaises(ValidationError):
                load_and_validate_config(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_validation_succeeds_with_valid_custom_yaml(self):
        """Verify only validated config can be used."""
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            yaml.dump(
                {
                    "session": {"ttl": 3600, "auth_code_ttl": 120},
                    "server": {"port": 8080},
                },
                f,
            )
            temp_path = f.name
        try:
            validated = load_and_validate_config(temp_path)
            self.assertEqual(validated.session.ttl, 3600)
            self.assertEqual(validated.session.auth_code_ttl, 120)
            self.assertEqual(validated.server.port, 8080)
            # Default values should still be populated
            self.assertEqual(validated.storage.data_dir, "data")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_get_config_cached_singleton(self):
        """Verify get_config returns validated singleton."""
        cfg1 = get_config()
        cfg2 = get_config()
        self.assertIs(cfg1, cfg2)
        self.assertIsInstance(cfg1, GatewayConfig)

    def test_path_resolvers(self):
        """Verify path resolvers construct valid Path objects based on validated config."""
        data_dir = get_data_dir()
        db_path = get_db_path()
        ws_dir = get_workspace_dir()

        self.assertIsInstance(data_dir, Path)
        self.assertIsInstance(db_path, Path)
        self.assertTrue(str(db_path).endswith("gateway.db"))
        self.assertIsInstance(ws_dir, str)


if __name__ == "__main__":
    unittest.main()
