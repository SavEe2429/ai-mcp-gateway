"""Access log filters suppressing repetitive polling and scanner bot noise."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import logging

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.utils.config import get_config

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
SCANNER_EXTENSIONS: tuple[str, ...] = tuple(get_config().security.scanner_extensions)
SCANNER_PREFIXES: tuple[str, ...] = tuple(get_config().security.scanner_prefixes)

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.


## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
class PollingAccessLogFilter(logging.Filter):
    """Filter out repetitive polling and bot vulnerability scans from Uvicorn access logs."""

    SILENCED_PREFIXES: tuple[str, ...] = tuple(get_config().security.silenced_log_prefixes)

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False for polling endpoints and scanner probe paths."""
        if record.args and len(record.args) >= 3:
            path = record.args[2]
            if isinstance(path, str):
                p_lower = path.lower()
                if any(p_lower.startswith(prefix) for prefix in self.SILENCED_PREFIXES):
                    return False
                if any(p_lower.endswith(ext) for ext in SCANNER_EXTENSIONS):
                    return False
                if any(prefix in p_lower for prefix in SCANNER_PREFIXES):
                    return False

        msg = record.getMessage().lower()
        if any(prefix in msg for prefix in self.SILENCED_PREFIXES):
            return False
        if any(ext in msg for ext in SCANNER_EXTENSIONS):
            return False
        return not any(prefix in msg for prefix in SCANNER_PREFIXES)


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
# Exposed via PollingAccessLogFilter class.

## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
# Logging filter module only.
