#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    # Remove shared dirs created by create_test_environment so setup.sh can
    # create them fresh — this lets us verify setup.sh actually creates them.
    rm -rf "${SHARED_DIR}"
}

teardown() {
    destroy_test_environment
}

# ==============================================================================
# Directory creation
# ==============================================================================

@test "setup creates all shared runtime directories" {
    run bash "$FORGE_DIR/setup.sh"
    assert_success

    assert_dir_exist "${SHARED_DIR}/.queue"
    assert_dir_exist "${SHARED_DIR}/.status"
    assert_dir_exist "${SHARED_DIR}/.memory"
    assert_dir_exist "${SHARED_DIR}/.decisions"
    assert_dir_exist "${SHARED_DIR}/.iterations"
    assert_dir_exist "${SHARED_DIR}/.artifacts"
    assert_dir_exist "${SHARED_DIR}/.locks"
    assert_dir_exist "${SHARED_DIR}/.logs"
    assert_dir_exist "${SHARED_DIR}/.logs/archive"
    assert_dir_exist "${SHARED_DIR}/.snapshots"
    assert_dir_exist "${SHARED_DIR}/.secrets"
    assert_dir_exist "${SHARED_DIR}/.human"
}

# ==============================================================================
# .secrets/.gitignore
# ==============================================================================

@test "setup creates .secrets/.gitignore containing wildcard" {
    run bash "$FORGE_DIR/setup.sh"
    assert_success

    local gitignore="${SHARED_DIR}/.secrets/.gitignore"
    assert_file_exist "$gitignore"

    run cat "$gitignore"
    assert_output "*"
}

# ==============================================================================
# Artifact registry
# ==============================================================================

@test "setup creates registry.json in .artifacts" {
    run bash "$FORGE_DIR/setup.sh"
    assert_success

    local registry="${SHARED_DIR}/.artifacts/registry.json"
    assert_file_exist "$registry"

    run cat "$registry"
    assert_output --partial '"artifacts"'
}

# ==============================================================================
# Script executability
# ==============================================================================

@test "setup makes scripts executable" {
    # Remove execute bit from all scripts before running setup
    chmod -x "${FORGE_DIR}/scripts/"*.sh 2>/dev/null || true
    chmod -x "${FORGE_DIR}/forge" 2>/dev/null || true

    run bash "$FORGE_DIR/setup.sh"
    assert_success

    # Verify forge CLI is executable
    [ -x "${FORGE_DIR}/forge" ]

    # Verify at least one script is executable
    [ -x "${FORGE_DIR}/scripts/broadcast.sh" ]
    [ -x "${FORGE_DIR}/scripts/stop.sh" ]
    [ -x "${FORGE_DIR}/scripts/spawn-agent.sh" ]
}

# ==============================================================================
# YAML validation (with mock yq)
# ==============================================================================

@test "setup validates config when yq is present and config is valid" {
    # Create a config file (mock yq always succeeds on eval so validation passes)
    create_test_config "mvp" "co-pilot" "agent-teams"

    run bash "$FORGE_DIR/setup.sh"
    assert_success
    assert_output --partial "valid YAML"
}

@test "setup warns when config file is missing" {
    # Do not create a config file
    run bash "$FORGE_DIR/setup.sh"
    assert_success
    assert_output --partial "team-config.yaml not found"
}

# ==============================================================================
# Idempotency
# ==============================================================================

@test "setup is idempotent — running twice succeeds" {
    create_test_config "mvp" "co-pilot" "agent-teams"

    run bash "$FORGE_DIR/setup.sh"
    assert_success

    run bash "$FORGE_DIR/setup.sh"
    assert_success
}

# ==============================================================================
# Help flag
# ==============================================================================

@test "setup --help exits 0 with usage info" {
    run bash "$FORGE_DIR/setup.sh" --help
    assert_success
    assert_output --partial "Usage"
}
