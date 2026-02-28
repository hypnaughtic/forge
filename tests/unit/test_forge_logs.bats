#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
    create_test_config
}

teardown() {
    destroy_test_environment
}

@test "forge logs: missing logs dir exits 1" {
    rm -rf "${SHARED_DIR}/.logs"

    run bash "$FORGE_DIR/forge" logs
    [ "$status" -eq 1 ]
    [[ "$output" == *"No logs directory"* ]]
}

@test "forge logs: --agent reads specific log" {
    local logs_dir="${SHARED_DIR}/.logs"
    echo "test log line 1" > "${logs_dir}/backend-developer.log"
    echo "test log line 2" >> "${logs_dir}/backend-developer.log"

    run bash "$FORGE_DIR/forge" logs --agent backend-developer
    [ "$status" -eq 0 ]
    [[ "$output" == *"test log line 1"* ]]
    [[ "$output" == *"test log line 2"* ]]
}

@test "forge logs: --agent nonexistent exits 1" {
    run bash "$FORGE_DIR/forge" logs --agent nonexistent
    [ "$status" -eq 1 ]
    [[ "$output" == *"No log file found"* ]]
}

@test "forge logs: no agent reads combined.log" {
    local logs_dir="${SHARED_DIR}/.logs"
    echo "combined log entry" > "${logs_dir}/combined.log"

    run bash "$FORGE_DIR/forge" logs
    [ "$status" -eq 0 ]
    [[ "$output" == *"combined log entry"* ]]
}
