"""Interfaces package exposing presentation and middleware layers."""

from ai_mcp_gateway.interfaces.middleware import (
    PollingAccessLogFilter,
    create_security_middleware,
    current_client_var,
    detect_ai_provider,
    extract_client_name,
)

__all__ = [
    "PollingAccessLogFilter",
    "create_security_middleware",
    "current_client_var",
    "detect_ai_provider",
    "extract_client_name",
]
