#!/usr/bin/env bats
# ==============================================================================
# Unit Tests: forge ask, tell, guide commands
# ==============================================================================
# Tests the ask (NL-routed), tell (deprecated), and guide commands.

load '../test_helper/common'

setup() {
    create_test_environment
    create_test_config
}

teardown() {
    destroy_test_environment
}

# --- forge ask ---

@test "forge ask: writes override.md with directive" {
    run bash "${FORGE_DIR}/forge" ask "please review the architecture"
    assert_success
    assert_file_exists "${SHARED_DIR}/.human/override.md"

    # Check content
    run grep "type: directive" "${SHARED_DIR}/.human/override.md"
    assert_success

    run grep "please review the architecture" "${SHARED_DIR}/.human/override.md"
    assert_success
}

@test "forge ask: shows confirmation message" {
    run bash "${FORGE_DIR}/forge" ask "refactor the auth module"
    assert_success
    [[ "$output" == *"queued"* || "$output" == *"Message"* || "$output" == *"sent"* ]]
}

@test "forge ask: with no arguments shows help" {
    run bash "${FORGE_DIR}/forge" ask
    assert_success
    [[ "$output" == *"Usage"* ]]
}

@test "forge ask: --help shows usage" {
    run bash "${FORGE_DIR}/forge" ask --help
    assert_success
    [[ "$output" == *"Usage"* ]]
}

# --- forge tell (backward compat) ---

@test "forge tell: still works with deprecation notice" {
    run bash "${FORGE_DIR}/forge" tell "refactor the payment module"
    assert_success
    # Should show deprecation warning
    [[ "$output" == *"deprecated"* ]]

    # Should still write override.md
    assert_file_exists "${SHARED_DIR}/.human/override.md"
    run grep "refactor the payment module" "${SHARED_DIR}/.human/override.md"
    assert_success
}

# --- forge guide ---

@test "forge guide: writes override.md with target_agent" {
    run bash "${FORGE_DIR}/forge" guide backend-developer "use PostgreSQL"
    assert_success
    assert_file_exists "${SHARED_DIR}/.human/override.md"

    # Check metadata
    run grep "type: agent-directive" "${SHARED_DIR}/.human/override.md"
    assert_success

    run grep "target_agent: backend-developer" "${SHARED_DIR}/.human/override.md"
    assert_success

    run grep "use PostgreSQL" "${SHARED_DIR}/.human/override.md"
    assert_success
}

@test "forge guide: shows targeted confirmation" {
    run bash "${FORGE_DIR}/forge" guide frontend-engineer "prioritize login page"
    assert_success
    [[ "$output" == *"frontend-engineer"* ]]
}

@test "forge guide: with insufficient args shows help" {
    run bash "${FORGE_DIR}/forge" guide backend-developer
    assert_success
    [[ "$output" == *"Usage"* ]]
}

@test "forge guide: --help shows usage" {
    run bash "${FORGE_DIR}/forge" guide --help
    assert_success
    [[ "$output" == *"Usage"* ]]
}

# --- Override file format ---

@test "override.md has timestamp in YAML frontmatter" {
    run bash "${FORGE_DIR}/forge" ask "test message"
    assert_success

    run grep "timestamp:" "${SHARED_DIR}/.human/override.md"
    assert_success
}

@test "guide override.md includes Target header" {
    run bash "${FORGE_DIR}/forge" guide qa-engineer "run integration tests"
    assert_success

    run grep -F "**Target:** qa-engineer" "${SHARED_DIR}/.human/override.md"
    assert_success
}
