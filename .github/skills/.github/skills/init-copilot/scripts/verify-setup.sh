#!/usr/bin/env bash
# verify-setup.sh - Verify that expected artifacts exist in the project
#
# Usage: bash verify-setup.sh <manifest-file>
#
# Manifest format: same as install-artifacts.sh
#   source-path                      (checks source path)
#   source-path -> target-path       (checks target path)
#
# Output:
#   [OK]      path/to/file    - File exists
#   [MISSING] path/to/file    - File not found
#
# Exit codes:
#   0 - All expected files present
#   1 - One or more files missing

set -euo pipefail

MANIFEST="${1:-}"

if [[ -z "$MANIFEST" ]]; then
  echo "Usage: bash verify-setup.sh <manifest-file>" >&2
  exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "Error: manifest file not found: $MANIFEST" >&2
  exit 1
fi

TOTAL=0
PRESENT=0
MISSING=0

while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%#*}"
  line="$(echo "$line" | xargs 2>/dev/null || true)"
  [[ -z "$line" ]] && continue

  # Parse source -> target format
  if [[ "$line" == *" -> "* ]]; then
    CHECK_PATH="${line##* -> }"
  else
    CHECK_PATH="$line"
  fi

  TOTAL=$((TOTAL + 1))

  if [[ -f "$CHECK_PATH" ]] || [[ -d "$CHECK_PATH" ]]; then
    echo "[OK]      $CHECK_PATH"
    PRESENT=$((PRESENT + 1))
  else
    echo "[MISSING] $CHECK_PATH"
    MISSING=$((MISSING + 1))
  fi
done < "$MANIFEST"

echo ""
echo "=== VERIFICATION ==="
echo "total:   $TOTAL"
echo "present: $PRESENT"
echo "missing: $MISSING"

[[ "$MISSING" -gt 0 ]] && exit 1
exit 0
