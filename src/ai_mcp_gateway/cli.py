"""Command-line interface entry point for AI Agent MCP Gateway."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import multiprocessing

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.main import run_server

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
# No module-level constants required.

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def main() -> None:
    """Launch the AI Agent MCP Gateway server."""
    multiprocessing.freeze_support()
    run_server()


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
if __name__ == "__main__":
    main()
