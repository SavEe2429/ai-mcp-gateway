#!/usr/bin/env bash
# Promotes the [Unreleased] section of CHANGELOG.md to a new release version header.
set -euo pipefail

VERSION="${1:?Version argument required (e.g. 1.0.0)}"
DATE="${2:?Date argument required (e.g. 2026-11-03)}"
CHANGELOG_PATH="${3:-CHANGELOG.md}"

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

$PYTHON_BIN "$DIR/release_ops.py" update-changelog "$VERSION" "$DATE" --file "$CHANGELOG_PATH"
