"""Configuration loader, validation, and runtime path resolution utility.

Reads config/config.yaml, validates its schema via Pydantic models in
``ai_mcp_gateway.model.config``, and resolves bundled vs. writable runtime
paths safely in both source execution and frozen PyInstaller binaries.
"""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import logging
import os
import secrets
import sys
from pathlib import Path
from typing import Any, Dict, Optional

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
import yaml
from pydantic import ValidationError

## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.model.config import GatewayConfig

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
LOGGER: logging.Logger = logging.getLogger(__name__)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_CONFIG_PATH: Path = PROJECT_ROOT / "config" / "config.yaml"
_PLACEHOLDER_SECRETS = frozenset(
    {
        "change-this-to-a-secure-random-token-in-production",
        "agent-secret-key-12345",
    }
)
_CONFIG_CACHE: Optional[GatewayConfig] = None

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def is_frozen() -> bool:
    """Return True when running inside a frozen PyInstaller executable."""
    return bool(getattr(sys, "frozen", False))


def get_bundle_dir() -> Path:
    """Return directory containing read-only bundled assets (config, UI)."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def get_runtime_dir() -> Path:
    """Return writable base directory for runtime state (data/, workspace/)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def get_ui_index_file() -> Path:
    """Resolve the dashboard index.html path across source and frozen runs."""
    source_ui = Path(__file__).resolve().parent.parent / "interfaces" / "ui" / "index.html"
    if source_ui.is_file():
        return source_ui
    return get_bundle_dir() / "ai_mcp_gateway" / "interfaces" / "ui" / "index.html"


def find_config_yaml(custom_path: Optional[str | Path] = None) -> Path:
    """Locate the active config.yaml path in prioritized search locations."""
    candidates: list[Path] = []
    if custom_path:
        candidates.append(Path(custom_path))

    env_path = os.environ.get("GATEWAY_CONFIG_PATH")
    if env_path:
        candidates.append(Path(env_path))

    runtime_cfg = get_runtime_dir() / "config" / "config.yaml"
    candidates.append(runtime_cfg)
    candidates.append(Path.cwd() / "config" / "config.yaml")
    candidates.append(get_bundle_dir() / "config" / "config.yaml")
    candidates.append(DEFAULT_CONFIG_PATH)

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    return runtime_cfg if is_frozen() else DEFAULT_CONFIG_PATH


def read_yaml_file(custom_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Read raw YAML file into a dictionary."""
    yaml_file = find_config_yaml(custom_path)
    if not yaml_file.is_file():
        raise FileNotFoundError(f"Configuration file not found: {yaml_file}")

    with open(yaml_file, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
        return data if isinstance(data, dict) else {}


def load_and_validate_config(
    custom_path: Optional[str | Path] = None,
) -> GatewayConfig:
    """Read YAML file and validate data with GatewayConfig Pydantic model."""
    raw_data = read_yaml_file(custom_path)
    try:
        return GatewayConfig.model_validate(raw_data)
    except ValidationError as err:
        LOGGER.error(
            "[Config Validation Error] Invalid config in %s", custom_path or DEFAULT_CONFIG_PATH
        )
        raise err


def get_config(reload: bool = False) -> GatewayConfig:
    """Get the validated configuration instance (cached singleton)."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None or reload:
        _CONFIG_CACHE = load_and_validate_config()
    return _CONFIG_CACHE


def get_data_dir() -> Path:
    """Resolve absolute Path for writable data directory."""
    cfg = get_config()
    override = os.environ.get("GATEWAY_DATA_DIR")
    if override:
        return Path(override).resolve()
    return (get_runtime_dir() / cfg.storage.data_dir).resolve()


def get_db_path() -> Path:
    """Resolve absolute Path for SQLite database."""
    cfg = get_config()
    override = os.environ.get("GATEWAY_DB_PATH")
    if override:
        return Path(override).resolve()
    return (get_runtime_dir() / cfg.storage.db_path).resolve()


def get_workspace_dir() -> str:
    """Resolve absolute path for workspace directory."""
    cfg = get_config()
    override = os.environ.get("GATEWAY_WORKSPACE_DIR")
    if override:
        return str(Path(override).resolve())
    return str((get_runtime_dir() / cfg.storage.workspace_dir).resolve())


def get_client_secret_file() -> Path:
    """Resolve absolute Path for client secret file."""
    cfg = get_config()
    override = os.environ.get("GATEWAY_CLIENT_SECRET_FILE")
    if override:
        return Path(override).resolve()
    return (get_runtime_dir() / cfg.storage.client_secret_file).resolve()


def load_or_create_client_secret(
    secret_file: Optional[Path] = None, data_dir: Optional[Path] = None
) -> str:
    """Load client secret from environment variables, config.yaml, or persistent key file."""
    env_secret = os.environ.get("MCP_CLIENT_SECRET") or os.environ.get("GATEWAY_SECRET_KEY")
    if env_secret and env_secret.strip() not in _PLACEHOLDER_SECRETS:
        return env_secret.strip()

    cfg = get_config()
    yaml_secret = (cfg.auth.client_secret or "").strip()
    if yaml_secret and yaml_secret not in _PLACEHOLDER_SECRETS:
        return yaml_secret

    target_secret_file = secret_file or get_client_secret_file()
    target_data_dir = data_dir or get_data_dir()

    try:
        if target_secret_file.is_file():
            existing = target_secret_file.read_text(encoding="utf-8").strip()
            if len(existing) >= 16 and existing not in _PLACEHOLDER_SECRETS:
                return existing
        target_data_dir.mkdir(parents=True, exist_ok=True)
        generated = secrets.token_urlsafe(24)
        target_secret_file.write_text(generated, encoding="utf-8")
        return generated
    except OSError:
        return secrets.token_urlsafe(24)


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
config: GatewayConfig = get_config()
CLIENT_ID: str = os.environ.get("MCP_CLIENT_ID", config.auth.client_id)
CLIENT_SECRET: str = load_or_create_client_secret()
