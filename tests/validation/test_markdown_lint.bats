#!/usr/bin/env bats
# ==============================================================================
# Validation: markdownlint passes on docs, README, and slash commands
# ==============================================================================

FORGE_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"

@test "markdownlint: docs/*.md" {
    run markdownlint-cli2 "$FORGE_ROOT/docs/**/*.md"
    [ "$status" -eq 0 ]
}

@test "markdownlint: README.md" {
    run markdownlint-cli2 "$FORGE_ROOT/README.md"
    [ "$status" -eq 0 ]
}

@test "markdownlint: CHANGELOG.md" {
    if [[ ! -f "$FORGE_ROOT/CHANGELOG.md" ]]; then
        skip "CHANGELOG.md not found"
    fi
    run markdownlint-cli2 "$FORGE_ROOT/CHANGELOG.md"
    [ "$status" -eq 0 ]
}

@test "markdownlint: .claude/commands/*.md" {
    run markdownlint-cli2 "$FORGE_ROOT/.claude/commands/*.md"
    [ "$status" -eq 0 ]
}
