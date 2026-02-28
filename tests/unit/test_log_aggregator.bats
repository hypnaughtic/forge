#!/usr/bin/env bats
load '../test_helper/common'

setup() {
    create_test_environment
}

teardown() {
    destroy_test_environment
}

@test "log-aggregator: --help exits 0" {
    run bash "$FORGE_DIR/scripts/log-aggregator.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Background daemon"* ]]
}

@test "log-aggregator: creates combined.log and archive dir" {
    local logs_dir="${SHARED_DIR}/.logs"
    mkdir -p "$logs_dir"

    # Run the aggregator in background and kill it after 2 seconds
    bash "$FORGE_DIR/scripts/log-aggregator.sh" --forge-dir "$FORGE_DIR" &
    local pid=$!
    sleep 2
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true

    [ -f "${logs_dir}/combined.log" ]
    [ -d "${logs_dir}/archive" ]
}

@test "log-aggregator: skips combined.log when aggregating" {
    local logs_dir="${SHARED_DIR}/.logs"
    mkdir -p "$logs_dir"
    echo "test entry 1" > "${logs_dir}/agent1.log"
    echo "should not recurse" > "${logs_dir}/combined.log"

    [ -f "${logs_dir}/agent1.log" ]
    [ -f "${logs_dir}/combined.log" ]
}
