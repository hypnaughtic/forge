#!/usr/bin/env bats
# ==============================================================================
# Validation: Agent markdown files have required structure
# ==============================================================================

FORGE_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
AGENTS_DIR="$FORGE_ROOT/agents"

# --- Base Agent Structure ---

@test "agent structure: _base-agent.md exists" {
    [ -f "$AGENTS_DIR/_base-agent.md" ]
}

@test "agent structure: _base-agent.md has numbered sections" {
    run grep -c '^## [0-9]' "$AGENTS_DIR/_base-agent.md"
    [ "$status" -eq 0 ]
    # Should have multiple numbered sections
    [ "$output" -ge 10 ]
}

# --- Role Agent Required Sections ---

# Each role agent should have key sections
check_agent_has_section() {
    local agent_file="$1"
    local section_pattern="$2"
    grep -qi "$section_pattern" "$agent_file"
}

@test "agent structure: all role agents reference _base-agent.md" {
    for agent_file in "$AGENTS_DIR"/*.md; do
        [[ "$(basename "$agent_file")" == "_base-agent.md" ]] && continue
        run grep -l "_base-agent" "$agent_file"
        [ "$status" -eq 0 ] || {
            echo "Missing _base-agent reference in $(basename "$agent_file")"
            return 1
        }
    done
}

@test "agent structure: team-leader.md has required sections" {
    local f="$AGENTS_DIR/team-leader.md"
    [ -f "$f" ]
    check_agent_has_section "$f" "Identity"
    check_agent_has_section "$f" "Responsibilit"
}

@test "agent structure: architect.md has required sections" {
    local f="$AGENTS_DIR/architect.md"
    [ -f "$f" ]
    check_agent_has_section "$f" "Identity"
    check_agent_has_section "$f" "Responsibilit"
}

@test "agent structure: backend-developer.md has required sections" {
    local f="$AGENTS_DIR/backend-developer.md"
    [ -f "$f" ]
    check_agent_has_section "$f" "Identity"
    check_agent_has_section "$f" "Responsibilit"
}

@test "agent structure: qa-engineer.md has required sections" {
    local f="$AGENTS_DIR/qa-engineer.md"
    [ -f "$f" ]
    check_agent_has_section "$f" "Identity"
    check_agent_has_section "$f" "Responsibilit"
}

@test "agent structure: critic.md has required sections" {
    local f="$AGENTS_DIR/critic.md"
    [ -f "$f" ]
    check_agent_has_section "$f" "Identity"
    check_agent_has_section "$f" "Responsibilit"
}

@test "agent structure: all role agents have Identity section" {
    for agent_file in "$AGENTS_DIR"/*.md; do
        [[ "$(basename "$agent_file")" == "_base-agent.md" ]] && continue
        run grep -qi "Identity" "$agent_file"
        [ "$status" -eq 0 ] || {
            echo "Missing Identity section in $(basename "$agent_file")"
            return 1
        }
    done
}

@test "agent structure: all role agents have Responsibilities section" {
    for agent_file in "$AGENTS_DIR"/*.md; do
        [[ "$(basename "$agent_file")" == "_base-agent.md" ]] && continue
        run grep -qi "Responsibilit" "$agent_file"
        [ "$status" -eq 0 ] || {
            echo "Missing Responsibilities section in $(basename "$agent_file")"
            return 1
        }
    done
}
