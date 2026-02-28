#!/usr/bin/env bats
# ==============================================================================
# Integration: setup → init-project → stop lifecycle
# ==============================================================================
load '../test_helper/common'

setup() {
    create_test_environment
    export MOCK_YQ_PASSTHROUGH="true"
    export MOCK_JQ_PASSTHROUGH="true"
    create_test_config "mvp" "auto-pilot" "agent-teams"
}

teardown() {
    destroy_test_environment
}

@test "lifecycle: setup.sh creates directory structure" {
    run bash "$FORGE_DIR/setup.sh"
    [ "$status" -eq 0 ]
    [ -d "${SHARED_DIR}/.queue" ]
    [ -d "${SHARED_DIR}/.status" ]
    [ -d "${SHARED_DIR}/.memory" ]
    [ -d "${SHARED_DIR}/.snapshots" ]
}

@test "lifecycle: init-project.sh generates agent files" {
    run bash "$FORGE_DIR/scripts/init-project.sh" \
        --config "$FORGE_DIR/config/team-config.yaml" \
        --project-dir "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [ -d "$PROJECT_DIR/.forge/agents" ]

    # Lean profile should have 8 agents
    local agent_count
    agent_count=$(ls -1 "$PROJECT_DIR/.forge/agents/"*.md 2>/dev/null | wc -l)
    [ "$agent_count" -eq 8 ]
}

@test "lifecycle: stop.sh creates snapshot after init" {
    # First init
    bash "$FORGE_DIR/scripts/init-project.sh" \
        --config "$FORGE_DIR/config/team-config.yaml" \
        --project-dir "$PROJECT_DIR"

    # Create some status files to simulate running agents
    create_status_file "team-leader" "working" "Orchestrating" "1.5"
    create_status_file "backend-developer" "working" "Building API" "2.0"

    # Run stop in snapshot-only mode
    run bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
    [ "$status" -eq 0 ]

    # Snapshot should exist
    local snapshot_count
    snapshot_count=$(ls -1 "${SHARED_DIR}/.snapshots"/snapshot-*.json 2>/dev/null | wc -l)
    [ "$snapshot_count" -ge 1 ]

    # Snapshot should contain agent info
    local latest
    latest=$(ls -t "${SHARED_DIR}/.snapshots"/snapshot-*.json | head -1)
    local agents_in_snapshot
    agents_in_snapshot=$(jq '.agents | length' "$latest")
    [ "$agents_in_snapshot" -eq 2 ]
}

@test "lifecycle: snapshot contains correct project info" {
    bash "$FORGE_DIR/scripts/init-project.sh" \
        --config "$FORGE_DIR/config/team-config.yaml" \
        --project-dir "$PROJECT_DIR"

    create_status_file "team-leader" "idle" "Ready"

    run bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
    [ "$status" -eq 0 ]

    local latest
    latest=$(ls -t "${SHARED_DIR}/.snapshots"/snapshot-*.json | head -1)

    local mode
    mode=$(jq -r '.project.mode' "$latest")
    [ "$mode" = "mvp" ]

    local strategy
    strategy=$(jq -r '.project.strategy' "$latest")
    [ "$strategy" = "auto-pilot" ]
}
