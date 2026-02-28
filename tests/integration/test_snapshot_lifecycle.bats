#!/usr/bin/env bats
# ==============================================================================
# Integration: Snapshot creation, retention, and resume
# ==============================================================================
load '../test_helper/common'

setup() {
    create_test_environment
    export MOCK_YQ_PASSTHROUGH="true"
    export MOCK_JQ_PASSTHROUGH="true"
    export MOCK_TMUX_HAS_SESSION="false"
    create_test_config "mvp" "co-pilot" "agent-teams"
}

teardown() {
    destroy_test_environment
}

@test "snapshot lifecycle: multiple snapshots are created with unique names" {
    create_status_file "agent-1" "idle"

    bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
    sleep 1
    bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only

    local count
    count=$(ls -1 "${SHARED_DIR}/.snapshots"/snapshot-*.json 2>/dev/null | wc -l)
    [ "$count" -ge 2 ]
}

@test "snapshot lifecycle: retention cleanup removes oldest" {
    # Set retention to 3
    yq eval -i '.session.snapshot_retention = 3' "$FORGE_DIR/config/team-config.yaml"

    create_status_file "agent-1" "idle"

    # Create 5 snapshots
    for i in $(seq 1 5); do
        bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
        sleep 1
    done

    local count
    count=$(ls -1 "${SHARED_DIR}/.snapshots"/snapshot-*.json 2>/dev/null | wc -l)
    [ "$count" -le 3 ]
}

@test "snapshot lifecycle: resume reads fields from snapshot" {
    create_status_file "team-leader" "working" "Building"

    bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only

    local latest
    latest=$(ls -t "${SHARED_DIR}/.snapshots"/snapshot-*.json | head -1)

    run bash "$FORGE_DIR/scripts/resume.sh" --snapshot "$latest"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Mode: mvp"* ]]
    [[ "$output" == *"Strategy: co-pilot"* ]]
}

@test "snapshot lifecycle: archive on fresh start" {
    create_status_file "team-leader" "idle"

    bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only

    local latest
    latest=$(ls -t "${SHARED_DIR}/.snapshots"/snapshot-*.json | head -1)

    # Manually archive (simulating what forge start --fresh does)
    mkdir -p "${SHARED_DIR}/.snapshots/archive"
    mv "$latest" "${SHARED_DIR}/.snapshots/archive/"

    # Verify archive has the file
    local archive_count
    archive_count=$(ls -1 "${SHARED_DIR}/.snapshots/archive/"*.json 2>/dev/null | wc -l)
    [ "$archive_count" -ge 1 ]

    # And snapshots dir is now empty
    local snap_count
    snap_count=$(ls -1 "${SHARED_DIR}/.snapshots"/snapshot-*.json 2>/dev/null | wc -l)
    [ "$snap_count" -eq 0 ]
}
