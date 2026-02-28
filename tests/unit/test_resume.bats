#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    create_test_config
    export MOCK_TMUX_HAS_SESSION="false"
}

teardown() {
    destroy_test_environment
}

@test "resume: no snapshots exits 1" {
    # Ensure no snapshots exist
    rm -rf "${SHARED_DIR}/.snapshots"
    mkdir -p "${SHARED_DIR}/.snapshots"

    run bash "$FORGE_DIR/scripts/resume.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"No snapshot"* ]]
}

@test "resume: specified snapshot missing exits 1" {
    run bash "$FORGE_DIR/scripts/resume.sh" --snapshot "/nonexistent/snapshot.json"
    [ "$status" -eq 1 ]
    [[ "$output" == *"not found"* ]]
}

@test "resume: finds latest snapshot automatically" {
    # Create two snapshots with different timestamps
    create_snapshot_file "snapshot-1000"
    sleep 1
    local latest
    latest=$(create_snapshot_file "snapshot-2000" 3)

    # The mock jq will handle parsing
    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/resume.sh"
    # It should find the latest snapshot and attempt to resume
    # It will call tmux (mocked) and spawn-agent (which will also call tmux mocked)
    [ "$status" -eq 0 ]
    [[ "$output" == *"Loading snapshot"* ]]
}

@test "resume: parses snapshot fields correctly" {
    local snapshot
    snapshot=$(create_snapshot_file "snapshot-test" 2)

    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/resume.sh" --snapshot "$snapshot"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Mode: mvp"* ]]
    [[ "$output" == *"Strategy: co-pilot"* ]]
}

@test "resume: creates resume-context.md" {
    local snapshot
    snapshot=$(create_snapshot_file "snapshot-test" 2)

    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/resume.sh" --snapshot "$snapshot"
    [ "$status" -eq 0 ]
    [ -f "${SHARED_DIR}/.memory/resume-context.md" ]
}

@test "resume: spawns team-leader with --resume" {
    local snapshot
    snapshot=$(create_snapshot_file "snapshot-test" 2)

    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/resume.sh" --snapshot "$snapshot"
    [ "$status" -eq 0 ]
    # Check tmux mock log for spawn-agent invocation
    [[ "$output" == *"Spawning Team Leader"* ]]
}
