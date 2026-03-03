#!/usr/bin/env bats
# ==============================================================================
# Unit Tests: NL Router (scripts/nl-router.sh)
# ==============================================================================
# Tests intent classification for the natural language router.

load '../test_helper/common'

setup() {
    create_test_environment
}

teardown() {
    destroy_test_environment
}

NL_ROUTER="${FORGE_ROOT}/scripts/nl-router.sh"

# --- Single intent: STATUS ---

@test "nl-router: 'what is the status' → STATUS" {
    run bash "$NL_ROUTER" "what is the status"
    assert_success
    assert_output "STATUS"
}

@test "nl-router: 'how is the project going' → STATUS" {
    run bash "$NL_ROUTER" "how is the project going"
    assert_success
    assert_output "STATUS"
}

@test "nl-router: 'show me progress' → STATUS" {
    run bash "$NL_ROUTER" "show me progress"
    assert_success
    assert_output "STATUS"
}

# --- Single intent: COST ---

@test "nl-router: 'what is the cost' → COST" {
    run bash "$NL_ROUTER" "what is the cost"
    assert_success
    assert_output "COST"
}

@test "nl-router: 'how much have we spent' → COST" {
    run bash "$NL_ROUTER" "how much have we spent"
    assert_success
    assert_output "COST"
}

@test "nl-router: 'show budget' → COST" {
    run bash "$NL_ROUTER" "show budget"
    assert_success
    assert_output "COST"
}

# --- Single intent: TEAM ---

@test "nl-router: 'show me the team' → TEAM" {
    run bash "$NL_ROUTER" "show me the team"
    assert_success
    assert_output "TEAM"
}

@test "nl-router: 'who is working' → TEAM" {
    run bash "$NL_ROUTER" "who is working"
    assert_success
    assert_output "TEAM"
}

@test "nl-router: 'list agents' → TEAM" {
    run bash "$NL_ROUTER" "list agents"
    assert_success
    assert_output "TEAM"
}

# --- Single intent: SNAPSHOT ---

@test "nl-router: 'take a snapshot' → SNAPSHOT" {
    run bash "$NL_ROUTER" "take a snapshot"
    assert_success
    assert_output "SNAPSHOT"
}

@test "nl-router: 'save state' → SNAPSHOT" {
    run bash "$NL_ROUTER" "save state"
    assert_success
    assert_output "SNAPSHOT"
}

# --- Single intent: MODE ---

@test "nl-router: 'switch to mvp mode' → MODE" {
    run bash "$NL_ROUTER" "switch to mvp mode"
    assert_success
    assert_output "MODE"
}

@test "nl-router: 'change mode to production-ready' → MODE" {
    run bash "$NL_ROUTER" "change mode to production-ready"
    assert_success
    assert_output "MODE"
}

# --- Single intent: STRATEGY ---

@test "nl-router: 'switch strategy to auto-pilot' → STRATEGY" {
    run bash "$NL_ROUTER" "switch strategy to auto-pilot"
    assert_success
    assert_output "STRATEGY"
}

@test "nl-router: 'change to co-pilot' → STRATEGY" {
    run bash "$NL_ROUTER" "change to co-pilot"
    assert_success
    assert_output "STRATEGY"
}

# --- Single intent: START ---

@test "nl-router: 'start building' → START" {
    run bash "$NL_ROUTER" "start building"
    assert_success
    assert_output "START"
}

@test "nl-router: 'kick off the project' → START" {
    run bash "$NL_ROUTER" "kick off the project"
    assert_success
    assert_output "START"
}

# --- Single intent: STOP ---

@test "nl-router: 'stop the session' → STOP" {
    run bash "$NL_ROUTER" "stop the session"
    assert_success
    assert_output "STOP"
}

@test "nl-router: 'shut down everything' → STOP" {
    run bash "$NL_ROUTER" "shut down everything"
    assert_success
    assert_output "STOP"
}

# --- Multi-intent ---

@test "nl-router: 'cost and status' → COST,STATUS (order: STATUS first)" {
    run bash "$NL_ROUTER" "cost and status"
    assert_success
    # Should contain both
    [[ "$output" == *"STATUS"* ]]
    [[ "$output" == *"COST"* ]]
}

@test "nl-router: 'show status, cost, and team' → multiple intents" {
    run bash "$NL_ROUTER" "show status, cost, and team"
    assert_success
    [[ "$output" == *"STATUS"* ]]
    [[ "$output" == *"COST"* ]]
    [[ "$output" == *"TEAM"* ]]
}

# --- Intent over invocation ---

@test "nl-router: 'what is the cost' recognized as COST (even via ask)" {
    run bash "$NL_ROUTER" "what is the cost"
    assert_success
    assert_output "COST"
    # This should NOT return ASK
    [[ "$output" != *"ASK"* ]]
}

# --- Fallback to ASK ---

@test "nl-router: 'make the UX more modern' → ASK" {
    run bash "$NL_ROUTER" "make the UX more modern"
    assert_success
    assert_output "ASK"
}

@test "nl-router: 'add authentication to the backend' → ASK" {
    run bash "$NL_ROUTER" "add authentication to the backend"
    assert_success
    assert_output "ASK"
}

# --- Edge cases ---

@test "nl-router: empty input → ASK" {
    run bash "$NL_ROUTER" ""
    assert_success
    assert_output "ASK"
}

@test "nl-router: gibberish → ASK" {
    run bash "$NL_ROUTER" "asdfghjkl qwerty"
    assert_success
    assert_output "ASK"
}

@test "nl-router: case insensitivity" {
    run bash "$NL_ROUTER" "WHAT IS THE STATUS"
    assert_success
    assert_output "STATUS"
}

@test "nl-router: long implementation request falls back to ASK" {
    local long_input="please implement a comprehensive user authentication system with OAuth2 support including Google and GitHub providers with proper token refresh mechanisms and session management"
    run bash "$NL_ROUTER" "$long_input"
    assert_success
    assert_output "ASK"
}

# --- Fixes from LLM integration testing ---

@test "nl-router: 'how much money have we burned' → COST (colloquial)" {
    run bash "$NL_ROUTER" "how much money have we burned"
    assert_success
    assert_output "COST"
}

@test "nl-router: 'save the current progress' → SNAPSHOT (not STATUS)" {
    run bash "$NL_ROUTER" "save the current progress"
    assert_success
    assert_output "SNAPSHOT"
}

@test "nl-router: 'please stop all work' → STOP (with prefix words)" {
    run bash "$NL_ROUTER" "please stop all work"
    assert_success
    assert_output "STOP"
}

@test "nl-router: 'shut down all agents' → STOP (not STOP,TEAM)" {
    run bash "$NL_ROUTER" "shut down all agents"
    assert_success
    assert_output "STOP"
}

@test "nl-router: 'kick off the next iteration' → START (not START,STATUS)" {
    run bash "$NL_ROUTER" "kick off the next iteration"
    assert_success
    assert_output "START"
}

@test "nl-router: 'make the UI more responsive and modern' → ASK (not MODE)" {
    run bash "$NL_ROUTER" "make the UI more responsive and modern"
    assert_success
    assert_output "ASK"
}

@test "nl-router: 'give me cost breakdown and team overview' → COST,TEAM (not STATUS)" {
    run bash "$NL_ROUTER" "give me cost breakdown and team overview"
    assert_success
    [[ "$output" == *"COST"* ]]
    [[ "$output" == *"TEAM"* ]]
    [[ "$output" != *"STATUS"* ]]
}
