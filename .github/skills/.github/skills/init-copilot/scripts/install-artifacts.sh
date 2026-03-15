#!/usr/bin/env bash
# install-artifacts.sh - Batch-fetch artifacts listed in a manifest file
#
# Usage: bash install-artifacts.sh <manifest-file>
#
# Manifest format:
#   One entry per line. Lines starting with # are comments. Empty lines ignored.
#   Two formats supported:
#     source-path                      (target = source)
#     source-path -> target-path       (different source and target)
#
# Environment variables (passed through to fetch-artifact.sh):
#   DEVCOPILOT_LOCAL   - Path to a local Dev Copilot clone. Skips network fetch.
#   DEVCOPILOT_REPO    - GitHub org/repo (default: pdffiller/dev-copilot).
#   DEVCOPILOT_BRANCH  - Branch name (default: main).
#
# Behavior:
#   - Skips files that already exist (prints SKIP)
#   - Reports INSTALLED / SKIP / FAIL per artifact
#   - Prints summary at the end
#
# Exit codes:
#   0 - All artifacts installed or skipped
#   1 - One or more artifacts failed

set -euo pipefail

MANIFEST="${1:-}"
FETCH_SCRIPT="$(dirname "$0")/fetch-artifact.sh"

if [[ -z "$MANIFEST" ]]; then
  echo "Usage: bash install-artifacts.sh <manifest-file>" >&2
  exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "Error: manifest file not found: $MANIFEST" >&2
  exit 1
fi

if [[ ! -f "$FETCH_SCRIPT" ]]; then
  echo "Error: fetch-artifact.sh not found at $FETCH_SCRIPT" >&2
  exit 1
fi

TOTAL=0
INSTALLED=0
SKIPPED=0
FAILED=0
FAILED_LIST=""

while IFS= read -r line || [[ -n "$line" ]]; do
  # Strip inline comments and trim whitespace
  line="${line%%#*}"
  line="$(echo "$line" | xargs 2>/dev/null || true)"
  [[ -z "$line" ]] && continue

  # Parse source -> target format
  if [[ "$line" == *" -> "* ]]; then
    SOURCE_PATH="${line%% -> *}"
    TARGET_PATH="${line##* -> }"
  else
    SOURCE_PATH="$line"
    TARGET_PATH="$line"
  fi

  TOTAL=$((TOTAL + 1))

  # Skip existing files
  if [[ -f "$TARGET_PATH" ]]; then
    echo "[SKIP]      $TARGET_PATH"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  if bash "$FETCH_SCRIPT" "$SOURCE_PATH" "$TARGET_PATH" > /dev/null 2>&1; then
    echo "[INSTALLED] $TARGET_PATH"
    INSTALLED=$((INSTALLED + 1))
  else
    echo "[FAIL]      $TARGET_PATH"
    FAILED=$((FAILED + 1))
    FAILED_LIST="$FAILED_LIST  - $SOURCE_PATH\n"
  fi
done < "$MANIFEST"

echo ""
echo "=== SUMMARY ==="
echo "total:     $TOTAL"
echo "installed: $INSTALLED"
echo "skipped:   $SKIPPED"
echo "failed:    $FAILED"

if [[ "$FAILED" -gt 0 ]]; then
  echo ""
  echo "Failed artifacts:"
  echo -e "$FAILED_LIST"
  exit 1
fi

exit 0
