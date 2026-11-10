#!/usr/bin/env bash
# Extracts release notes for a specified version into a standalone markdown file.
set -euo pipefail

VERSION="${1:?Version argument required (e.g. 1.0.0)}"
CHANGELOG_PATH="${2:-CHANGELOG.md}"
OUTPUT_DIR="${3:-Docs/public/release-notes}"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON_BIN=""
for cmd in python3 python py uv; do
  if command -v "$cmd" >/dev/null 2>&1; then
    if [[ "$cmd" == "uv" ]]; then
      PYTHON_BIN="uv run python"
    else
      PYTHON_BIN="$cmd"
    fi
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "ERROR: Python runtime not found (checked python3, python, py, uv)" >&2
  exit 1
fi

$PYTHON_BIN "$DIR/release_ops.py" generate-notes "$VERSION" --changelog "$CHANGELOG_PATH" --out-dir "$OUTPUT_DIR"
