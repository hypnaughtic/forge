#!/usr/bin/env bats
# ==============================================================================
# Unit Tests: team-view.sh
# ==============================================================================
# Tests all-agent overview and single-agent deep dive views.

load '../test_helper/common'

setup() {
    create_test_environment
    create_test_config
    # Use real jq for JSON parsing (mock jq returns hardcoded values)
    export MOCK_JQ_PASSTHROUGH=true
    # Create some mock agent status files
    create_status_file "team-leader" "working" "Orchestrating iteration 2" "0.50"
    create_status_file "backend-developer" "working" "Implementing auth module" "1.20"
    create_status_file "frontend-engineer" "idle" "Waiting for API spec" "0.30"
    create_status_file "qa-engineer" "blocked" "Blocked on auth endpoints" "0.10"
}

teardown() {
    destroy_test_environment
}

# TEAM_VIEW must be set after setup, not at file scope

# --- All agents overview ---

@test "team-view: shows all agents in overview" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh"
    assert_success
    [[ "$output" == *"team-leader"* ]]
    [[ "$output" == *"backend-developer"* ]]
    [[ "$output" == *"frontend-engineer"* ]]
    [[ "$output" == *"qa-engineer"* ]]
}

@test "team-view: shows status for each agent" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh"
    assert_success
    [[ "$output" == *"working"* ]]
    [[ "$output" == *"idle"* ]]
    [[ "$output" == *"blocked"* ]]
}

@test "team-view: shows current task" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh"
    assert_success
    [[ "$output" == *"Implementing auth"* || "$output" == *"auth module"* ]]
}

@test "team-view: shows header" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh"
    assert_success
    [[ "$output" == *"Team Overview"* ]]
}

@test "team-view: shows hint for deep dive" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh"
    assert_success
    [[ "$output" == *"team <agent-name>"* || "$output" == *"detailed view"* ]]
}

# --- Single agent deep dive ---

@test "team-view: deep dive shows agent name" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh" "backend-developer"
    assert_success
    [[ "$output" == *"backend-developer"* ]]
    [[ "$output" == *"Deep Dive"* ]]
}

@test "team-view: deep dive shows status details" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh" "backend-developer"
    assert_success
    [[ "$output" == *"Status"* ]]
    [[ "$output" == *"Task"* ]]
    [[ "$output" == *"Cost"* ]]
}

@test "team-view: deep dive shows cost" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh" "backend-developer"
    assert_success
    [[ "$output" == *"1.2"* ]]
}

# --- Edge cases ---

@test "team-view: handles missing status directory gracefully" {
    # Remove status directory entirely
    rm -rf "${SHARED_DIR}/.status"
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh"
    assert_success
    [[ "$output" == *"No agents"* || "$output" == *"Start a session"* ]]
}

@test "team-view: handles missing agent in deep dive" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh" "nonexistent-agent"
    assert_success
    [[ "$output" == *"No status file"* || "$output" == *"nonexistent-agent"* ]]
}

@test "team-view: --help shows usage" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh" --help
    assert_success
    [[ "$output" == *"Usage"* ]]
}

# --- Working memory ---

@test "team-view: deep dive shows working memory section" {
    # Create a mock memory file
    mkdir -p "${SHARED_DIR}/.memory"
    echo "# Backend Developer Memory" > "${SHARED_DIR}/.memory/backend-developer-memory.md"
    echo "Currently implementing user authentication." >> "${SHARED_DIR}/.memory/backend-developer-memory.md"

    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/team-view.sh" "backend-developer"
    assert_success
    [[ "$output" == *"Working Memory"* ]]
}
