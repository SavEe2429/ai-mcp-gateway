"""HTTP middleware package providing modular shields, logging filters, identity, and security pipeline."""

from ai_mcp_gateway.interfaces.middleware.identity import (
    current_client_var,
    detect_ai_provider,
    extract_client_name,
    extract_identity_from_payload,
)
from ai_mcp_gateway.interfaces.middleware.logging_filter import (
    SCANNER_EXTENSIONS,
    SCANNER_PREFIXES,
    PollingAccessLogFilter,
)
from ai_mcp_gateway.interfaces.middleware.security import create_security_middleware
from ai_mcp_gateway.interfaces.middleware.shield import (
    check_ip_blacklist,
    check_localhost_dashboard_guard,
    check_scanner_shield,
)

__all__ = [
    "PollingAccessLogFilter",
    "SCANNER_EXTENSIONS",
    "SCANNER_PREFIXES",
    "create_security_middleware",
    "current_client_var",
    "detect_ai_provider",
    "extract_client_name",
    "extract_identity_from_payload",
    "check_ip_blacklist",
    "check_scanner_shield",
    "check_localhost_dashboard_guard",
]
