#!/usr/bin/env bats
# ==============================================================================
# Validation: yamllint passes on all YAML config files
# ==============================================================================

FORGE_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"

@test "yamllint: config/team-config.yaml" {
    run yamllint -c "$FORGE_ROOT/.yamllint.yml" "$FORGE_ROOT/config/team-config.yaml"
    [ "$status" -eq 0 ]
}

@test "yamllint: config/team-config.example.yaml" {
    run yamllint -c "$FORGE_ROOT/.yamllint.yml" "$FORGE_ROOT/config/team-config.example.yaml"
    [ "$status" -eq 0 ]
}
