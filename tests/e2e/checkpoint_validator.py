"""Deterministic assertions on checkpoint state.

Used after every stop and resume to verify exact state continuity.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from tests.e2e.tmux_helpers import SessionSnapshot


class CheckpointValidator:
    """Deterministic assertions on checkpoint state."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.forge_dir = project_dir / ".forge"
        self.checkpoints_dir = self.forge_dir / "checkpoints"

    # -- Existence checks --

    def assert_session_exists(self) -> dict:
        session_path = self.forge_dir / "session.json"
        assert session_path.exists(), "session.json does not exist"
        data = json.loads(session_path.read_text())
        return data

    def assert_checkpoint_exists(self, agent_type: str) -> dict:
        cp_path = self.checkpoints_dir / f"{agent_type}.json"
        assert cp_path.exists(), f"Checkpoint for {agent_type} does not exist"
        return json.loads(cp_path.read_text())

    def assert_all_agents_checkpointed(self, expected_agents: list[str]) -> None:
        for agent in expected_agents:
            self.assert_checkpoint_exists(agent)

    def assert_no_orphaned_checkpoints(self, expected_agents: list[str]) -> None:
        expected_set = set(expected_agents)
        for cp_file in self.checkpoints_dir.glob("*.json"):
            if cp_file.name.endswith(".tmp"):
                continue
            agent_type = cp_file.stem
            assert agent_type in expected_set, \
                f"Orphaned checkpoint: {agent_type} (not in expected: {expected_agents})"

    # -- Status checks --

    def assert_session_status(self, expected: str) -> None:
        data = self.assert_session_exists()
        assert data["status"] == expected, \
            f"Session status: expected '{expected}', got '{data['status']}'"

    def assert_agent_status(self, agent_type: str, expected: str) -> None:
        data = self.assert_checkpoint_exists(agent_type)
        assert data["status"] == expected, \
            f"{agent_type} status: expected '{expected}', got '{data['status']}'"

    def assert_all_agents_status(self, expected: str) -> None:
        for cp_file in self.checkpoints_dir.glob("*.json"):
            if cp_file.name.endswith(".tmp"):
                continue
            data = json.loads(cp_file.read_text())
            assert data["status"] == expected, \
                f"{cp_file.stem} status: expected '{expected}', got '{data['status']}'"

    # -- Content checks --

    def assert_checkpoint_field(self, agent_type: str, field: str, expected: object) -> None:
        data = self.assert_checkpoint_exists(agent_type)
        assert data.get(field) == expected, \
            f"{agent_type}.{field}: expected {expected!r}, got {data.get(field)!r}"

    def assert_checkpoint_field_not_empty(self, agent_type: str, field: str) -> None:
        data = self.assert_checkpoint_exists(agent_type)
        value = data.get(field)
        assert value, f"{agent_type}.{field} is empty: {value!r}"

    def assert_agent_name_preserved(self, agent_type: str, expected_name: str) -> None:
        data = self.assert_checkpoint_exists(agent_type)
        assert data.get("agent_name") == expected_name, \
            f"{agent_type} name changed: expected '{expected_name}', got '{data.get('agent_name')}'"

    def assert_iteration_preserved(self, agent_type: str, expected_iteration: int) -> None:
        data = self.assert_checkpoint_exists(agent_type)
        actual = data.get("iteration", 0)
        assert actual >= expected_iteration, \
            f"{agent_type} iteration regressed: expected >= {expected_iteration}, got {actual}"

    def assert_phase_preserved(self, agent_type: str, expected_phase: str) -> None:
        data = self.assert_checkpoint_exists(agent_type)
        assert data.get("phase") == expected_phase, \
            f"{agent_type} phase: expected '{expected_phase}', got '{data.get('phase')}'"

    # -- Freshness checks --

    def assert_checkpoint_fresh(self, agent_type: str, max_age_seconds: int = 120) -> None:
        cp_path = self.checkpoints_dir / f"{agent_type}.json"
        assert cp_path.exists(), f"Checkpoint for {agent_type} does not exist"
        age = time.time() - cp_path.stat().st_mtime
        assert age <= max_age_seconds, \
            f"{agent_type} checkpoint is {age:.0f}s old (max: {max_age_seconds}s)"

    def assert_activity_log_has_entries(self, agent_type: str, min_entries: int = 1) -> None:
        log_path = self.checkpoints_dir / f"{agent_type}.activity.jsonl"
        assert log_path.exists(), f"Activity log for {agent_type} does not exist"
        lines = [l for l in log_path.read_text().strip().split("\n") if l.strip()]
        assert len(lines) >= min_entries, \
            f"{agent_type} activity log has {len(lines)} entries (min: {min_entries})"

    # -- Cross-snapshot comparison --

    def assert_state_continuity(self, before: SessionSnapshot, after: SessionSnapshot) -> list[str]:
        """Compare two snapshots and verify state continuity.

        Returns list of violations (empty = pass).
        """
        violations: list[str] = []

        # Same agent types present
        before_agents = set(before.checkpoints.keys())
        after_agents = set(after.checkpoints.keys())
        missing = before_agents - after_agents
        for agent in missing:
            # Only flag if agent wasn't complete
            status = before.checkpoints.get(agent, {}).get("status", "")
            if status not in ("complete",):
                violations.append(f"{agent} missing after resume (was {status})")

        # Per-agent checks
        for agent in before_agents & after_agents:
            pre = before.checkpoints[agent]
            post = after.checkpoints[agent]

            # Agent name must be preserved
            if pre.get("agent_name") != post.get("agent_name"):
                violations.append(
                    f"{agent} name changed: {pre.get('agent_name')} -> {post.get('agent_name')}"
                )

            # Iteration must not regress
            pre_iter = pre.get("iteration", 0)
            post_iter = post.get("iteration", 0)
            if post_iter < pre_iter:
                violations.append(
                    f"{agent} iteration regressed: {pre_iter} -> {post_iter}"
                )

            # Cost must accumulate, not reset
            pre_cost = pre.get("cost_usd", 0)
            post_cost = post.get("cost_usd", 0)
            if post_cost < pre_cost:
                violations.append(
                    f"{agent} cost reset: {pre_cost} -> {post_cost}"
                )

            # Completed tasks must be superset
            pre_completed = {t.get("id", "") for t in pre.get("completed_tasks", [])}
            post_completed = {t.get("id", "") for t in post.get("completed_tasks", [])}
            lost_tasks = pre_completed - post_completed
            if lost_tasks:
                violations.append(f"{agent} lost completed tasks: {lost_tasks}")

        return violations

    # -- Hierarchy checks --

    def assert_hierarchy_intact(self, expected_tree: dict) -> None:
        """Verify parent-child relationships match expected tree."""
        for agent, expected_parent in expected_tree.items():
            data = self.assert_checkpoint_exists(agent)
            actual_parent = data.get("parent_agent")
            assert actual_parent == expected_parent, \
                f"{agent} parent: expected '{expected_parent}', got '{actual_parent}'"

    # -- Cleanup checks --

    def assert_completed_agent_cleaned(self, agent_type: str) -> None:
        cp_path = self.checkpoints_dir / f"{agent_type}.json"
        assert not cp_path.exists(), \
            f"Completed agent {agent_type} checkpoint should be cleaned up"

    def assert_sentinel_cleaned(self) -> None:
        sentinel = self.forge_dir / "STOP_REQUESTED"
        assert not sentinel.exists(), "STOP_REQUESTED sentinel should be removed"
