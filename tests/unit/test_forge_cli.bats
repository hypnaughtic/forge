#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
}

teardown() {
    destroy_test_environment
}

# ==============================================================================
# forge --help
# ==============================================================================

@test "forge --help exits 0" {
    run bash "$FORGE_DIR/forge" --help
    assert_success
}

@test "forge --help output contains Usage" {
    run bash "$FORGE_DIR/forge" --help
    assert_success
    assert_output --partial "Usage"
}

@test "forge help subcommand exits 0" {
    run bash "$FORGE_DIR/forge" help
    assert_success
    assert_output --partial "Usage"
}

@test "forge -h exits 0" {
    run bash "$FORGE_DIR/forge" -h
    assert_success
    assert_output --partial "Usage"
}

# ==============================================================================
# Unknown command
# ==============================================================================

@test "forge unknown-command exits 1" {
    run bash "$FORGE_DIR/forge" nonexistent-command
    assert_failure
    assert_output --partial "Unknown command"
}

# ==============================================================================
# No-args (interactive mode) — requires config + claude + yq
# ==============================================================================

@test "no-args invokes cmd_interactive which checks for config" {
    # No config file exists, so it should fail looking for team-config.yaml
    run bash "$FORGE_DIR/forge"
    assert_failure
    assert_output --partial "No project configuration found"
}

# ==============================================================================
# setup subcommand
# ==============================================================================

@test "forge setup runs setup.sh" {
    run bash "$FORGE_DIR/forge" setup
    assert_success
    assert_output --partial "Setup"
}

# ==============================================================================
# tell subcommand
# ==============================================================================

@test "forge tell with no args shows help and exits 0" {
    run bash "$FORGE_DIR/forge" tell
    assert_success
    assert_output --partial "Usage"
    assert_output --partial "forge tell"
}

@test "forge tell --help shows help and exits 0" {
    run bash "$FORGE_DIR/forge" tell --help
    assert_success
    assert_output --partial "Usage"
}

@test "forge tell with message creates override.md" {
    run bash "$FORGE_DIR/forge" tell "Switch to production mode"
    assert_success

    local override_file="${SHARED_DIR}/.human/override.md"
    assert_file_exist "$override_file"

    run cat "$override_file"
    assert_output --partial "Switch to production mode"
    assert_output --partial "timestamp:"
    assert_output --partial "type: directive"
}

@test "forge tell writes message content into override.md body" {
    run bash "$FORGE_DIR/forge" tell "Pause all work immediately"
    assert_success

    local override_file="${SHARED_DIR}/.human/override.md"
    run cat "$override_file"
    assert_output --partial "Pause all work immediately"
    assert_output --partial "## Directive"
}

# ==============================================================================
# logs subcommand
# ==============================================================================

@test "forge logs --agent nonexistent exits 1 when log file missing" {
    # The logs directory exists (created by create_test_environment) but no
    # agent-specific log file is present.
    run bash "$FORGE_DIR/forge" logs --agent nonexistent-agent
    assert_failure
    assert_output --partial "No log file found for agent"
}

@test "forge logs --agent shows log content when file exists" {
    local logs_dir="${SHARED_DIR}/.logs"
    echo "2026-03-01 INFO test-agent started" > "${logs_dir}/test-agent.log"

    run bash "$FORGE_DIR/forge" logs --agent test-agent
    assert_success
    assert_output --partial "test-agent started"
}
