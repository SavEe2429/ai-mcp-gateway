#!/usr/bin/env bash
# Constructs the final release body markdown for GitHub Releases.
set -euo pipefail

VERSION="${1:?Version argument required}"
NOTES_FILE="${2:-Docs/public/release-notes/v${VERSION}.md}"
CHECKSUM_FILE="${3:-dist/SHA256SUMS.txt}"
OUTPUT_FILE="${4:-dist/RELEASE_BODY.md}"

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

$PYTHON_BIN "$DIR/release_ops.py" build-body "$VERSION" --notes "$NOTES_FILE" --checksums "$CHECKSUM_FILE" --out "$OUTPUT_FILE"
