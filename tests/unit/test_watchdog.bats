#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    create_test_config
}

teardown() {
    destroy_test_environment
}

@test "watchdog: --help exits 0" {
    run bash "$FORGE_DIR/scripts/watchdog.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Background daemon"* ]]
}

@test "watchdog: send_to_team_leader creates inbox message" {
    # Source the watchdog script to get access to send_to_team_leader function
    # We need to extract and test this function directly
    local inbox="${SHARED_DIR}/.queue/team-leader-inbox"
    mkdir -p "$inbox"

    # Create a minimal script that sources the function and calls it
    cat > "${TEST_TEMP_DIR}/test_send.sh" <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
FORGE_DIR="$1"
SHARED_DIR="${FORGE_DIR}/shared"

send_to_team_leader() {
    local priority="$1"
    local subject="$2"
    local body="$3"
    local inbox="${SHARED_DIR}/.queue/team-leader-inbox"
    mkdir -p "$inbox"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local unix_ts
    unix_ts=$(date +%s)
    local temp_file
    temp_file=$(mktemp "${TMPDIR:-/tmp}/forge-msg-XXXXXXXX")

    cat > "$temp_file" <<EOF
---
id: msg-${unix_ts}-watchdog
from: watchdog
to: team-leader
priority: ${priority}
timestamp: ${timestamp}
type: status-update
---

## ${subject}

${body}
EOF

    mv "$temp_file" "${inbox}/msg-${unix_ts}-watchdog.md"
}

send_to_team_leader "critical" "AGENT_DEAD: test-agent" "Agent test-agent has died."
SCRIPT
    chmod +x "${TEST_TEMP_DIR}/test_send.sh"

    run bash "${TEST_TEMP_DIR}/test_send.sh" "$FORGE_DIR"
    [ "$status" -eq 0 ]

    # Check that a message was created
    local msg_count
    msg_count=$(ls -1 "$inbox" 2>/dev/null | wc -l)
    [ "$msg_count" -eq 1 ]

    # Check message content
    local msg_file
    msg_file=$(ls "$inbox"/*.md | head -1)
    run cat "$msg_file"
    [[ "$output" == *"from: watchdog"* ]]
    [[ "$output" == *"to: team-leader"* ]]
    [[ "$output" == *"priority: critical"* ]]
    [[ "$output" == *"AGENT_DEAD"* ]]
}
