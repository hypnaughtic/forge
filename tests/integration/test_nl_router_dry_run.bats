#!/usr/bin/env bats
# ==============================================================================
# Integration Tests: NL Router Dry Run
# ==============================================================================
# Tests the full NL routing chain: input → classify → verify intents.
# Uses the real nl-router.sh script (not mocked).

load '../test_helper/common'

setup() {
    create_test_environment
    create_test_config
}

teardown() {
    destroy_test_environment
}

NL_ROUTER="${FORGE_ROOT}/scripts/nl-router.sh"

# --- Full chain: multi-intent parsing ---

@test "nl-router-chain: 'give me the cost and status overview' → STATUS,COST" {
    run bash "$NL_ROUTER" "give me the cost and status overview"
    assert_success
    [[ "$output" == *"STATUS"* ]]
    [[ "$output" == *"COST"* ]]
    # Should NOT contain ASK since we matched specific intents
    [[ "$output" != *"ASK"* ]]
}

@test "nl-router-chain: 'show team and budget' → TEAM,COST" {
    run bash "$NL_ROUTER" "show team and budget"
    assert_success
    [[ "$output" == *"TEAM"* ]]
    [[ "$output" == *"COST"* ]]
}

# --- Full chain: mode/strategy extraction ---

@test "nl-router-chain: 'switch to production-ready' → MODE" {
    run bash "$NL_ROUTER" "switch to production-ready"
    assert_success
    [[ "$output" == *"MODE"* ]]
}

@test "nl-router-chain: 'set auto-pilot strategy' → STRATEGY" {
    run bash "$NL_ROUTER" "set auto-pilot strategy"
    assert_success
    [[ "$output" == *"STRATEGY"* ]]
}

# --- Full chain: async fallback ---

@test "nl-router-chain: complex request falls back to ASK" {
    run bash "$NL_ROUTER" "redesign the database schema for better performance"
    assert_success
    assert_output "ASK"
}

# --- Full chain: guide detection ---

@test "nl-router-chain: 'guide backend-developer to use Redis' → GUIDE" {
    run bash "$NL_ROUTER" "guide backend-developer to use Redis"
    assert_success
    [[ "$output" == *"GUIDE"* ]]
}

# --- Pipe input ---

@test "nl-router-chain: accepts pipe input" {
    run bash -c "echo 'what is the status' | bash '$NL_ROUTER'"
    assert_success
    assert_output "STATUS"
}

# --- Combined instant + async detection ---

@test "nl-router-chain: all-instant returns only instant intents" {
    run bash "$NL_ROUTER" "show me the status, cost, and team"
    assert_success
    [[ "$output" == *"STATUS"* ]]
    [[ "$output" == *"COST"* ]]
    [[ "$output" == *"TEAM"* ]]
    [[ "$output" != *"ASK"* ]]
}
