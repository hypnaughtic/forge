#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    create_test_config
}

teardown() {
    destroy_test_environment
}

@test "forge tell: no args shows help" {
    # The forge tell with no args exits 0 (shows help)
    run bash "$FORGE_DIR/forge" tell
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
}

@test "forge tell: creates override.md" {
    run bash "$FORGE_DIR/forge" tell "Please refactor the auth module"
    [ "$status" -eq 0 ]
    [ -f "${SHARED_DIR}/.human/override.md" ]
}

@test "forge tell: override.md contains message" {
    run bash "$FORGE_DIR/forge" tell "Please refactor the auth module"
    [ "$status" -eq 0 ]

    run cat "${SHARED_DIR}/.human/override.md"
    [[ "$output" == *"Please refactor the auth module"* ]]
}

@test "forge tell: override.md has YAML frontmatter" {
    run bash "$FORGE_DIR/forge" tell "Test message"
    [ "$status" -eq 0 ]

    run cat "${SHARED_DIR}/.human/override.md"
    [[ "$output" == *"---"* ]]
    [[ "$output" == *"timestamp:"* ]]
    [[ "$output" == *"type: directive"* ]]
}
