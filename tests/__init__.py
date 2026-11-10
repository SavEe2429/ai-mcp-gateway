"""Test suite initialization ensuring hermetic temporary storage paths."""

import atexit
import os
import shutil
import sys
import tempfile

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

if "GATEWAY_DB_PATH" not in os.environ:
    _TEST_ROOT = tempfile.mkdtemp(prefix="ai_mcp_gateway_test_")
    _TEST_DATA = os.path.join(_TEST_ROOT, "data")
    _TEST_WORKSPACE = os.path.join(_TEST_ROOT, "workspace")
    os.makedirs(_TEST_DATA, exist_ok=True)
    os.makedirs(_TEST_WORKSPACE, exist_ok=True)

    os.environ.setdefault("GATEWAY_DATA_DIR", _TEST_DATA)
    os.environ["GATEWAY_DB_PATH"] = os.path.join(_TEST_DATA, "gateway.db")
    os.environ.setdefault("GATEWAY_WORKSPACE_DIR", _TEST_WORKSPACE)
    os.environ.setdefault(
        "GATEWAY_CLIENT_SECRET_FILE", os.path.join(_TEST_DATA, "client_secret.key")
    )

    atexit.register(lambda: shutil.rmtree(_TEST_ROOT, ignore_errors=True))
