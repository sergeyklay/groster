#!/usr/bin/env bash

# fetch-artifact.sh - Download a single artifact from the Dev Copilot repository
#
# Usage: ./fetch-artifact.sh <source-path> <target-path>
#
# Example:
#   ./fetch-artifact.sh .github/instructions/writing.instructions.md .github/instructions/writing.instructions.md
#   ./fetch-artifact.sh .github/agents/writer.agent.md .github/agents/writer.agent.md
#
# Environment variables (all optional):
#   DEVCOPILOT_LOCAL   - Path to a local clone of Dev Copilot. Skips network fetch.
#   DEVCOPILOT_REPO    - GitHub repo (default: pdffiller/dev-copilot). For private forks.
#   DEVCOPILOT_BRANCH  - Branch to fetch from (default: main).
#
# Fetch methods (tried in order):
#   1. Local clone (if DEVCOPILOT_LOCAL is set and the file exists there)
#   2. gh CLI (handles authentication for private repos)
#   3. curl to raw.githubusercontent.com (public repos, no auth)
#
# Exit codes:
#   0 - Success
#   1 - Missing arguments
#   2 - All fetch methods failed

set -euo pipefail

REPO="${DEVCOPILOT_REPO:-pdffiller/dev-copilot}"
BRANCH="${DEVCOPILOT_BRANCH:-main}"
SOURCE_PATH="$1"
TARGET_PATH="$2"

if [[ -z "${SOURCE_PATH:-}" || -z "${TARGET_PATH:-}" ]]; then
  echo "Usage: $0 <source-path> <target-path>" >&2
  exit 1
fi

# Create target directory
mkdir -p "$(dirname "$TARGET_PATH")"

# Method 1: Local clone
if [[ -n "${DEVCOPILOT_LOCAL:-}" ]]; then
  LOCAL_FILE="${DEVCOPILOT_LOCAL%/}/${SOURCE_PATH}"
  if [[ -f "$LOCAL_FILE" ]]; then
    cp "$LOCAL_FILE" "$TARGET_PATH"
    echo "Copied from local clone: $SOURCE_PATH -> $TARGET_PATH"
    exit 0
  else
    echo "Warning: Local file not found at $LOCAL_FILE, trying network methods" >&2
  fi
fi

# Method 2: gh CLI (handles auth for private repos)
if command -v gh &>/dev/null; then
  if gh api "repos/${REPO}/contents/${SOURCE_PATH}?ref=${BRANCH}" \
    --jq '.content' 2>/dev/null | base64 -d > "$TARGET_PATH" 2>/dev/null; then
    if [[ -s "$TARGET_PATH" ]]; then
      echo "Fetched via gh CLI: $SOURCE_PATH -> $TARGET_PATH"
      exit 0
    fi
  fi
  # gh method failed, clean up empty file
  rm -f "$TARGET_PATH"
fi

# Method 3: curl to raw.githubusercontent.com
RAW_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}/${SOURCE_PATH}"
HTTP_CODE=$(curl -sL -w "%{http_code}" -o "$TARGET_PATH" "$RAW_URL" 2>/dev/null || echo "000")

if [[ "$HTTP_CODE" == "200" && -s "$TARGET_PATH" ]]; then
  echo "Fetched via curl: $SOURCE_PATH -> $TARGET_PATH"
  exit 0
fi

# All methods failed
rm -f "$TARGET_PATH"
echo "Error: Failed to fetch $SOURCE_PATH from $REPO ($BRANCH)" >&2
echo "Tried: local clone, gh CLI, curl ($RAW_URL returned HTTP $HTTP_CODE)" >&2
echo "" >&2
echo "Possible fixes:" >&2
echo "  - Clone the repo locally: git clone https://github.com/${REPO}.git ~/dev-copilot" >&2
echo "  - Set DEVCOPILOT_LOCAL=~/dev-copilot" >&2
echo "  - For private repos, authenticate with: gh auth login" >&2
exit 2
