#!/usr/bin/env bats
# ==============================================================================
# Integration Tests: Cockpit Layout
# ==============================================================================
# Tests that cockpit scripts produce valid output when given mock data.
# Does NOT test tmux layout creation (requires tmux session).

load '../test_helper/common'

setup() {
    create_test_environment
    create_test_config "production-ready" "co-pilot"

    # Copy cockpit scripts
    mkdir -p "${FORGE_DIR}/scripts/cockpit"
    for script in "${FORGE_ROOT}/scripts/cockpit/"*.sh; do
        cp "$script" "${FORGE_DIR}/scripts/cockpit/"
        chmod +x "${FORGE_DIR}/scripts/cockpit/$(basename "$script")"
    done

    # Copy VERSION
    if [[ -f "${FORGE_ROOT}/VERSION" ]]; then
        cp "${FORGE_ROOT}/VERSION" "${FORGE_DIR}/VERSION"
    fi

    # Create mock agent status files
    create_status_file "team-leader" "working" "Orchestrating iteration 2" "0.50"
    create_status_file "backend-developer" "working" "Implementing auth" "1.20"
    create_status_file "qa-engineer" "idle" "Waiting for endpoints" "0.10"
}

teardown() {
    destroy_test_environment
}

# --- Metrics panel ---

@test "cockpit: metrics-panel produces output" {
    run bash -c "FORGE_DIR='${FORGE_DIR}' bash '${FORGE_DIR}/scripts/cockpit/metrics-panel.sh' 2>/dev/null"
    assert_success
    [[ -n "$output" ]]
}

@test "cockpit: metrics-panel shows version" {
    run bash -c "FORGE_DIR='${FORGE_DIR}' bash '${FORGE_DIR}/scripts/cockpit/metrics-panel.sh' 2>/dev/null"
    assert_success
    [[ "$output" == *"COCKPIT"* ]]
}

@test "cockpit: metrics-panel shows project info" {
    run bash -c "FORGE_DIR='${FORGE_DIR}' bash '${FORGE_DIR}/scripts/cockpit/metrics-panel.sh' 2>/dev/null"
    assert_success
    [[ "$output" == *"Project"* ]]
    [[ "$output" == *"Mode"* ]]
    [[ "$output" == *"Strategy"* ]]
}

# --- Agent grid ---

@test "cockpit: agent-grid produces output" {
    run bash -c "FORGE_DIR='${FORGE_DIR}' bash '${FORGE_DIR}/scripts/cockpit/agent-grid.sh' 2>/dev/null"
    assert_success
    [[ -n "$output" ]]
}

@test "cockpit: agent-grid shows agents" {
    run bash -c "FORGE_DIR='${FORGE_DIR}' bash '${FORGE_DIR}/scripts/cockpit/agent-grid.sh' 2>/dev/null"
    assert_success
    [[ "$output" == *"AGENT STATUS"* ]]
}

@test "cockpit: agent-grid shows agent abbreviations" {
    run bash -c "FORGE_DIR='${FORGE_DIR}' bash '${FORGE_DIR}/scripts/cockpit/agent-grid.sh' 2>/dev/null"
    assert_success
    # Should have abbreviated agent names
    [[ "$output" == *"TL"* || "$output" == *"BE"* || "$output" == *"QA"* ]]
}

@test "cockpit: agent-grid handles no agents gracefully" {
    rm -f "${SHARED_DIR}/.status/"*.json
    run bash -c "FORGE_DIR='${FORGE_DIR}' bash '${FORGE_DIR}/scripts/cockpit/agent-grid.sh' 2>/dev/null"
    assert_success
    [[ "$output" == *"No agents"* ]]
}

# --- Activity feed ---

@test "cockpit: activity-feed produces output" {
    run bash -c "FORGE_DIR='${FORGE_DIR}' bash '${FORGE_DIR}/scripts/cockpit/activity-feed.sh' 2>/dev/null"
    assert_success
    [[ -n "$output" ]]
}

@test "cockpit: activity-feed shows header" {
    run bash -c "FORGE_DIR='${FORGE_DIR}' bash '${FORGE_DIR}/scripts/cockpit/activity-feed.sh' 2>/dev/null"
    assert_success
    [[ "$output" == *"RECENT ACTIVITY"* ]]
}

@test "cockpit: activity-feed handles no logs gracefully" {
    run bash -c "FORGE_DIR='${FORGE_DIR}' bash '${FORGE_DIR}/scripts/cockpit/activity-feed.sh' 2>/dev/null"
    assert_success
    [[ "$output" == *"No"* ]]
}

# --- Render utilities ---

@test "cockpit: render.sh can be sourced without error" {
    run bash -c "source '${FORGE_DIR}/scripts/cockpit/render.sh'"
    assert_success
}
