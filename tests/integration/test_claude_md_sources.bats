#!/usr/bin/env bats
# ==============================================================================
# Integration: CLAUDE.md source resolution (global, project, both, none)
# ==============================================================================
load '../test_helper/common'

setup() {
    create_test_environment
    export MOCK_YQ_PASSTHROUGH="true"
}

teardown() {
    destroy_test_environment
}

create_config_with_claude_md() {
    local source="$1"
    local priority="${2:-project-first}"
    local global_path="${3:-}"

    cat > "${FORGE_DIR}/config/team-config.yaml" <<EOF
project:
  description: "Test Project"
  requirements_file: ""
  type: "new"
  existing_project_path: ""
  directory: "${PROJECT_DIR}"

mode: "mvp"
strategy: "co-pilot"
orchestration: "agent-teams"

cost:
  max_development_cost: 50
  max_project_runtime_cost: "no-cap"

agents:
  team_profile: "auto"
  exclude: []
  additional: []
  include: []

claude_md:
  source: "${source}"
  priority: "${priority}"
  global_path: "${global_path}"
  project_path: ""

tech_stack:
  languages: []
  frameworks: []
  databases: []
  infrastructure: []

llm_gateway:
  local_claude_model: "claude-sonnet-4-20250514"
  enable_local_claude: true
  cost_tracking: true

bootstrap_template: "auto"

session:
  snapshot_retention: 5
  auto_stop_after_hours: 0
  shutdown_grace_period_seconds: 60

usage_limits:
  proactive_save_interval_hours: 4
  estimated_refresh_window_hours: 1
  auto_resume_after_limit: true
  fleet_limit_threshold: 3
  scheduled_resume_time: ""
EOF
}

@test "claude_md source=none: no user conventions in output" {
    create_config_with_claude_md "none"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" \
        --project-dir "$PROJECT_DIR" \
        --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "$PROJECT_DIR/CLAUDE.md"
    # Should NOT have user conventions section
    [[ "$output" != *"User's CLAUDE.md Conventions"* ]]
}

@test "claude_md source=global: includes global CLAUDE.md" {
    local global_path="${TEST_TEMP_DIR}/global-claude.md"
    echo "# Global Convention: always use tabs" > "$global_path"

    create_config_with_claude_md "global" "project-first" "$global_path"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" \
        --project-dir "$PROJECT_DIR" \
        --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    run cat "$PROJECT_DIR/CLAUDE.md"
    [[ "$output" == *"always use tabs"* ]]
}

@test "claude_md source=project: includes project CLAUDE.md" {
    # Create a fake project CLAUDE.md that will be backed up
    echo "# Project Convention: use semicolons" > "${PROJECT_DIR}/CLAUDE.md"

    create_config_with_claude_md "project"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" \
        --project-dir "$PROJECT_DIR" \
        --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    # The script backs up existing CLAUDE.md, then regenerates with conventions
    run cat "$PROJECT_DIR/CLAUDE.md"
    [[ "$output" == *"use semicolons"* ]]
}

@test "claude_md source=both priority=project-first: project first in output" {
    local global_path="${TEST_TEMP_DIR}/global-claude.md"
    echo "GLOBAL_MARKER_ABC" > "$global_path"
    echo "PROJECT_MARKER_XYZ" > "${PROJECT_DIR}/CLAUDE.md"

    create_config_with_claude_md "both" "project-first" "$global_path"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" \
        --project-dir "$PROJECT_DIR" \
        --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    local content
    content=$(cat "$PROJECT_DIR/CLAUDE.md")
    [[ "$content" == *"PROJECT_MARKER_XYZ"* ]]
    [[ "$content" == *"GLOBAL_MARKER_ABC"* ]]

    # Project should come before global (project-first)
    local proj_pos
    local global_pos
    proj_pos=$(echo "$content" | grep -n "PROJECT_MARKER_XYZ" | head -1 | cut -d: -f1)
    global_pos=$(echo "$content" | grep -n "GLOBAL_MARKER_ABC" | head -1 | cut -d: -f1)
    [ "$proj_pos" -lt "$global_pos" ]
}

@test "claude_md source=both priority=global-first: global first in output" {
    local global_path="${TEST_TEMP_DIR}/global-claude.md"
    echo "GLOBAL_MARKER_ABC" > "$global_path"
    echo "PROJECT_MARKER_XYZ" > "${PROJECT_DIR}/CLAUDE.md"

    create_config_with_claude_md "both" "global-first" "$global_path"

    run bash "$FORGE_DIR/scripts/generate-claude-md.sh" \
        --project-dir "$PROJECT_DIR" \
        --config "$FORGE_DIR/config/team-config.yaml"
    [ "$status" -eq 0 ]

    local content
    content=$(cat "$PROJECT_DIR/CLAUDE.md")
    [[ "$content" == *"PROJECT_MARKER_XYZ"* ]]
    [[ "$content" == *"GLOBAL_MARKER_ABC"* ]]

    # Global should come before project (global-first)
    local proj_pos
    local global_pos
    proj_pos=$(echo "$content" | grep -n "PROJECT_MARKER_XYZ" | head -1 | cut -d: -f1)
    global_pos=$(echo "$content" | grep -n "GLOBAL_MARKER_ABC" | head -1 | cut -d: -f1)
    [ "$global_pos" -lt "$proj_pos" ]
}
