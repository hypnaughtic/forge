#!/usr/bin/env bats
# ==============================================================================
# Unit Tests: change-mode.sh
# ==============================================================================
# Tests mode switching, validation, broadcast, and reporting.

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

@test "change-mode: updates config from mvp to production-ready" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" "production-ready"
    assert_success

    local new_mode
    new_mode=$(yq eval '.mode' "${FORGE_DIR}/config/team-config.yaml")
    [[ "$new_mode" == "production-ready" ]]
}

@test "change-mode: updates config to no-compromise" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" "no-compromise"
    assert_success

    local new_mode
    new_mode=$(yq eval '.mode' "${FORGE_DIR}/config/team-config.yaml")
    [[ "$new_mode" == "no-compromise" ]]
}

@test "change-mode: rejects invalid mode" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" "ultra-mode"
    assert_failure
    [[ "$output" == *"Invalid mode"* ]]
}

@test "change-mode: rejects empty mode" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" ""
    assert_failure
    [[ "$output" == *"No mode specified"* ]]
}

@test "change-mode: no-op when same mode" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" "mvp"
    assert_success
    [[ "$output" == *"already set"* ]]
}

@test "change-mode: shows before/after report" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" "production-ready"
    assert_success
    [[ "$output" == *"Previous"* ]]
    [[ "$output" == *"New"* ]]
    [[ "$output" == *"production-ready"* ]]
}

@test "change-mode: shows quality details for mvp" {
    env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" "production-ready"
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" "mvp"
    assert_success
    [[ "$output" == *"70%"* ]]
}

@test "change-mode: shows quality details for production-ready" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" "production-ready"
    assert_success
    [[ "$output" == *"90%"* ]]
}

@test "change-mode: shows quality details for no-compromise" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" "no-compromise"
    assert_success
    [[ "$output" == *"100%"* ]]
}

@test "change-mode: --help shows usage" {
    run env FORGE_DIR="${FORGE_DIR}" bash "${FORGE_DIR}/scripts/change-mode.sh" --help
    assert_success
    [[ "$output" == *"Usage"* ]]
}
