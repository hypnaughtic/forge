#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
}

teardown() {
    destroy_test_environment
}

# ==============================================================================
# Required argument validation
# ==============================================================================

@test "broadcast exits 1 when both --type and --message are missing" {
    run bash "$FORGE_DIR/scripts/broadcast.sh"
    assert_failure
    assert_output --partial "--type and --message are required"
}

@test "broadcast exits 1 when --type is missing" {
    run bash "$FORGE_DIR/scripts/broadcast.sh" --message "hello"
    assert_failure
    assert_output --partial "--type and --message are required"
}

@test "broadcast exits 1 when --message is missing" {
    run bash "$FORGE_DIR/scripts/broadcast.sh" --type "SHUTDOWN"
    assert_failure
    assert_output --partial "--type and --message are required"
}

# ==============================================================================
# Delivery to agent inboxes
# ==============================================================================

@test "broadcast delivers to all agent inboxes" {
    # Create 3 agent inboxes
    mkdir -p "${SHARED_DIR}/.queue/agent-alpha-inbox"
    mkdir -p "${SHARED_DIR}/.queue/agent-beta-inbox"
    mkdir -p "${SHARED_DIR}/.queue/agent-gamma-inbox"

    run bash "$FORGE_DIR/scripts/broadcast.sh" \
        --type "SHUTDOWN" \
        --message "Stop now"
    assert_success

    # Each inbox should have exactly one message file
    local count_alpha count_beta count_gamma
    count_alpha=$(ls -1 "${SHARED_DIR}/.queue/agent-alpha-inbox/"*.md 2>/dev/null | wc -l)
    count_beta=$(ls -1 "${SHARED_DIR}/.queue/agent-beta-inbox/"*.md 2>/dev/null | wc -l)
    count_gamma=$(ls -1 "${SHARED_DIR}/.queue/agent-gamma-inbox/"*.md 2>/dev/null | wc -l)

    [ "$count_alpha" -ge 1 ]
    [ "$count_beta" -ge 1 ]
    [ "$count_gamma" -ge 1 ]
}

@test "broadcast reports correct agent count" {
    mkdir -p "${SHARED_DIR}/.queue/agent-one-inbox"
    mkdir -p "${SHARED_DIR}/.queue/agent-two-inbox"
    mkdir -p "${SHARED_DIR}/.queue/agent-three-inbox"

    run bash "$FORGE_DIR/scripts/broadcast.sh" \
        --type "PAUSE" \
        --message "Pause work"
    assert_success
    assert_output --partial "3 agent(s)"
}

# ==============================================================================
# Message file content / YAML frontmatter
# ==============================================================================

@test "message file has correct YAML frontmatter fields" {
    mkdir -p "${SHARED_DIR}/.queue/test-agent-inbox"

    run bash "$FORGE_DIR/scripts/broadcast.sh" \
        --type "PREPARE_SHUTDOWN" \
        --message "Finalize work"
    assert_success

    # Find the delivered message file
    local msg_file
    msg_file=$(ls "${SHARED_DIR}/.queue/test-agent-inbox/"*.md 2>/dev/null | head -1)
    [ -n "$msg_file" ]

    run cat "$msg_file"
    assert_output --partial "from:"
    assert_output --partial "to:"
    assert_output --partial "priority:"
    assert_output --partial "timestamp:"
    assert_output --partial "type: PREPARE_SHUTDOWN"
}

# ==============================================================================
# Default values
# ==============================================================================

@test "default priority is high" {
    mkdir -p "${SHARED_DIR}/.queue/test-agent-inbox"

    run bash "$FORGE_DIR/scripts/broadcast.sh" \
        --type "INFO" \
        --message "Hello"
    assert_success

    local msg_file
    msg_file=$(ls "${SHARED_DIR}/.queue/test-agent-inbox/"*.md 2>/dev/null | head -1)
    [ -n "$msg_file" ]

    run cat "$msg_file"
    assert_output --partial "priority: high"
}

@test "default from is system" {
    mkdir -p "${SHARED_DIR}/.queue/test-agent-inbox"

    run bash "$FORGE_DIR/scripts/broadcast.sh" \
        --type "INFO" \
        --message "Hello"
    assert_success

    local msg_file
    msg_file=$(ls "${SHARED_DIR}/.queue/test-agent-inbox/"*.md 2>/dev/null | head -1)
    [ -n "$msg_file" ]

    run cat "$msg_file"
    assert_output --partial "from: system"
}

# ==============================================================================
# Custom --priority and --from
# ==============================================================================

@test "custom --priority is written to message" {
    mkdir -p "${SHARED_DIR}/.queue/test-agent-inbox"

    run bash "$FORGE_DIR/scripts/broadcast.sh" \
        --type "ALERT" \
        --message "Urgent" \
        --priority "critical"
    assert_success

    local msg_file
    msg_file=$(ls "${SHARED_DIR}/.queue/test-agent-inbox/"*.md 2>/dev/null | head -1)
    run cat "$msg_file"
    assert_output --partial "priority: critical"
}

@test "custom --from is written to message" {
    mkdir -p "${SHARED_DIR}/.queue/test-agent-inbox"

    run bash "$FORGE_DIR/scripts/broadcast.sh" \
        --type "directive" \
        --message "Do something" \
        --from "team-leader"
    assert_success

    local msg_file
    msg_file=$(ls "${SHARED_DIR}/.queue/test-agent-inbox/"*.md 2>/dev/null | head -1)
    run cat "$msg_file"
    assert_output --partial "from: team-leader"
}

# ==============================================================================
# Atomic write — message files are .md (moved from temp)
# ==============================================================================

@test "message files are .md files" {
    mkdir -p "${SHARED_DIR}/.queue/test-agent-inbox"

    run bash "$FORGE_DIR/scripts/broadcast.sh" \
        --type "INFO" \
        --message "Test atomic write"
    assert_success

    # All files in the inbox should be .md
    local msg_file
    msg_file=$(ls "${SHARED_DIR}/.queue/test-agent-inbox/"*.md 2>/dev/null | head -1)
    [ -n "$msg_file" ]
    [[ "$msg_file" == *.md ]]
}

@test "no temp files left in inbox after broadcast" {
    mkdir -p "${SHARED_DIR}/.queue/test-agent-inbox"

    run bash "$FORGE_DIR/scripts/broadcast.sh" \
        --type "INFO" \
        --message "Clean delivery"
    assert_success

    # There should be no non-.md files in the inbox
    local non_md_count
    non_md_count=$(find "${SHARED_DIR}/.queue/test-agent-inbox/" -type f ! -name '*.md' 2>/dev/null | wc -l)
    [ "$non_md_count" -eq 0 ]
}
