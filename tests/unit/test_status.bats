#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    # Default: a forge session exists but no windows (so agents show as DEAD)
    export MOCK_TMUX_SESSIONS="forge-test:1 windows"
    export MOCK_TMUX_WINDOWS=""
}

teardown() {
    destroy_test_environment
}

# ==============================================================================
# Missing status directory
# ==============================================================================

@test "status: missing status dir exits 1" {
    rm -rf "${SHARED_DIR}/.status"

    run bash "$FORGE_DIR/scripts/status.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"No status directory found"* ]]
}

# ==============================================================================
# Basic output
# ==============================================================================

@test "status: reads status files and produces output" {
    create_status_file "backend-dev-1" "working" "Building API"
    create_status_file "frontend-dev-1" "idle" "Waiting"

    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/status.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"backend-dev-1"* ]]
    [[ "$output" == *"frontend-dev-1"* ]]
    [[ "$output" == *"Forge Agent Status"* ]]
}

@test "status: shows formatted table header" {
    create_status_file "agent-1" "idle"

    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/status.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"AGENT"* ]]
    [[ "$output" == *"STATUS"* ]]
    [[ "$output" == *"CURRENT TASK"* ]]
    [[ "$output" == *"FLAGS"* ]]
}

# ==============================================================================
# --json flag
# ==============================================================================

@test "status: --json flag does not crash" {
    create_status_file "json-agent" "working" "Some task" "1.5"

    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/status.sh" --json
    [ "$status" -eq 0 ]
    # In JSON mode, the formatted table header should NOT appear
    [[ "$output" != *"Forge Agent Status"* ]]
}

# ==============================================================================
# Stale detection
# ==============================================================================

@test "status: detects stale agents with old timestamp" {
    local agent="stale-agent"
    create_status_file "$agent" "working" "Stuck task"

    # Manually overwrite the timestamp to be >900 seconds old
    local old_timestamp
    if [[ "$(uname)" == "Darwin" ]]; then
        old_timestamp=$(date -u -v-20M +"%Y-%m-%dT%H:%M:%SZ")
    else
        old_timestamp=$(date -u -d "20 minutes ago" +"%Y-%m-%dT%H:%M:%SZ")
    fi

    local status_file="${SHARED_DIR}/.status/${agent}.json"
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "s/\"last_updated\": *\"[^\"]*\"/\"last_updated\": \"${old_timestamp}\"/" "$status_file"
    else
        sed -i "s/\"last_updated\": *\"[^\"]*\"/\"last_updated\": \"${old_timestamp}\"/" "$status_file"
    fi

    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/status.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"STALE"* ]]
}

# ==============================================================================
# Dead agent detection
# ==============================================================================

@test "status: agents without tmux windows show DEAD flag" {
    create_status_file "dead-agent" "working" "Lost task"

    # MOCK_TMUX_WINDOWS is empty, so no window matches "dead-agent"
    export MOCK_TMUX_WINDOWS=""
    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/status.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"DEAD"* ]]
}

@test "status: --help exits 0" {
    run bash "$FORGE_DIR/scripts/status.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
    [[ "$output" == *"--json"* ]]
}

# ==============================================================================
# No status files (empty directory)
# ==============================================================================

@test "status: empty status dir produces header but no agents" {
    # Status dir exists but is empty (no .json files)
    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/status.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Forge Agent Status"* ]]
}
