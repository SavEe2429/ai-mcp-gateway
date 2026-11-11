# Packaging Directory (`packaging/`)

Build scripts for compiling `ai-mcp-gateway` into standalone executables using PyInstaller.

## Contents

- `build.py`: Cross-platform PyInstaller packaging script targeting `out/ai-mcp-gateway/` (with
  intermediate work files in `build/ai-mcp-gateway/` and generated `packaging/ai-mcp-gateway.spec`
  via `--specpath`, ignored by `*.spec` in `.gitignore`).

## Build Commands

```bash
# Directory bundle (recommended, used by release.yml)
uv run python packaging/build.py --mode onedir

# Single standalone executable
uv run python packaging/build.py --mode onefile
```

## Bundled Data & Runtime Paths

- Bundles `src/ai_mcp_gateway/interfaces/ui/` and `config/` into read-only `_MEIPASS` storage.
- Writable runtime files (`data/`, `workspace/`, and optional external `config/config.yaml`) resolve
  relative to the executable directory via `src/ai_mcp_gateway/utils/config.py`.
