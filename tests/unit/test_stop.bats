#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    # Create config so stop.sh can read it
    create_test_config "mvp" "co-pilot" "agent-teams"
    # Set grace period to 0 via mock yq so tests don't sleep
    export MOCK_YQ_GRACE_PERIOD=0
    # Initialize the project dir as a git repo so git commands succeed
    git init "$PROJECT_DIR" >/dev/null 2>&1
    git -C "$PROJECT_DIR" config user.email "test@test.com" 2>/dev/null || true
    git -C "$PROJECT_DIR" config user.name "Test" 2>/dev/null || true
    # Create an initial commit so rev-parse works
    touch "$PROJECT_DIR/.gitkeep"
    git -C "$PROJECT_DIR" add . >/dev/null 2>&1
    git -C "$PROJECT_DIR" commit -m "init" --allow-empty >/dev/null 2>&1 || true
}

teardown() {
    destroy_test_environment
}

# ==============================================================================
# Snapshot creation
# ==============================================================================

@test "stop creates a snapshot JSON file in snapshots dir" {
    # Use --snapshot-only to avoid broadcast delays and tmux interactions
    run bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
    assert_success

    # There should be at least one snapshot file
    local snap_count
    snap_count=$(ls -1 "${SHARED_DIR}/.snapshots"/snapshot-*.json 2>/dev/null | wc -l)
    [ "$snap_count" -ge 1 ]
}

@test "snapshot file is valid JSON with expected top-level keys" {
    run bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
    assert_success

    local snap_file
    snap_file=$(ls -t "${SHARED_DIR}/.snapshots"/snapshot-*.json 2>/dev/null | head -1)
    [ -n "$snap_file" ]

    # Check that the file contains expected keys (basic string search since
    # jq mock doesn't parse files)
    run cat "$snap_file"
    assert_output --partial '"snapshot_id"'
    assert_output --partial '"timestamp"'
    assert_output --partial '"project"'
    assert_output --partial '"agents"'
    assert_output --partial '"git"'
    assert_output --partial '"costs"'
}

# ==============================================================================
# Snapshot includes agent states
# ==============================================================================

@test "snapshot includes agent states from status files" {
    # Create status files for two agents
    create_status_file "backend-developer" "active" "Building API" "2.50"
    create_status_file "frontend-engineer" "idle" "Waiting" "1.00"

    run bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
    assert_success

    local snap_file
    snap_file=$(ls -t "${SHARED_DIR}/.snapshots"/snapshot-*.json 2>/dev/null | head -1)

    run cat "$snap_file"
    assert_output --partial '"backend-developer"'
    assert_output --partial '"frontend-engineer"'
}

# ==============================================================================
# Snapshot includes git state
# ==============================================================================

@test "snapshot includes git branch information" {
    run bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
    assert_success

    local snap_file
    snap_file=$(ls -t "${SHARED_DIR}/.snapshots"/snapshot-*.json 2>/dev/null | head -1)

    run cat "$snap_file"
    assert_output --partial '"current_branch"'
    assert_output --partial '"last_tag"'
    assert_output --partial '"uncommitted_changes"'
}

# ==============================================================================
# Snapshot retention
# ==============================================================================

@test "snapshot retention removes oldest snapshots beyond limit" {
    export MOCK_YQ_SNAPSHOT_RETENTION=5

    # Create 7 pre-existing snapshots with distinct timestamps
    for i in $(seq 1 7); do
        local ts=$((1000000 + i))
        echo '{"snapshot_id": "snapshot-'"$ts"'"}' > \
            "${SHARED_DIR}/.snapshots/snapshot-${ts}.json"
        # Ensure distinct modification times for ls -t ordering
        touch -t "202601010${i}00.00" "${SHARED_DIR}/.snapshots/snapshot-${ts}.json" 2>/dev/null || true
    done

    # stop.sh will create one more snapshot (total 8), then enforce retention=5
    run bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
    assert_success

    local remaining
    remaining=$(ls -1 "${SHARED_DIR}/.snapshots"/snapshot-*.json 2>/dev/null | wc -l)
    # Should have at most 5 snapshots after retention cleanup
    [ "$remaining" -le 5 ]
}

# ==============================================================================
# --snapshot-only skips broadcast
# ==============================================================================

@test "--snapshot-only skips broadcast to inboxes" {
    # Create agent inboxes
    mkdir -p "${SHARED_DIR}/.queue/agent-one-inbox"
    mkdir -p "${SHARED_DIR}/.queue/agent-two-inbox"

    run bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
    assert_success

    # No messages should be in any inbox
    local msg_count
    msg_count=$(find "${SHARED_DIR}/.queue/" -name "*.md" -type f 2>/dev/null | wc -l)
    [ "$msg_count" -eq 0 ]
}

@test "--snapshot-only output mentions skipping steps" {
    run bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
    assert_success
    assert_output --partial "Skipped"
}

# ==============================================================================
# --pause keeps tmux alive
# ==============================================================================

@test "--pause does not call tmux kill-session" {
    # Ensure mock tmux log starts clean
    rm -f "${MOCK_LOG_DIR}/tmux.log"

    # Create a status file so there's something to snapshot
    create_status_file "test-agent" "active" "Working" "1.0"

    # Create agent inbox so broadcast has a target
    mkdir -p "${SHARED_DIR}/.queue/test-agent-inbox"

    run bash "$FORGE_DIR/scripts/stop.sh" --pause
    assert_success

    # Save the script output for later assertion
    local stop_output="$output"

    # Verify tmux kill-session was NOT called
    if [ -f "${MOCK_LOG_DIR}/tmux.log" ]; then
        run cat "${MOCK_LOG_DIR}/tmux.log"
        refute_output --partial "kill-session"
    fi

    # Output from stop.sh should mention pause mode
    [[ "$stop_output" == *"Pause mode"* ]]
}
