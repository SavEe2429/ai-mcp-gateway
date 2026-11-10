"""Package execution entry point for `python -m ai_mcp_gateway`."""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
from ai_mcp_gateway.cli import main

## ---------- (04) CONSTANTS -------------------------------------------------------- ##
# No module-level constants required.

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.

## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
# Entry point delegates directly to ai_mcp_gateway.cli.main.

## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
# No private helper functions required.

## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
if __name__ == "__main__":
    main()
