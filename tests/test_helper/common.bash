#!/usr/bin/env bash
# ==============================================================================
# Forge — BATS Shared Test Setup
# ==============================================================================
# Loaded by all test files via: load 'test_helper/common'
# Provides BATS libraries, temp dirs, and helper functions.

# Resolve paths relative to the repo root (two levels up from this file)
FORGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export FORGE_ROOT

# Load BATS test libraries
load "${FORGE_ROOT}/tests/test_helper/bats-support/load"
load "${FORGE_ROOT}/tests/test_helper/bats-assert/load"
load "${FORGE_ROOT}/tests/test_helper/bats-file/load"

# --- Setup / Teardown ---

# Create a temp directory structure that mimics a forge runtime environment.
# Called automatically before each test via setup().
create_test_environment() {
    export TEST_TEMP_DIR
    TEST_TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/forge-test-XXXXXXXX")"

    # Mimic FORGE_DIR
    export FORGE_DIR="${TEST_TEMP_DIR}/forge"
    mkdir -p "${FORGE_DIR}/scripts"
    mkdir -p "${FORGE_DIR}/agents"
    mkdir -p "${FORGE_DIR}/config"
    mkdir -p "${FORGE_DIR}/.claude/commands"

    # Copy actual scripts under test
    cp "${FORGE_ROOT}/forge" "${FORGE_DIR}/forge"
    chmod +x "${FORGE_DIR}/forge"
    cp "${FORGE_ROOT}/setup.sh" "${FORGE_DIR}/setup.sh"
    chmod +x "${FORGE_DIR}/setup.sh"
    for script in "${FORGE_ROOT}/scripts/"*.sh; do
        cp "$script" "${FORGE_DIR}/scripts/"
        chmod +x "${FORGE_DIR}/scripts/$(basename "$script")"
    done

    # Copy cockpit scripts
    if [[ -d "${FORGE_ROOT}/scripts/cockpit" ]]; then
        mkdir -p "${FORGE_DIR}/scripts/cockpit"
        for script in "${FORGE_ROOT}/scripts/cockpit/"*.sh; do
            [[ -f "$script" ]] || continue
            cp "$script" "${FORGE_DIR}/scripts/cockpit/"
            chmod +x "${FORGE_DIR}/scripts/cockpit/$(basename "$script")"
        done
    fi

    # Copy VERSION file
    if [[ -f "${FORGE_ROOT}/VERSION" ]]; then
        cp "${FORGE_ROOT}/VERSION" "${FORGE_DIR}/VERSION"
    fi

    # Copy agent templates
    for agent in "${FORGE_ROOT}/agents/"*.md; do
        cp "$agent" "${FORGE_DIR}/agents/"
    done

    # Mimic shared/ runtime dirs
    export SHARED_DIR="${FORGE_DIR}/shared"
    mkdir -p "${SHARED_DIR}/.queue"
    mkdir -p "${SHARED_DIR}/.status"
    mkdir -p "${SHARED_DIR}/.memory"
    mkdir -p "${SHARED_DIR}/.decisions"
    mkdir -p "${SHARED_DIR}/.iterations"
    mkdir -p "${SHARED_DIR}/.artifacts"
    mkdir -p "${SHARED_DIR}/.locks"
    mkdir -p "${SHARED_DIR}/.logs"
    mkdir -p "${SHARED_DIR}/.logs/archive"
    mkdir -p "${SHARED_DIR}/.snapshots"
    mkdir -p "${SHARED_DIR}/.secrets"
    mkdir -p "${SHARED_DIR}/.human"

    # Create a mock project directory
    export PROJECT_DIR="${TEST_TEMP_DIR}/project"
    mkdir -p "${PROJECT_DIR}"

    # Prepend mock-bin to PATH so external tools resolve to mocks
    export ORIGINAL_PATH="$PATH"
    export PATH="${FORGE_ROOT}/tests/test_helper/mock-bin:${PATH}"

    # Mock invocation log directory
    export MOCK_LOG_DIR="${TEST_TEMP_DIR}/mock-logs"
    mkdir -p "$MOCK_LOG_DIR"
}

