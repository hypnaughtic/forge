#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    # Ensure tmux mock finds a forge session
    export MOCK_TMUX_SESSIONS="forge-test:1 windows"
}

teardown() {
    destroy_test_environment
}

# ==============================================================================
# Argument validation
# ==============================================================================

@test "kill-agent: missing --agent exits 1" {
    run bash "$FORGE_DIR/scripts/kill-agent.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"--agent is required"* ]]
}

@test "kill-agent: --help exits 0" {
    run bash "$FORGE_DIR/scripts/kill-agent.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
    [[ "$output" == *"--agent"* ]]
}

# ==============================================================================
# Graceful mode (default, non-force)
# ==============================================================================

@test "kill-agent: graceful mode sends SHUTDOWN message to agent inbox" {
    local agent="test-agent-1"
    # Create a status file that is already "terminated" so the wait loop exits immediately
    create_status_file "$agent" "terminated" "Done"

    run bash "$FORGE_DIR/scripts/kill-agent.sh" --agent "$agent" --session forge-test
    [ "$status" -eq 0 ]

    # Verify SHUTDOWN message was created in the inbox
    local inbox="${SHARED_DIR}/.queue/${agent}-inbox"
    [ -d "$inbox" ]
    local msg_count
    msg_count=$(ls -1 "$inbox"/*.md 2>/dev/null | wc -l | tr -d ' ')
    [ "$msg_count" -ge 1 ]

    # Check message content
    local msg_file
    msg_file=$(ls "$inbox"/*.md | head -1)
    run cat "$msg_file"
    [[ "$output" == *"SHUTDOWN"* ]]
    [[ "$output" == *"from: system"* ]]
    [[ "$output" == *"to: ${agent}"* ]]
    [[ "$output" == *"priority: critical"* ]]
}

@test "kill-agent: graceful mode detects terminated status and acknowledges" {
    local agent="test-agent-2"
    # Pre-set status to "terminated" so the wait loop exits on first check
    create_status_file "$agent" "terminated" "Shutdown complete"

    export MOCK_JQ_PASSTHROUGH="true"

    run bash "$FORGE_DIR/scripts/kill-agent.sh" --agent "$agent" --session forge-test
    [ "$status" -eq 0 ]
    [[ "$output" == *"acknowledged shutdown"* ]]
}

# ==============================================================================
# Force mode
# ==============================================================================

@test "kill-agent: --force skips graceful shutdown, no message in inbox" {
    local agent="force-agent"
    create_status_file "$agent" "working" "Some task"

    run bash "$FORGE_DIR/scripts/kill-agent.sh" --agent "$agent" --session forge-test --force
    [ "$status" -eq 0 ]

    # Verify no inbox message was created (force skips graceful shutdown)
    local inbox="${SHARED_DIR}/.queue/${agent}-inbox"
    if [ -d "$inbox" ]; then
        local msg_count
        msg_count=$(ls -1 "$inbox"/*.md 2>/dev/null | wc -l | tr -d ' ')
        [ "$msg_count" -eq 0 ]
    fi
}

@test "kill-agent: --force still kills tmux window" {
    local agent="force-agent"
    create_status_file "$agent" "working" "Some task"

    run bash "$FORGE_DIR/scripts/kill-agent.sh" --agent "$agent" --session forge-test --force
    [ "$status" -eq 0 ]

    # Verify tmux kill-window was called
    run cat "${MOCK_LOG_DIR}/tmux.log"
    [[ "$output" == *"kill-window"* ]]
    [[ "$output" == *"forge-test:${agent}"* ]]
}

# ==============================================================================
# Status file update
# ==============================================================================

@test "kill-agent: updates status to terminated" {
    local agent="status-agent"
    # Create a status file with "working" status
    create_status_file "$agent" "working" "Building feature"

    run bash "$FORGE_DIR/scripts/kill-agent.sh" --agent "$agent" --session forge-test --force
    [ "$status" -eq 0 ]

    # Verify the status file was updated to "terminated"
    local status_file="${SHARED_DIR}/.status/${agent}.json"
    [ -f "$status_file" ]
    run cat "$status_file"
    [[ "$output" == *'"status": "terminated"'* ]]
}

@test "kill-agent: terminated message in output" {
    local agent="msg-agent"
    create_status_file "$agent" "idle"

    run bash "$FORGE_DIR/scripts/kill-agent.sh" --agent "$agent" --session forge-test --force
    [ "$status" -eq 0 ]
    [[ "$output" == *"${agent} terminated"* ]]
}

# ==============================================================================
# Session auto-detection
# ==============================================================================

@test "kill-agent: auto-detects tmux session from forge- prefix" {
    local agent="auto-detect-agent"
    create_status_file "$agent" "working" "Task"
    export MOCK_TMUX_SESSIONS="forge-myproject:1 windows"

    run bash "$FORGE_DIR/scripts/kill-agent.sh" --agent "$agent" --force
    [ "$status" -eq 0 ]
    [[ "$output" == *"terminated"* ]]
}

@test "kill-agent: no forge session found exits 1" {
    local agent="no-session-agent"
    export MOCK_TMUX_SESSIONS="none"

    run bash "$FORGE_DIR/scripts/kill-agent.sh" --agent "$agent"
    [ "$status" -eq 1 ]
    [[ "$output" == *"No Forge tmux session found"* ]]
}
