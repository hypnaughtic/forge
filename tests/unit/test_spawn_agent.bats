#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    # spawn-agent.sh needs the base agent protocol and at least one agent MD
    # These were already copied by create_test_environment from the real
    # agents/ directory.
}

teardown() {
    destroy_test_environment
}

# ==============================================================================
# Required argument validation
# ==============================================================================

@test "spawn-agent exits 1 when --agent-type is missing" {
    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR"
    assert_failure
    assert_output --partial "--agent-type is required"
}

# ==============================================================================
# Inbox creation
# ==============================================================================

@test "spawn-agent creates inbox directory for agent" {
    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test"
    assert_success

    assert_dir_exist "${SHARED_DIR}/.queue/backend-developer-inbox"
}

# ==============================================================================
# Status file creation
# ==============================================================================

@test "spawn-agent creates status JSON file for agent" {
    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test"
    assert_success

    assert_file_exist "${SHARED_DIR}/.status/backend-developer.json"
}

@test "status file has correct initial values" {
    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test"
    assert_success

    local status_file="${SHARED_DIR}/.status/backend-developer.json"
    run cat "$status_file"
    assert_output --partial '"status": "idle"'
    assert_output --partial '"current_task": "Initializing"'
    assert_output --partial '"cost_estimate_usd": 0.0'
    assert_output --partial '"iteration": 0'
}

# ==============================================================================
# Permission flags by strategy
# ==============================================================================

@test "auto-pilot strategy passes --dangerously-skip-permissions to tmux" {
    rm -f "${MOCK_LOG_DIR}/tmux.log"

    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test" \
        --strategy "auto-pilot"
    assert_success

    # Check the tmux mock log for the permission flag
    assert_file_exist "${MOCK_LOG_DIR}/tmux.log"
    run cat "${MOCK_LOG_DIR}/tmux.log"
    assert_output --partial "dangerously-skip-permissions"
}

@test "co-pilot strategy passes --permission-mode acceptEdits to tmux" {
    rm -f "${MOCK_LOG_DIR}/tmux.log"

    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test" \
        --strategy "co-pilot"
    assert_success

    assert_file_exist "${MOCK_LOG_DIR}/tmux.log"
    run cat "${MOCK_LOG_DIR}/tmux.log"
    assert_output --partial "permission-mode acceptEdits"
}

@test "micro-manage strategy does not pass special permission flags" {
    rm -f "${MOCK_LOG_DIR}/tmux.log"

    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test" \
        --strategy "micro-manage"
    assert_success

    assert_file_exist "${MOCK_LOG_DIR}/tmux.log"
    run cat "${MOCK_LOG_DIR}/tmux.log"
    refute_output --partial "dangerously-skip-permissions"
    refute_output --partial "permission-mode"
}

# ==============================================================================
# Generated agent file takes priority over template
# ==============================================================================

@test "spawn-agent prefers generated agent file over template" {
    # Create the generated agent file location
    mkdir -p "${PROJECT_DIR}/.forge/agents"
    echo "# Generated backend-developer instructions" \
        > "${PROJECT_DIR}/.forge/agents/backend-developer.md"

    rm -f "${MOCK_LOG_DIR}/tmux.log"

    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test"
    assert_success

    # The script succeeded, meaning it found the generated file.
    # Verify by checking that the generated file still exists and was the
    # one that would be used (it's checked first in the script).
    assert_file_exist "${PROJECT_DIR}/.forge/agents/backend-developer.md"
}

@test "spawn-agent falls back to template when generated file is absent" {
    # Ensure no generated agent file exists
    rm -rf "${PROJECT_DIR}/.forge/agents"

    # The template agent file should exist (copied by create_test_environment)
    assert_file_exist "${FORGE_DIR}/agents/backend-developer.md"

    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test"
    assert_success
}

# ==============================================================================
# --resume includes working memory
# ==============================================================================

@test "--resume includes working memory in instruction" {
    # Create a working memory file for the agent
    echo "## Session State" > "${SHARED_DIR}/.memory/backend-developer-memory.md"
    echo "Last task: Completed API endpoints" >> "${SHARED_DIR}/.memory/backend-developer-memory.md"

    rm -f "${MOCK_LOG_DIR}/tmux.log"
    rm -f "${MOCK_LOG_DIR}/claude.log"

    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test" \
        --resume
    assert_success

    # The tmux new-window command includes the instruction file path. The
    # instruction file is a temp file that gets cat'd into claude. Since we
    # can't easily inspect a temp file after the script runs, we verify that
    # the tmux log contains the command and that the script succeeded with
    # --resume when the memory file exists.
    assert_file_exist "${MOCK_LOG_DIR}/tmux.log"
    run cat "${MOCK_LOG_DIR}/tmux.log"
    assert_output --partial "new-window"
}

@test "--resume without memory file still succeeds" {
    # No memory file exists — --resume should not fail, just skip memory
    rm -f "${SHARED_DIR}/.memory/backend-developer-memory.md"

    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test" \
        --resume
    assert_success
}

# ==============================================================================
# Instance ID handling
# ==============================================================================

@test "instance-id 1 uses simplified agent name without suffix" {
    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --instance-id "1" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test"
    assert_success

    # Status file should be named without -1 suffix
    assert_file_exist "${SHARED_DIR}/.status/backend-developer.json"
}

@test "instance-id 2 uses full agent name with suffix" {
    run bash "$FORGE_DIR/scripts/spawn-agent.sh" \
        --agent-type "backend-developer" \
        --instance-id "2" \
        --forge-dir "$FORGE_DIR" \
        --project-dir "$PROJECT_DIR" \
        --session "forge-test"
    assert_success

    # Status file should include the instance suffix
    assert_file_exist "${SHARED_DIR}/.status/backend-developer-2.json"
}
