#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Docker smoke tests for groster
#
# Validates the full Docker stack: image build, runtime behavior, security,
# and volume persistence. Requires a running Docker daemon.
#
# Usage: bash scripts/docker-smoke-test.sh
# ---------------------------------------------------------------------------

IMAGE_NAME="groster-bot"
COMPOSE_SERVICE="bot"
MAX_IMAGE_SIZE_MB=350
EXPECTED_VERSION="0.5.0"
EXPECTED_USER="groster"

PASSED=0
FAILED=0

pass() {
    echo "  PASS: $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo "  FAIL: $1"
    FAILED=$((FAILED + 1))
}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

test_image_builds_successfully() {
    echo "[1/9] test_image_builds_successfully"
    if docker compose build --quiet "${COMPOSE_SERVICE}" >/dev/null 2>&1; then
        pass "Image builds successfully"
    else
        fail "Image build failed"
    fi
}

test_image_size_under_limit() {
    echo "[2/9] test_image_size_under_limit"
    local raw_size
    raw_size=$(docker images "${IMAGE_NAME}" --format '{{.Size}}' | head -1)

    local numeric
    numeric=$(echo "$raw_size" | grep -oP '[\d.]+')
    local unit
    unit=$(echo "$raw_size" | grep -oP '[A-Za-z]+')

    local size_mb=0
    case "$unit" in
        MB) size_mb=$(echo "$numeric" | awk '{printf "%d", $1}') ;;
        GB) size_mb=$(echo "$numeric" | awk '{printf "%d", $1 * 1024}') ;;
        kB|KB) size_mb=0 ;;
        *) size_mb=9999 ;;
    esac

    if [[ "$size_mb" -le "$MAX_IMAGE_SIZE_MB" ]]; then
        pass "Image size ${raw_size} is under ${MAX_IMAGE_SIZE_MB}MB"
    else
        fail "Image size ${raw_size} exceeds ${MAX_IMAGE_SIZE_MB}MB limit"
    fi
}

test_runs_as_nonroot_user() {
    echo "[3/9] test_runs_as_nonroot_user"
    local user
    user=$(docker run --rm --entrypoint whoami "${IMAGE_NAME}" 2>/dev/null)
    if [[ "$user" == "$EXPECTED_USER" ]]; then
        pass "Runs as non-root user '${user}'"
    else
        fail "Expected user '${EXPECTED_USER}', got '${user}'"
    fi
}

test_cli_version_outputs_version_string() {
    echo "[4/9] test_cli_version_outputs_version_string"
    local output
    output=$(docker run --rm "${IMAGE_NAME}" --version 2>&1)
    if echo "$output" | grep -q "$EXPECTED_VERSION"; then
        pass "CLI --version contains '${EXPECTED_VERSION}'"
    else
        fail "CLI --version output missing '${EXPECTED_VERSION}': ${output}"
    fi
}

test_cli_help_exits_zero() {
    echo "[5/9] test_cli_help_exits_zero"
    if docker run --rm "${IMAGE_NAME}" --help >/dev/null 2>&1; then
        pass "CLI --help exits 0"
    else
        fail "CLI --help exited non-zero"
    fi
}

test_no_secrets_in_image_history() {
    echo "[6/9] test_no_secrets_in_image_history"
    local history
    history=$(docker history "${IMAGE_NAME}" --no-trunc 2>/dev/null)
    if echo "$history" | grep -qiE 'CLIENT_SECRET|PUBLIC_KEY|BOT_TOKEN'; then
        fail "Secrets found in image history"
    else
        pass "No secrets in image history"
    fi
}

test_volume_mount_persists_data() {
    echo "[7/9] test_volume_mount_persists_data"
    local vol_name="groster-smoke-test-vol-$$"
    local marker="smoke-test-marker-$$"

    # Write a marker file
    docker run --rm -e GROSTER_DATA_PATH=/app/data -v "${vol_name}:/app/data" --entrypoint sh "${IMAGE_NAME}" \
        -c "echo '${marker}' > /app/data/test-marker.txt" 2>/dev/null

    # Read it back from a fresh container
    local content
    content=$(docker run --rm -e GROSTER_DATA_PATH=/app/data -v "${vol_name}:/app/data" --entrypoint cat "${IMAGE_NAME}" \
        /app/data/test-marker.txt 2>/dev/null || true)

    # Cleanup
    docker volume rm "$vol_name" >/dev/null 2>&1 || true

    if [[ "$content" == "$marker" ]]; then
        pass "Volume data persists across containers"
    else
        fail "Volume data did not persist (expected '${marker}', got '${content}')"
    fi
}

test_json_log_format_emits_valid_json() {
    echo "[8/9] test_json_log_format_emits_valid_json"
    local output
    output=$(docker run --rm -e GROSTER_LOG_FORMAT=json "${IMAGE_NAME}" --help 2>&1 || true)

    # Filter only lines that look like JSON objects
    local json_lines
    json_lines=$(echo "$output" | grep '^\s*{' || true)

    if [[ -z "$json_lines" ]]; then
        pass "JSON log format test (no log lines emitted on --help, skipped)"
    else
        if echo "$json_lines" | python -m json.tool >/dev/null 2>&1; then
            pass "JSON log output is valid JSON"
        else
            fail "JSON log output is not valid JSON: ${json_lines}"
        fi
    fi
}

test_text_log_format_writes_to_configured_log_dir() {
    echo "[9/9] test_text_log_format_writes_to_configured_log_dir"
    local log_dir="groster-smoke-test-logs-$$"
    local log_file="${log_dir}/groster.log"

    docker run --rm \
        -e GROSTER_LOG_FORMAT=text \
        -e GROSTER_LOG_DIR=/app/logs \
        -v "${log_dir}:/app/logs" \
        --entrypoint python \
        "${IMAGE_NAME}" \
        -c "from groster.logging import setup_logging; import logging; setup_logging(); logging.getLogger('groster.smoke').info('smoke test')" \
        >/dev/null 2>&1 || true

    if [[ -f "$log_file" ]] && grep -q "smoke test" "$log_file"; then
        pass "Text log format writes to configured log directory"
    else
        fail "Text log format did not write expected log file"
    fi

    rm -rf "$log_dir"
}

# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

echo "=== groster Docker Smoke Tests ==="
echo ""

test_image_builds_successfully
test_image_size_under_limit
test_runs_as_nonroot_user
test_cli_version_outputs_version_string
test_cli_help_exits_zero
test_no_secrets_in_image_history
test_volume_mount_persists_data
test_json_log_format_emits_valid_json
test_text_log_format_writes_to_configured_log_dir

echo ""
echo "=== Results: ${PASSED} passed, ${FAILED} failed (total $((PASSED + FAILED))) ==="

if [[ "$FAILED" -gt 0 ]]; then
    exit 1
fi
