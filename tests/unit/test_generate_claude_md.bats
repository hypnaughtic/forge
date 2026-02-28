#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    # Default mock yq values
    export MOCK_YQ_MODE="mvp"
    export MOCK_YQ_STRATEGY="co-pilot"
    export MOCK_YQ_ORCHESTRATION="agent-teams"
    export MOCK_YQ_PROJECT_DESC="Test Project"
    export MOCK_YQ_COST_CAP="50"
    export MOCK_YQ_TEAM_PROFILE="auto"
    export MOCK_YQ_EXCLUDE=""
    export MOCK_YQ_ADDITIONAL=""
    export MOCK_YQ_INCLUDE=""
    export MOCK_YQ_CLAUDE_MD_SOURCE="none"
    export MOCK_YQ_CLAUDE_MD_PRIORITY="project-first"
    export MOCK_YQ_CLAUDE_MD_GLOBAL=""
    export MOCK_YQ_REQ_FILE=""
    export MOCK_YQ_TECH_LANGS=""
    export MOCK_YQ_TECH_FRAMEWORKS=""
    # Use real jq for snapshot parsing
    export MOCK_JQ_PASSTHROUGH="true"
}

teardown() {
    destroy_test_environment
}

# ==============================================================================
# Argument validation
# ==============================================================================

@test "generate-claude-md: missing --project-dir exits 1" {
    # Create config so it doesn't fail on missing config
    create_test_config

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Missing --project-dir"* ]]
}

@test "generate-claude-md: missing config file exits 1" {
    # Do not create config file, but ensure yq is on PATH (it is via mock)
    # Point to a nonexistent config explicitly
    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --project-dir "$PROJECT_DIR" --config "/nonexistent/config.yaml"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Config file not found"* ]]
}

@test "generate-claude-md: --help exits 0" {
    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
}

# ==============================================================================
# Output content
# ==============================================================================

@test "generate-claude-md: output contains project config values" {
    create_test_config "mvp" "co-pilot" "agent-teams"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    # Verify CLAUDE.md was created
    [ -f "${PROJECT_DIR}/CLAUDE.md" ]

    # Check content for project name, mode, and strategy
    run cat "${PROJECT_DIR}/CLAUDE.md"
    [[ "$output" == *"Test Project"* ]]
    [[ "$output" == *"mvp"* ]]
    [[ "$output" == *"co-pilot"* ]]
}

@test "generate-claude-md: output contains Team Leader identity" {
    create_test_config

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "${PROJECT_DIR}/CLAUDE.md"
    [[ "$output" == *"Team Leader"* ]]
    [[ "$output" == *"Your Identity"* ]]
}

@test "generate-claude-md: output contains slash commands" {
    create_test_config

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "${PROJECT_DIR}/CLAUDE.md"
    [[ "$output" == *"/forge-start"* ]]
    [[ "$output" == *"/forge-stop"* ]]
    [[ "$output" == *"/forge-status"* ]]
}

# ==============================================================================
# Orchestration mode instructions
# ==============================================================================

@test "generate-claude-md: agent-teams orchestration generates Agent Teams instructions" {
    create_test_config "mvp" "co-pilot" "agent-teams"
    export MOCK_YQ_ORCHESTRATION="agent-teams"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "${PROJECT_DIR}/CLAUDE.md"
    [[ "$output" == *"Agent Teams Mode"* ]]
    [[ "$output" == *"Agent tool"* ]]
}

@test "generate-claude-md: tmux orchestration generates tmux instructions" {
    create_test_config "mvp" "co-pilot" "tmux"
    export MOCK_YQ_ORCHESTRATION="tmux"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "${PROJECT_DIR}/CLAUDE.md"
    [[ "$output" == *"tmux Mode"* ]]
    [[ "$output" == *"spawn-agent.sh"* ]]
    [[ "$output" == *"file queue"* ]]
}

# ==============================================================================
# Resume context from snapshot
# ==============================================================================

@test "generate-claude-md: resume context appears when snapshot exists" {
    create_test_config

    # Create a snapshot file in the shared directory
    create_snapshot_file "snapshot-resume-test" 3

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "${PROJECT_DIR}/CLAUDE.md"
    [[ "$output" == *"Resume Context"* ]]
    [[ "$output" == *"Previous Session Found"* ]]
    [[ "$output" == *"snapshot"* ]]
}

@test "generate-claude-md: no resume section when no snapshots exist" {
    create_test_config

    # Remove all snapshots
    rm -rf "${SHARED_DIR}/.snapshots"
    mkdir -p "${SHARED_DIR}/.snapshots"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "${PROJECT_DIR}/CLAUDE.md"
    [[ "$output" != *"Resume Context"* ]]
}

# ==============================================================================
# Agent roster
# ==============================================================================

@test "generate-claude-md: output lists agent roster" {
    create_test_config

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "${PROJECT_DIR}/CLAUDE.md"
    [[ "$output" == *"Agent Roster"* ]]
    [[ "$output" == *"backend-developer"* ]]
    [[ "$output" == *"architect"* ]]
}

@test "generate-claude-md: output contains Forge directory paths" {
    create_test_config

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "${PROJECT_DIR}/CLAUDE.md"
    [[ "$output" == *"Forge Directory"* ]]
    [[ "$output" == *"scripts/"* ]]
    [[ "$output" == *"agents/"* ]]
}
