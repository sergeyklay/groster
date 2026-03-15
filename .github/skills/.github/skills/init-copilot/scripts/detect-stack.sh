#!/usr/bin/env bash
# detect-stack.sh - Detect project tech stack and existing Dev Copilot artifacts
#
# Usage: bash detect-stack.sh [project-root]
#        Defaults to current directory if project-root is not specified.
#
# Output format (machine-readable, agent-parseable):
#   === STACKS ===
#   nodejs                          # One detected stack per line
#   php
#   === EXISTING ===
#   AGENTS.md                       # One existing artifact path per line
#   .github/agents/writer.agent.md
#   === DONE ===
#
# Exit codes: 0 always (informational tool)

set -euo pipefail
shopt -s nullglob

ROOT="${1:-.}"

# Normalize to absolute path for reliable file checks
ROOT="$(cd "$ROOT" && pwd)"

# --- Stack detection ---
echo "=== STACKS ==="

STACKS=""

check_stack() {
  local file="$1" stack="$2"
  if [[ -f "$ROOT/$file" ]] && [[ ! " $STACKS " == *" $stack "* ]]; then
    STACKS="$STACKS $stack"
    echo "$stack"
  fi
}

check_stack "package.json" "nodejs"
check_stack "composer.json" "php"
check_stack "go.mod" "go"
check_stack "requirements.txt" "python"
check_stack "pyproject.toml" "python"
check_stack "setup.py" "python"
check_stack "setup.cfg" "python"
check_stack "pom.xml" "java"
check_stack "build.gradle" "java"
check_stack "build.gradle.kts" "java"
check_stack "Cargo.toml" "rust"
check_stack "Gemfile" "ruby"

# .NET requires glob matching
for _ in "$ROOT"/*.sln "$ROOT"/*.csproj; do
  if [[ ! " $STACKS " == *" dotnet "* ]]; then
    STACKS="$STACKS dotnet"
    echo "dotnet"
  fi
  break
done

[[ -z "${STACKS// /}" ]] && echo "none"

# --- Existing artifacts ---
echo ""
echo "=== EXISTING ==="

# Governance and config files
for f in AGENTS.md .github/copilot-instructions.md .vscode/mcp.json; do
  [[ -f "$ROOT/$f" ]] && echo "$f"
done

# Agents
for f in "$ROOT"/.github/agents/*.agent.md; do
  echo ".github/agents/$(basename "$f")"
done

# Prompts
for f in "$ROOT"/.github/prompts/*.prompt.md; do
  echo ".github/prompts/$(basename "$f")"
done

# Instructions
for f in "$ROOT"/.github/instructions/*.instructions.md "$ROOT"/.github/instructions/*.instruction.md; do
  echo ".github/instructions/$(basename "$f")"
done

# Skills
for d in "$ROOT"/.github/skills/*/; do
  [[ -f "$d/SKILL.md" ]] && echo ".github/skills/$(basename "$d")/"
done

echo ""
echo "=== DONE ==="
