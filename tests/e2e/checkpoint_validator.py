"""Deterministic assertions on checkpoint state.

Used after every stop and resume to verify exact state continuity.
Supports both hierarchical ({type}/{name}.json) and flat ({type}.json) checkpoint paths.
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

    # -- Private path helpers --

    def _resolve_checkpoint_path(self, agent_type: str,
                                  agent_name: str | None = None) -> Path:
        """Resolve checkpoint path: hierarchical first, flat fallback."""
        if agent_name:
            hier = self.checkpoints_dir / agent_type / f"{agent_name}.json"
            if hier.exists():
                return hier
        flat = self.checkpoints_dir / f"{agent_type}.json"
        if flat.exists():
            return flat
        if agent_name:
            return hier
        return flat

    def _resolve_activity_log_path(self, agent_type: str,
                                    agent_name: str | None = None) -> Path:
        """Resolve activity log path: hierarchical first, flat fallback."""
        if agent_name:
            hier = self.checkpoints_dir / agent_type / f"{agent_name}.activity.jsonl"
            if hier.exists():
                return hier
        flat = self.checkpoints_dir / f"{agent_type}.activity.jsonl"
        if flat.exists():
            return flat
        if agent_name:
            return hier
        return flat

    # -- Existence checks --

    def assert_session_exists(self) -> dict:
        session_path = self.forge_dir / "session.json"
        assert session_path.exists(), "session.json does not exist"
        data = json.loads(session_path.read_text())
        return data

    def assert_checkpoint_exists(self, agent_type: str,
                                  agent_name: str | None = None) -> dict:
        cp_path = self._resolve_checkpoint_path(agent_type, agent_name)
        label = f"{agent_type}/{agent_name}" if agent_name else agent_type
        assert cp_path.exists(), f"Checkpoint for {label} does not exist"
        return json.loads(cp_path.read_text())

    def assert_all_agents_checkpointed(self, expected_agents: list[str]) -> None:
        for agent in expected_agents:
            self.assert_checkpoint_exists(agent)

    def assert_no_orphaned_checkpoints(
        self, expected_agents: list[str] | list[tuple[str, str]],
    ) -> None:
        expected_set: set[str] = set()
        for item in expected_agents:
            if isinstance(item, tuple):
                expected_set.add(f"{item[0]}/{item[1]}")
                expected_set.add(item[1])
            else:
                expected_set.add(item)

        # Scan flat checkpoints
        for cp_file in self.checkpoints_dir.glob("*.json"):
            if cp_file.name.endswith(".tmp"):
                continue
            agent_id = cp_file.stem
            assert agent_id in expected_set, \
                f"Orphaned checkpoint: {agent_id} (not in expected)"

        # Scan hierarchical checkpoints
        for cp_file in self.checkpoints_dir.glob("*/*.json"):
            if cp_file.name.endswith(".tmp"):
                continue
            agent_name = cp_file.stem
            agent_key = f"{cp_file.parent.name}/{agent_name}"
            assert agent_name in expected_set or agent_key in expected_set, \
                f"Orphaned checkpoint: {agent_key} (not in expected)"

    # -- Status checks --

    def assert_session_status(self, expected: str) -> None:
        data = self.assert_session_exists()
        actual = data["status"]
        # "resumed" is functionally equivalent to "running" after a resume
        if expected == "running" and actual == "resumed":
            return
        assert actual == expected, \
            f"Session status: expected '{expected}', got '{actual}'"

    def assert_agent_status(self, agent_type: str, expected: str,
                             agent_name: str | None = None) -> None:
        data = self.assert_checkpoint_exists(agent_type, agent_name)
        label = f"{agent_type}/{agent_name}" if agent_name else agent_type
        assert data["status"] == expected, \
            f"{label} status: expected '{expected}', got '{data['status']}'"

    def assert_all_agents_status(self, expected: str) -> None:
        # Scan both flat and hierarchical
        for cp_file in self.checkpoints_dir.glob("**/*.json"):
            if cp_file.name.endswith(".tmp"):
                continue
            data = json.loads(cp_file.read_text())
            assert data["status"] == expected, \
                f"{cp_file.stem} status: expected '{expected}', got '{data['status']}'"

    # -- Content checks --

    def assert_checkpoint_field(self, agent_type: str, field: str,
                                 expected: object,
                                 agent_name: str | None = None) -> None:
        data = self.assert_checkpoint_exists(agent_type, agent_name)
        label = f"{agent_type}/{agent_name}" if agent_name else agent_type
        assert data.get(field) == expected, \
            f"{label}.{field}: expected {expected!r}, got {data.get(field)!r}"

    def assert_checkpoint_field_not_empty(self, agent_type: str, field: str,
                                          agent_name: str | None = None) -> None:
        data = self.assert_checkpoint_exists(agent_type, agent_name)
        value = data.get(field)
        label = f"{agent_type}/{agent_name}" if agent_name else agent_type
        assert value, f"{label}.{field} is empty: {value!r}"

    def assert_agent_name_preserved(self, agent_type: str, expected_name: str,
                                     agent_name: str | None = None) -> None:
        data = self.assert_checkpoint_exists(agent_type, agent_name)
        assert data.get("agent_name") == expected_name, \
            f"{agent_type} name changed: expected '{expected_name}', got '{data.get('agent_name')}'"

    def assert_iteration_preserved(self, agent_type: str,
                                    expected_iteration: int,
                                    agent_name: str | None = None) -> None:
        data = self.assert_checkpoint_exists(agent_type, agent_name)
        actual = data.get("iteration", 0)
        assert actual >= expected_iteration, \
            f"{agent_type} iteration regressed: expected >= {expected_iteration}, got {actual}"

    def assert_phase_preserved(self, agent_type: str, expected_phase: str,
                                agent_name: str | None = None) -> None:
        data = self.assert_checkpoint_exists(agent_type, agent_name)
        assert data.get("phase") == expected_phase, \
            f"{agent_type} phase: expected '{expected_phase}', got '{data.get('phase')}'"

    # -- Freshness checks --

    def assert_checkpoint_fresh(self, agent_type: str,
                                 max_age_seconds: int = 120,
                                 agent_name: str | None = None) -> None:
        cp_path = self._resolve_checkpoint_path(agent_type, agent_name)
        label = f"{agent_type}/{agent_name}" if agent_name else agent_type
        assert cp_path.exists(), f"Checkpoint for {label} does not exist"
        age = time.time() - cp_path.stat().st_mtime
        assert age <= max_age_seconds, \
            f"{label} checkpoint is {age:.0f}s old (max: {max_age_seconds}s)"

    def assert_activity_log_has_entries(self, agent_type: str,
                                         min_entries: int = 1,
                                         agent_name: str | None = None) -> None:
        log_path = self._resolve_activity_log_path(agent_type, agent_name)
        label = f"{agent_type}/{agent_name}" if agent_name else agent_type
        assert log_path.exists(), f"Activity log for {label} does not exist"
        lines = [l for l in log_path.read_text().strip().split("\n") if l.strip()]
        assert len(lines) >= min_entries, \
            f"{label} activity log has {len(lines)} entries (min: {min_entries})"

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

    def assert_completed_agent_cleaned(self, agent_type: str,
                                        agent_name: str | None = None) -> None:
        cp_path = self._resolve_checkpoint_path(agent_type, agent_name)
        label = f"{agent_type}/{agent_name}" if agent_name else agent_type
        assert not cp_path.exists(), \
            f"Completed agent {label} checkpoint should be cleaned up"

    def assert_sentinel_cleaned(self) -> None:
        sentinel = self.forge_dir / "STOP_REQUESTED"
        assert not sentinel.exists(), "STOP_REQUESTED sentinel should be removed"

    # -- Compaction-specific assertions --

    def assert_compaction_count(self, agent_type: str, agent_name: str,
                                 expected_count: int) -> None:
        """Assert that compaction_count in checkpoint matches expected."""
        data = self.assert_checkpoint_exists(agent_type, agent_name)
        actual = data.get("compaction_count", 0)
        assert actual >= expected_count, (
            f"{agent_type}/{agent_name} compaction_count: "
            f"expected >= {expected_count}, got {actual}"
        )

    def assert_essential_files_populated(self, agent_type: str,
                                          agent_name: str,
                                          min_count: int = 1) -> None:
        """Assert essential_files list is populated with at least min_count entries."""
        data = self.assert_checkpoint_exists(agent_type, agent_name)
        files = data.get("essential_files", [])
        assert len(files) >= min_count, (
            f"{agent_type}/{agent_name} essential_files has {len(files)} "
            f"entries (min: {min_count})"
        )

    def assert_context_anchor_exists(self, agent_type: str,
                                      agent_name: str) -> Path:
        """Assert context anchor file exists and return its path."""
        anchor = (self.checkpoints_dir / agent_type
                  / f"{agent_name}.context-anchor.md")
        assert anchor.exists(), (
            f"Context anchor for {agent_type}/{agent_name} does not exist"
        )
        return anchor

    def assert_context_anchor_fresh(self, agent_type: str,
                                     agent_name: str,
                                     max_age_seconds: int = 900) -> None:
        """Assert context anchor was updated recently."""
        anchor = self.assert_context_anchor_exists(agent_type, agent_name)
        age = time.time() - anchor.stat().st_mtime
        assert age <= max_age_seconds, (
            f"{agent_type}/{agent_name} context anchor is {age:.0f}s old "
            f"(max: {max_age_seconds}s)"
        )

    def assert_compaction_marker_absent(self, agent_type: str,
                                         agent_name: str) -> None:
        """Assert compaction marker has been cleaned up (respawn completed)."""
        marker = (self.checkpoints_dir / agent_type
                  / f"{agent_name}.compaction-marker")
        assert not marker.exists(), (
            f"Compaction marker for {agent_type}/{agent_name} should be absent"
        )

    def assert_compaction_marker_present(self, agent_type: str,
                                          agent_name: str) -> None:
        """Assert compaction marker exists (compaction in progress)."""
        marker = (self.checkpoints_dir / agent_type
                  / f"{agent_name}.compaction-marker")
        assert marker.exists(), (
            f"Compaction marker for {agent_type}/{agent_name} should be present"
        )

    def assert_token_estimate_reset(self, agent_type: str,
                                     agent_name: str) -> None:
        """Assert activity log size is small (< 1000 bytes) after respawn."""
        log_path = self._resolve_activity_log_path(agent_type, agent_name)
        if not log_path.exists():
            return  # No log = reset
        size = log_path.stat().st_size
        assert size < 1000, (
            f"{agent_type}/{agent_name} activity log is {size} bytes "
            f"(expected < 1000 after compaction reset)"
        )

    def assert_handoff_notes_not_empty(self, agent_type: str,
                                        agent_name: str) -> None:
        """Assert handoff_notes field is non-empty in checkpoint."""
        data = self.assert_checkpoint_exists(agent_type, agent_name)
        notes = data.get("handoff_notes", "")
        assert notes, (
            f"{agent_type}/{agent_name} handoff_notes is empty"
        )

    def assert_context_summary_not_empty(self, agent_type: str,
                                          agent_name: str) -> None:
        """Assert context_summary field is non-empty in checkpoint."""
        data = self.assert_checkpoint_exists(agent_type, agent_name)
        summary = data.get("context_summary", "")
        assert summary, (
            f"{agent_type}/{agent_name} context_summary is empty"
        )

    def assert_compaction_state_continuity(
        self, before: SessionSnapshot, after: SessionSnapshot,
    ) -> list[str]:
        """Extended state continuity check including compaction fields.

        Returns violations list (empty = pass).
        """
        violations = self.assert_state_continuity(before, after)

        for agent in set(before.checkpoints) & set(after.checkpoints):
            pre = before.checkpoints[agent]
            post = after.checkpoints[agent]

            # compaction_count must be monotonically increasing
            pre_cc = pre.get("compaction_count", 0)
            post_cc = post.get("compaction_count", 0)
            if post_cc < pre_cc:
                violations.append(
                    f"{agent} compaction_count regressed: {pre_cc} -> {post_cc}"
                )

            # essential_files must be superset (no files lost)
            pre_ef = set(pre.get("essential_files", []))
            post_ef = set(post.get("essential_files", []))
            lost_files = pre_ef - post_ef
            if lost_files:
                violations.append(
                    f"{agent} lost essential_files: {lost_files}"
                )

            # context_anchor_updated_at must not regress
            pre_anchor = pre.get("context_anchor_updated_at", "")
            post_anchor = post.get("context_anchor_updated_at", "")
            if pre_anchor and post_anchor and post_anchor < pre_anchor:
                violations.append(
                    f"{agent} context_anchor regressed: "
                    f"{pre_anchor} -> {post_anchor}"
                )

        return violations
