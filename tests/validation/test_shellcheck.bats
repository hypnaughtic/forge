#!/usr/bin/env bats
# ==============================================================================
# Validation: shellcheck passes on all shell scripts
# ==============================================================================

FORGE_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"

@test "shellcheck: forge CLI" {
    run shellcheck "$FORGE_ROOT/forge"
    [ "$status" -eq 0 ]
}

@test "shellcheck: setup.sh" {
    run shellcheck "$FORGE_ROOT/setup.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/broadcast.sh" {
    run shellcheck "$FORGE_ROOT/scripts/broadcast.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/cost-tracker.sh" {
    run shellcheck "$FORGE_ROOT/scripts/cost-tracker.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/generate-claude-md.sh" {
    run shellcheck "$FORGE_ROOT/scripts/generate-claude-md.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/init-project.sh" {
    run shellcheck "$FORGE_ROOT/scripts/init-project.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/kill-agent.sh" {
    run shellcheck "$FORGE_ROOT/scripts/kill-agent.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/log-aggregator.sh" {
    run shellcheck "$FORGE_ROOT/scripts/log-aggregator.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/resume.sh" {
    run shellcheck "$FORGE_ROOT/scripts/resume.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/spawn-agent.sh" {
    run shellcheck "$FORGE_ROOT/scripts/spawn-agent.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/start.sh" {
    run shellcheck "$FORGE_ROOT/scripts/start.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/status.sh" {
    run shellcheck "$FORGE_ROOT/scripts/status.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/stop.sh" {
    run shellcheck "$FORGE_ROOT/scripts/stop.sh"
    [ "$status" -eq 0 ]
}

@test "shellcheck: scripts/watchdog.sh" {
    run shellcheck "$FORGE_ROOT/scripts/watchdog.sh"
    [ "$status" -eq 0 ]
}
