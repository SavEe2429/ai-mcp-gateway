#!/usr/bin/env bash
# Retrieves the most recent SemVer Git tag prior to the current release.
set -euo pipefail

CURRENT_TAG="${1:-}"

# Fetch tags if in shallow clone
git fetch --tags --quiet 2>/dev/null || true

PREV_TAG=$(git tag -l "v[0-9]*" --sort=-v:refname | grep -v "^${CURRENT_TAG}$" | head -n 1 || true)

if [[ -z "$PREV_TAG" ]]; then
  echo "none"
else
  echo "$PREV_TAG"
fi
