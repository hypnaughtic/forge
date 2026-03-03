#!/usr/bin/env bats
# ==============================================================================
# Unit Tests: change-strategy.sh
# ==============================================================================
# Tests strategy switching, validation, broadcast, and reporting.

load '../test_helper/common'

setup() {
    create_test_environment
    create_test_config "mvp" "co-pilot"
    chmod +x "${FORGE_DIR}/scripts/broadcast.sh"
    # Use real yq for in-place config edits
    export MOCK_YQ_PASSTHROUGH=true
}

teardown() {
    destroy_test_environment
}

@test "change-strategy: updates config from co-pilot to auto-pilot" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-strategy.sh" "auto-pilot"
    assert_success

    local new_strategy
    new_strategy=$(yq eval '.strategy' "${FORGE_DIR}/config/team-config.yaml")
    [[ "$new_strategy" == "auto-pilot" ]]
}

@test "change-strategy: updates config to micro-manage" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-strategy.sh" "micro-manage"
    assert_success

    local new_strategy
    new_strategy=$(yq eval '.strategy' "${FORGE_DIR}/config/team-config.yaml")
    [[ "$new_strategy" == "micro-manage" ]]
}

@test "change-strategy: rejects invalid strategy" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-strategy.sh" "yolo-mode"
    assert_failure
    [[ "$output" == *"Invalid strategy"* ]]
}

@test "change-strategy: rejects empty strategy" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-strategy.sh" ""
    assert_failure
    [[ "$output" == *"No strategy specified"* ]]
}

@test "change-strategy: no-op when same strategy" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-strategy.sh" "co-pilot"
    assert_success
    [[ "$output" == *"already set"* ]]
}

@test "change-strategy: shows before/after report" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-strategy.sh" "auto-pilot"
    assert_success
    [[ "$output" == *"Previous"* ]]
    [[ "$output" == *"New"* ]]
    [[ "$output" == *"auto-pilot"* ]]
}

@test "change-strategy: shows details for auto-pilot" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-strategy.sh" "auto-pilot"
    assert_success
    [[ "$output" == *"autonomous"* ]]
}

@test "change-strategy: shows details for micro-manage" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-strategy.sh" "micro-manage"
    assert_success
    [[ "$output" == *"approval"* ]]
}

@test "change-strategy: --help shows usage" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-strategy.sh" --help
    assert_success
    [[ "$output" == *"Usage"* ]]
}
