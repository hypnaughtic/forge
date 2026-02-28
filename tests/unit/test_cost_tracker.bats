#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    create_test_config
    # Use real jq for cost parsing
    export MOCK_JQ_PASSTHROUGH="true"
}

teardown() {
    destroy_test_environment
}

# ==============================================================================
# Basic operation
# ==============================================================================

@test "cost-tracker: creates cost-summary.json in logs dir" {
    create_status_file "agent-1" "working" "Building" "2.5"

    run bash "$FORGE_DIR/scripts/cost-tracker.sh"
    [ "$status" -eq 0 ]
    [ -f "${SHARED_DIR}/.logs/cost-summary.json" ]
}

@test "cost-tracker: --help exits 0" {
    run bash "$FORGE_DIR/scripts/cost-tracker.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
    [[ "$output" == *"--report"* ]]
    [[ "$output" == *"--json"* ]]
}

# ==============================================================================
# Cost aggregation
# ==============================================================================

@test "cost-tracker: aggregates costs from multiple status files" {
    create_status_file "agent-alpha" "working" "Task A" "3.5"
    create_status_file "agent-beta" "idle" "Task B" "1.5"

    run bash "$FORGE_DIR/scripts/cost-tracker.sh"
    [ "$status" -eq 0 ]

    # Verify cost-summary.json contains the total
    local summary="${SHARED_DIR}/.logs/cost-summary.json"
    [ -f "$summary" ]

    # Total should be 3.5 + 1.5 = 5.0 (or 5)
    run cat "$summary"
    [[ "$output" == *'"total_cost_usd"'* ]]
    [[ "$output" == *'"agent-alpha"'* ]]
    [[ "$output" == *'"agent-beta"'* ]]

    # Parse the total with real jq
    local real_jq
    real_jq=$(which -a jq 2>/dev/null | grep -v "mock-bin" | head -1)
    local total
    total=$("$real_jq" -r '.total_cost_usd' "$summary")
    # bc comparison: total should equal 5 (3.5 + 1.5)
    local is_correct
    is_correct=$(echo "$total == 5" | bc)
    [ "$is_correct" -eq 1 ]
}

# ==============================================================================
# Report mode
# ==============================================================================

@test "cost-tracker: --report produces formatted output" {
    create_status_file "report-agent" "working" "Reporting" "4.2"

    run bash "$FORGE_DIR/scripts/cost-tracker.sh" --report
    [ "$status" -eq 0 ]
    [[ "$output" == *"Forge Cost Report"* ]]
    [[ "$output" == *"Total Cost"* ]]
    [[ "$output" == *"Budget Cap"* ]]
}

@test "cost-tracker: --report shows per-agent breakdown" {
    create_status_file "dev-1" "working" "Task 1" "2.0"
    create_status_file "dev-2" "idle" "Task 2" "3.0"

    run bash "$FORGE_DIR/scripts/cost-tracker.sh" --report
    [ "$status" -eq 0 ]
    [[ "$output" == *"Per Agent"* ]]
    [[ "$output" == *"dev-1"* ]]
    [[ "$output" == *"dev-2"* ]]
}

# ==============================================================================
# JSON mode
# ==============================================================================

@test "cost-tracker: --json outputs JSON" {
    create_status_file "json-agent" "working" "Task" "1.0"

    run bash "$FORGE_DIR/scripts/cost-tracker.sh" --json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"total_cost_usd"'* ]]
    [[ "$output" == *'"cost_cap_usd"'* ]]
    [[ "$output" == *'"per_agent"'* ]]
    [[ "$output" == *'"last_updated"'* ]]
}

# ==============================================================================
# Budget warnings
# ==============================================================================

@test "cost-tracker: budget warning at 80% threshold" {
    # Set cost_cap to 10 via mock yq
    export MOCK_YQ_COST_CAP="10"

    # Create a status file with cost=9 (90% of cap, above 80% threshold)
    create_status_file "expensive-agent" "working" "Heavy compute" "9"

    run bash "$FORGE_DIR/scripts/cost-tracker.sh" 2>&1
    # The warning goes to stderr, but bats captures both with 2>&1 in the command
    # Actually, bats `run` captures both stdout and stderr in $output
    [[ "$output" == *"Approaching"* ]] || [[ "$output" == *"Over budget"* ]]
}

@test "cost-tracker: over-budget warning when cost exceeds cap" {
    export MOCK_YQ_COST_CAP="5"

    create_status_file "overbudget-agent" "working" "Expensive task" "8"

    run bash "$FORGE_DIR/scripts/cost-tracker.sh" 2>&1
    [[ "$output" == *"Over budget"* ]] || [[ "$output" == *"WARNING"* ]]
}

@test "cost-tracker: no-cap produces no budget warning" {
    export MOCK_YQ_COST_CAP="no-cap"

    create_status_file "nocap-agent" "working" "Task" "100"

    run bash "$FORGE_DIR/scripts/cost-tracker.sh" 2>&1
    [ "$status" -eq 0 ]
    # Should NOT contain any budget warning
    [[ "$output" != *"Approaching"* ]]
    [[ "$output" != *"Over budget"* ]]
}

# ==============================================================================
# Edge cases
# ==============================================================================

@test "cost-tracker: handles no status files gracefully" {
    # No status files created; directory exists but is empty
    run bash "$FORGE_DIR/scripts/cost-tracker.sh"
    [ "$status" -eq 0 ]
    [ -f "${SHARED_DIR}/.logs/cost-summary.json" ]
}

@test "cost-tracker: handles zero-cost agents" {
    create_status_file "free-agent" "idle" "Resting" "0"

    run bash "$FORGE_DIR/scripts/cost-tracker.sh" --json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"total_cost_usd"'* ]]
}
