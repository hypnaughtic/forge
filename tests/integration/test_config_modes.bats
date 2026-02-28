#!/usr/bin/env bats
# ==============================================================================
# Integration: Config mode/strategy/orchestration combinations
# ==============================================================================
# Uses real yq against test YAML files. Mocks tmux, claude, docker.
load '../test_helper/common'

setup() {
    create_test_environment
    export MOCK_YQ_PASSTHROUGH="true"
}

teardown() {
    destroy_test_environment
}

@test "config modes: mvp+auto-pilot resolves lean profile" {
    create_test_config "mvp" "auto-pilot" "agent-teams"

    run bash "$FORGE_DIR/scripts/init-project.sh" \
        --config "$FORGE_DIR/config/team-config.yaml" \
        --project-dir "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved team profile: lean"* ]]
}

@test "config modes: mvp+co-pilot resolves lean profile" {
    create_test_config "mvp" "co-pilot" "agent-teams"

    run bash "$FORGE_DIR/scripts/init-project.sh" \
        --config "$FORGE_DIR/config/team-config.yaml" \
        --project-dir "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved team profile: lean"* ]]
}

@test "config modes: mvp+micro-manage resolves lean profile" {
    create_test_config "mvp" "micro-manage" "tmux"

    run bash "$FORGE_DIR/scripts/init-project.sh" \
        --config "$FORGE_DIR/config/team-config.yaml" \
        --project-dir "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved team profile: lean"* ]]
}

@test "config modes: production-ready+auto-pilot resolves full profile" {
    create_test_config "production-ready" "auto-pilot" "agent-teams"

    run bash "$FORGE_DIR/scripts/init-project.sh" \
        --config "$FORGE_DIR/config/team-config.yaml" \
        --project-dir "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved team profile: full"* ]]
}

@test "config modes: no-compromise+auto-pilot resolves full profile" {
    create_test_config "no-compromise" "auto-pilot" "agent-teams"

    run bash "$FORGE_DIR/scripts/init-project.sh" \
        --config "$FORGE_DIR/config/team-config.yaml" \
        --project-dir "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved team profile: full"* ]]
}

@test "config modes: auto-pilot generates skip-permissions in CLAUDE.md" {
    create_test_config "mvp" "auto-pilot" "agent-teams"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" \
        --project-dir "$PROJECT_DIR" \
        --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "$PROJECT_DIR/CLAUDE.md"
    [[ "$output" == *"Strategy**: auto-pilot"* ]]
}

@test "config modes: co-pilot generates acceptEdits in CLAUDE.md" {
    create_test_config "mvp" "co-pilot" "agent-teams"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" \
        --project-dir "$PROJECT_DIR" \
        --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "$PROJECT_DIR/CLAUDE.md"
    [[ "$output" == *"Strategy**: co-pilot"* ]]
}
