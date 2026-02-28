#!/usr/bin/env bats
# ==============================================================================
# Validation: Config files have required keys and valid values
# ==============================================================================

FORGE_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"

setup() {
    # Use real yq for validation tests
    REAL_YQ=$(which -a yq 2>/dev/null | head -1)
    if [[ -z "$REAL_YQ" ]]; then
        skip "yq not installed"
    fi
}

# --- team-config.yaml ---

@test "config schema: team-config.yaml has project key" {
    run yq eval '.project' "$FORGE_ROOT/config/team-config.yaml"
    [ "$status" -eq 0 ]
    [ "$output" != "null" ]
}

@test "config schema: team-config.yaml has mode key" {
    run yq eval '.mode' "$FORGE_ROOT/config/team-config.yaml"
    [ "$status" -eq 0 ]
    [ "$output" != "null" ]
}

@test "config schema: team-config.yaml has strategy key" {
    run yq eval '.strategy' "$FORGE_ROOT/config/team-config.yaml"
    [ "$status" -eq 0 ]
    [ "$output" != "null" ]
}

@test "config schema: team-config.yaml has orchestration key" {
    run yq eval '.orchestration' "$FORGE_ROOT/config/team-config.yaml"
    [ "$status" -eq 0 ]
    [ "$output" != "null" ]
}

@test "config schema: team-config.yaml has cost key" {
    run yq eval '.cost' "$FORGE_ROOT/config/team-config.yaml"
    [ "$status" -eq 0 ]
    [ "$output" != "null" ]
}

@test "config schema: team-config.yaml has agents key" {
    run yq eval '.agents' "$FORGE_ROOT/config/team-config.yaml"
    [ "$status" -eq 0 ]
    [ "$output" != "null" ]
}

@test "config schema: team-config.yaml mode is valid enum" {
    local mode
    mode=$(yq eval '.mode' "$FORGE_ROOT/config/team-config.yaml")
    [[ "$mode" == "mvp" || "$mode" == "production-ready" || "$mode" == "no-compromise" ]]
}

@test "config schema: team-config.yaml strategy is valid enum" {
    local strategy
    strategy=$(yq eval '.strategy' "$FORGE_ROOT/config/team-config.yaml")
    [[ "$strategy" == "auto-pilot" || "$strategy" == "co-pilot" || "$strategy" == "micro-manage" ]]
}

@test "config schema: team-config.yaml orchestration is valid enum" {
    local orch
    orch=$(yq eval '.orchestration' "$FORGE_ROOT/config/team-config.yaml")
    [[ "$orch" == "agent-teams" || "$orch" == "tmux" ]]
}

# --- team-config.example.yaml ---

@test "config schema: team-config.example.yaml has project key" {
    run yq eval '.project' "$FORGE_ROOT/config/team-config.example.yaml"
    [ "$status" -eq 0 ]
    [ "$output" != "null" ]
}

@test "config schema: team-config.example.yaml has mode key" {
    run yq eval '.mode' "$FORGE_ROOT/config/team-config.example.yaml"
    [ "$status" -eq 0 ]
    [ "$output" != "null" ]
}

@test "config schema: team-config.example.yaml mode is valid enum" {
    local mode
    mode=$(yq eval '.mode' "$FORGE_ROOT/config/team-config.example.yaml")
    [[ "$mode" == "mvp" || "$mode" == "production-ready" || "$mode" == "no-compromise" ]]
}

@test "config schema: team-config.example.yaml strategy is valid enum" {
    local strategy
    strategy=$(yq eval '.strategy' "$FORGE_ROOT/config/team-config.example.yaml")
    [[ "$strategy" == "auto-pilot" || "$strategy" == "co-pilot" || "$strategy" == "micro-manage" ]]
}

@test "config schema: team-config.example.yaml orchestration is valid enum" {
    local orch
    orch=$(yq eval '.orchestration' "$FORGE_ROOT/config/team-config.example.yaml")
    [[ "$orch" == "agent-teams" || "$orch" == "tmux" ]]
}