# Clean up temp directory after each test
destroy_test_environment() {
    if [[ -n "${TEST_TEMP_DIR:-}" && -d "$TEST_TEMP_DIR" ]]; then
        rm -rf "$TEST_TEMP_DIR"
    fi
}

# --- Helper Functions ---

# Create a minimal valid team-config.yaml in the test FORGE_DIR
create_test_config() {
    local mode="${1:-mvp}"
    local strategy="${2:-co-pilot}"
    local orchestration="${3:-agent-teams}"

    cat > "${FORGE_DIR}/config/team-config.yaml" <<EOF
project:
  description: "Test Project"
  requirements_file: "config/project-requirements.md"
  type: "new"
  existing_project_path: ""
  directory: "${PROJECT_DIR}"

mode: "${mode}"
strategy: "${strategy}"
orchestration: "${orchestration}"

cost:
  max_development_cost: 50
  max_project_runtime_cost: "no-cap"

agents:
  team_profile: "auto"
  exclude: []
  additional: []
  include: []

claude_md:
  source: "none"
  priority: "project-first"
  global_path: ""
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

    # Also create a minimal project-requirements.md
    echo "# Test Requirements" > "${FORGE_DIR}/config/project-requirements.md"
}

# Create a status JSON file for a mock agent
create_status_file() {
    local agent_name="$1"
    local status="${2:-idle}"
    local task="${3:-Initializing}"
    local cost="${4:-0.0}"

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    cat > "${SHARED_DIR}/.status/${agent_name}.json" <<EOF
{
  "agent": "${agent_name}",
  "status": "${status}",
  "current_task": "${task}",
  "blockers": [],
  "iteration": 0,
  "last_updated": "${timestamp}",
  "session_start": "${timestamp}",
  "artifacts_produced": [],
  "estimated_completion": "",
  "messages_processed": 0,
  "usage_limits": {
    "warnings_detected": 0,
    "last_warning_at": null,
    "status": "normal"
  },
  "cost_estimate_usd": ${cost}
}
EOF
}

# Create a snapshot file for resume testing
create_snapshot_file() {
    local snapshot_id="${1:-snapshot-test}"
    local agent_count="${2:-2}"

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local unix_ts
    unix_ts=$(date +%s)

    local agents_json="["
    for i in $(seq 1 "$agent_count"); do
        [[ $i -gt 1 ]] && agents_json="${agents_json},"
        agents_json="${agents_json}
    {
      \"name\": \"agent-${i}\",
      \"type\": \"backend-developer\",
      \"instance_id\": \"${i}\",
      \"status\": \"idle\",
      \"current_task\": \"Task ${i}\",
      \"memory_file\": \"shared/.memory/agent-${i}-memory.md\",
      \"last_updated\": \"${timestamp}\",
      \"unprocessed_messages\": 0,
      \"file_locks_held\": []
    }"
    done
    agents_json="${agents_json}]"

    local snapshot_file="${SHARED_DIR}/.snapshots/${snapshot_id}.json"

    cat > "$snapshot_file" <<EOF
{
  "snapshot_id": "${snapshot_id}",
  "timestamp": "${timestamp}",
  "project": {
    "name": "test-project",
    "mode": "mvp",
    "strategy": "co-pilot",
    "project_dir": "${PROJECT_DIR}",
    "config_path": "config/team-config.yaml"
  },
  "iteration": {
    "current": 1,
    "phase": "EXECUTE",
    "last_verified_tag": "none",
    "summary": "Test snapshot"
  },
  "agents": ${agents_json},
  "git": {
    "current_branch": "main",
    "active_branches": [],
    "uncommitted_changes": false,
    "last_tag": "none"
  },
  "costs": {
    "total_development_cost_usd": 5.0,
    "cost_cap_usd": "50",
    "per_agent_costs": {}
  },
  "pending_decisions": [],
  "human_overrides_pending": false
}
EOF

    echo "$snapshot_file"
}
