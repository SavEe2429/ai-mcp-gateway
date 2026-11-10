#!/usr/bin/env bash
# Updates the release notes index document with the latest release reference.
set -euo pipefail

VERSION="${1:?Version argument required}"
DATE="${2:?Date argument required}"
INDEX_FILE="${3:-Docs/public/release-notes/README.md}"

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

$PYTHON_BIN "$DIR/release_ops.py" update-index "$VERSION" "$DATE" --file "$INDEX_FILE"
