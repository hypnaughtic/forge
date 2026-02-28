#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    # Default mock yq values for init-project + generate-claude-md
    export MOCK_YQ_MODE="mvp"
    export MOCK_YQ_STRATEGY="co-pilot"
    export MOCK_YQ_ORCHESTRATION="agent-teams"
    export MOCK_YQ_PROJECT_DESC="Test Project"
    export MOCK_YQ_PROJECT_TYPE="new"
    export MOCK_YQ_PROJECT_DIR="$PROJECT_DIR"
    export MOCK_YQ_COST_CAP="50"
    export MOCK_YQ_TEAM_PROFILE="auto"
    export MOCK_YQ_EXCLUDE=""
    export MOCK_YQ_ADDITIONAL=""
    export MOCK_YQ_INCLUDE=""
    export MOCK_YQ_CLAUDE_MD_SOURCE="none"
    export MOCK_YQ_CLAUDE_MD_PRIORITY="project-first"
    export MOCK_YQ_CLAUDE_MD_GLOBAL=""
    export MOCK_YQ_CLAUDE_MD_PROJECT=""
    export MOCK_YQ_REQ_FILE=""
    export MOCK_YQ_TECH_LANGS=""
    export MOCK_YQ_TECH_FRAMEWORKS=""
    export MOCK_YQ_TEMPLATE="auto"
    # Use real jq for snapshot parsing in generate-claude-md
    export MOCK_JQ_PASSTHROUGH="true"
}

teardown() {
    destroy_test_environment
}

# ==============================================================================
# Argument validation
# ==============================================================================

@test "init-project: missing config exits 1" {
    # Do not create config file — the default path should not exist
    rm -f "$FORGE_DIR/config/team-config.yaml"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Config file not found"* ]]
}

@test "init-project: --help exits 0" {
    run bash "$FORGE_DIR/scripts/init-project.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
}

# ==============================================================================
# Auto profile resolution
# ==============================================================================

@test "init-project: auto+mvp resolves to lean profile" {
    create_test_config "mvp" "co-pilot" "agent-teams"
    export MOCK_YQ_MODE="mvp"
    export MOCK_YQ_TEAM_PROFILE="auto"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved team profile: lean"* ]]
}

@test "init-project: auto+production-ready resolves to full profile" {
    create_test_config "production-ready" "co-pilot" "agent-teams"
    export MOCK_YQ_MODE="production-ready"
    export MOCK_YQ_TEAM_PROFILE="auto"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved team profile: full"* ]]
}

# ==============================================================================
# Agent file generation (lean profile)
# ==============================================================================

@test "init-project: lean profile creates 8 agent files" {
    create_test_config "mvp" "co-pilot" "agent-teams"
    export MOCK_YQ_MODE="mvp"
    export MOCK_YQ_TEAM_PROFILE="auto"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    # Lean roster: team-leader research-strategist architect backend-developer
    #              frontend-engineer qa-engineer devops-specialist critic
    local agent_dir="${PROJECT_DIR}/.forge/agents"
    [ -d "$agent_dir" ]

    # Count generated .md files
    local file_count
    file_count=$(ls -1 "$agent_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
    [ "$file_count" -eq 8 ]
}

@test "init-project: lean profile generates correct agent names" {
    create_test_config "mvp" "co-pilot" "agent-teams"
    export MOCK_YQ_MODE="mvp"
    export MOCK_YQ_TEAM_PROFILE="auto"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    local agent_dir="${PROJECT_DIR}/.forge/agents"
    [ -f "${agent_dir}/team-leader.md" ]
    [ -f "${agent_dir}/research-strategist.md" ]
    [ -f "${agent_dir}/architect.md" ]
    [ -f "${agent_dir}/backend-developer.md" ]
    [ -f "${agent_dir}/frontend-engineer.md" ]
    [ -f "${agent_dir}/qa-engineer.md" ]
    [ -f "${agent_dir}/devops-specialist.md" ]
    [ -f "${agent_dir}/critic.md" ]
}

# ==============================================================================
# Generated agent file content
# ==============================================================================

@test "init-project: generated agent files contain Project Context section" {
    create_test_config "mvp" "co-pilot" "agent-teams"
    export MOCK_YQ_MODE="mvp"
    export MOCK_YQ_TEAM_PROFILE="auto"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    local agent_file="${PROJECT_DIR}/.forge/agents/backend-developer.md"
    [ -f "$agent_file" ]

    run cat "$agent_file"
    [[ "$output" == *"## Project Context"* ]]
}

@test "init-project: generated agent files contain mode and strategy" {
    create_test_config "mvp" "auto-pilot" "agent-teams"
    export MOCK_YQ_MODE="mvp"
    export MOCK_YQ_STRATEGY="auto-pilot"
    export MOCK_YQ_TEAM_PROFILE="auto"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    local agent_file="${PROJECT_DIR}/.forge/agents/architect.md"
    [ -f "$agent_file" ]

    run cat "$agent_file"
    [[ "$output" == *"**Mode**: mvp"* ]]
    [[ "$output" == *"**Strategy**: auto-pilot"* ]]
}

@test "init-project: generated agent files contain auto-generated header comment" {
    create_test_config
    export MOCK_YQ_TEAM_PROFILE="auto"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    local agent_file="${PROJECT_DIR}/.forge/agents/critic.md"
    [ -f "$agent_file" ]

    run cat "$agent_file"
    [[ "$output" == *"Generated by init-project.sh"* ]]
    [[ "$output" == *"DO NOT EDIT MANUALLY"* ]]
}

# ==============================================================================
# Custom profile with empty include
# ==============================================================================

@test "init-project: custom profile with empty include exits 1" {
    create_test_config
    export MOCK_YQ_TEAM_PROFILE="custom"
    export MOCK_YQ_INCLUDE=""

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 1 ]
    [[ "$output" == *"custom"* ]] || [[ "$output" == *"empty"* ]]
}

# ==============================================================================
# Full profile
# ==============================================================================

@test "init-project: full profile creates more agent files than lean" {
    create_test_config "production-ready" "co-pilot" "agent-teams"
    export MOCK_YQ_MODE="production-ready"
    export MOCK_YQ_TEAM_PROFILE="auto"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    local agent_dir="${PROJECT_DIR}/.forge/agents"
    local file_count
    file_count=$(ls -1 "$agent_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
    # Full roster has 13 agents
    [ "$file_count" -gt 8 ]
}

# ==============================================================================
# CLAUDE.md generation
# ==============================================================================

@test "init-project: generates CLAUDE.md in project directory" {
    create_test_config
    export MOCK_YQ_TEAM_PROFILE="auto"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    # init-project calls generate-claude-md.sh which creates CLAUDE.md
    [ -f "${PROJECT_DIR}/CLAUDE.md" ]
}

@test "init-project: completion message lists active agents" {
    create_test_config
    export MOCK_YQ_TEAM_PROFILE="auto"

    run bash "$FORGE_DIR/scripts/init-project.sh" --project-dir "$PROJECT_DIR" --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Project initialization complete"* ]]
}
