#!/usr/bin/env bats
# ==============================================================================
# Unit Tests: Cockpit Render Utilities (scripts/cockpit/render.sh)
# ==============================================================================
# Tests color functions, truncation, box drawing, and formatting.

load '../test_helper/common'

setup() {
    create_test_environment
    # cockpit scripts are already copied by create_test_environment
    RENDER="${FORGE_DIR}/scripts/cockpit/render.sh"
}

teardown() {
    destroy_test_environment
}

# --- Truncation ---

@test "render: truncate short string unchanged" {
    source "$RENDER"
    result=$(truncate "hello" 20)
    [[ "$result" == "hello" ]]
}

@test "render: truncate long string with ellipsis" {
    source "$RENDER"
    result=$(truncate "this is a very long string that should be truncated" 20)
    [[ ${#result} -le 20 ]]
    [[ "$result" == *"..."* ]]
}

@test "render: truncate exact length unchanged" {
    source "$RENDER"
    result=$(truncate "12345" 5)
    [[ "$result" == "12345" ]]
}

# --- Format elapsed ---

@test "render: format_elapsed seconds" {
    source "$RENDER"
    result=$(format_elapsed 45)
    [[ "$result" == "45s" ]]
}

@test "render: format_elapsed minutes" {
    source "$RENDER"
    result=$(format_elapsed 300)
    [[ "$result" == "5m" ]]
}

@test "render: format_elapsed hours and minutes" {
    source "$RENDER"
    result=$(format_elapsed 5400)
    [[ "$result" == "1h 30m" ]]
}

# --- Agent abbreviations ---

@test "render: agent_abbrev known agents" {
    source "$RENDER"
    [[ "$(agent_abbrev "team-leader")" == "TL" ]]
    [[ "$(agent_abbrev "backend-developer")" == "BE" ]]
    [[ "$(agent_abbrev "frontend-engineer")" == "FE" ]]
    [[ "$(agent_abbrev "qa-engineer")" == "QA" ]]
    [[ "$(agent_abbrev "devops-specialist")" == "DO" ]]
    [[ "$(agent_abbrev "critic")" == "CR" ]]
    [[ "$(agent_abbrev "architect")" == "AR" ]]
}

@test "render: agent_abbrev unknown agent uses first 2 chars" {
    source "$RENDER"
    result=$(agent_abbrev "custom-agent")
    [[ "$result" == "cu" ]]
}

# --- Color functions produce output ---

@test "render: color_status produces output for each status" {
    source "$RENDER"
    for status in working idle blocked done review error rate-limited suspended; do
        result=$(color_status "$status")
        [[ -n "$result" ]]
    done
}

@test "render: status_dot produces output for each status" {
    source "$RENDER"
    for status in working idle blocked done review error rate-limited suspended; do
        result=$(status_dot "$status")
        [[ -n "$result" ]]
    done
}

# --- Header and separator ---

@test "render: draw_header produces output" {
    source "$RENDER"
    result=$(draw_header "TEST HEADER" 40)
    [[ -n "$result" ]]
    [[ "$result" == *"TEST HEADER"* ]]
}

@test "render: draw_separator produces output" {
    source "$RENDER"
    result=$(draw_separator 40)
    [[ -n "$result" ]]
}

# --- Color constants defined ---

@test "render: color constants are defined" {
    source "$RENDER"
    [[ -n "$CR_RESET" ]]
    [[ -n "$CR_RED" ]]
    [[ -n "$CR_GREEN" ]]
    [[ -n "$CR_YELLOW" ]]
    [[ -n "$CR_CYAN" ]]
}

# --- Box drawing characters defined ---

@test "render: box drawing characters are defined" {
    source "$RENDER"
    [[ "$BOX_H" == "─" ]]
    [[ "$BOX_V" == "│" ]]
    [[ "$BOX_TL" == "┌" ]]
    [[ "$BOX_TR" == "┐" ]]
    [[ "$BOX_BL" == "└" ]]
    [[ "$BOX_BR" == "┘" ]]
}
