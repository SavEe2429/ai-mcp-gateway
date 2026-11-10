# Project Delivery Roadmap

## Current Milestone: v1.0.0 Public Launch & Windows Binary Release

- Modularize ASGI routes, built-in MCP tools, and external MCP client bridging.
- Ship Windows `onedir` binary bundles (`ai-mcp-gateway-windows-x64.zip`) via automated GitHub Releases.
- Enforce hermetic tests, 9-section Python module structure, and Conventional Commits.

## Post-1.0 Priorities

- Cross-platform standalone binaries for Linux and macOS (`#2`).
- Dedicated frozen-runtime unit test coverage in `tests/unit/test_config.py` (`#3`).
- Optional desktop system tray launcher and runtime configuration editor in Web Dashboard.
