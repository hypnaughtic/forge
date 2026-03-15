"""Unit tests for ghost/orphan/missing detection in validate_checkpoints_against_tree."""

from __future__ import annotations

from pathlib import Path

import pytest

from forge_cli.models import AgentCheckpoint, AgentMeta
from forge_cli.checkpoint import (
    read_all_checkpoints,
    validate_checkpoints_against_tree,
    write_checkpoint,
)


class TestGhostDetection:
    def test_ghost_registered_no_checkpoint_no_activity(self, tmp_path):
        """Agent registered but never started = ghost."""
        checkpoints_dir = tmp_path / "checkpoints"
        checkpoints_dir.mkdir()
        agent_tree = {
            "Ghost": AgentMeta(
                agent_type="dev", agent_name="Ghost", status="registered",
            ),
        }
        orphans, missing, ghosts = validate_checkpoints_against_tree(
            {}, agent_tree, checkpoints_dir,
        )
        assert "Ghost" in ghosts
        assert missing == []
        assert orphans == []

    def test_missing_started_has_activity_no_checkpoint(self, tmp_path):
        """Agent started (has activity log) but lost checkpoint = missing."""
        checkpoints_dir = tmp_path / "checkpoints"
        type_dir = checkpoints_dir / "dev"
        type_dir.mkdir(parents=True)
        (type_dir / "Lost.activity.jsonl").write_text('{"tool":"Write"}\n')

        agent_tree = {
            "Lost": AgentMeta(
                agent_type="dev", agent_name="Lost", status="active",
            ),
        }
        orphans, missing, ghosts = validate_checkpoints_against_tree(
            {}, agent_tree, checkpoints_dir,
        )
        assert "Lost" in missing
        assert ghosts == []

    def test_orphan_checkpoint_no_tree_entry(self, tmp_path):
        """Checkpoint exists but not in agent_tree = orphan."""
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(
            AgentCheckpoint(agent_type="dev", agent_name="Orphan"),
            checkpoints_dir,
        )
        checkpoints = read_all_checkpoints(checkpoints_dir)
        orphans, missing, ghosts = validate_checkpoints_against_tree(
            checkpoints, {}, checkpoints_dir,
        )
        assert "Orphan" in orphans

    def test_completed_agent_not_reported(self, tmp_path):
        """Agents with status=complete are excluded from checks."""
        checkpoints_dir = tmp_path / "checkpoints"
        agent_tree = {
            "Done": AgentMeta(
                agent_type="dev", agent_name="Done", status="complete",
            ),
        }
        orphans, missing, ghosts = validate_checkpoints_against_tree(
            {}, agent_tree, checkpoints_dir,
        )
        assert ghosts == []
        assert missing == []

    def test_no_issues(self, tmp_path):
        """Happy path: everything lines up."""
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(
            AgentCheckpoint(agent_type="dev", agent_name="Alpha"),
            checkpoints_dir,
        )
        agent_tree = {
            "Alpha": AgentMeta(agent_type="dev", agent_name="Alpha", status="active"),
        }
        checkpoints = read_all_checkpoints(checkpoints_dir)
        orphans, missing, ghosts = validate_checkpoints_against_tree(
            checkpoints, agent_tree, checkpoints_dir,
        )
        assert orphans == []
        assert missing == []
        assert ghosts == []

    def test_deep_ghost_not_in_tl_scope(self, tmp_path):
        """Ghost at level 3 should be detected but parent handles it."""
        checkpoints_dir = tmp_path / "checkpoints"
        checkpoints_dir.mkdir(parents=True)

        agent_tree = {
            "TL": AgentMeta(agent_type="team-leader", agent_name="TL", status="active"),
            "Atlas": AgentMeta(agent_type="sub-tl", agent_name="Atlas", parent_agent="TL", status="active"),
            "DeepGhost": AgentMeta(
                agent_type="dev", agent_name="DeepGhost",
                parent_agent="Atlas", status="registered",
            ),
        }

        # TL has checkpoint, Atlas has checkpoint, DeepGhost is a ghost
        write_checkpoint(AgentCheckpoint(agent_type="team-leader", agent_name="TL"), checkpoints_dir)
        write_checkpoint(AgentCheckpoint(agent_type="sub-tl", agent_name="Atlas"), checkpoints_dir)

        checkpoints = read_all_checkpoints(checkpoints_dir)
        orphans, missing, ghosts = validate_checkpoints_against_tree(
            checkpoints, agent_tree, checkpoints_dir,
        )
        assert "DeepGhost" in ghosts

    def test_mixed_issues(self, tmp_path):
        """Multiple issues at once: orphan + ghost + missing."""
        checkpoints_dir = tmp_path / "checkpoints"
        type_dir = checkpoints_dir / "dev"
        type_dir.mkdir(parents=True)

        # Orphan: checkpoint without tree entry
        write_checkpoint(
            AgentCheckpoint(agent_type="dev", agent_name="OrphanAgent"),
            checkpoints_dir,
        )
        # Ghost: registered, no activity
        # Missing: active, has activity
        (type_dir / "MissingAgent.activity.jsonl").write_text('{"x":1}\n')

        agent_tree = {
            "GhostAgent": AgentMeta(agent_type="dev", agent_name="GhostAgent", status="registered"),
            "MissingAgent": AgentMeta(agent_type="dev", agent_name="MissingAgent", status="active"),
        }
        checkpoints = read_all_checkpoints(checkpoints_dir)

        orphans, missing, ghosts = validate_checkpoints_against_tree(
            checkpoints, agent_tree, checkpoints_dir,
        )
        assert "OrphanAgent" in orphans
        assert "GhostAgent" in ghosts
        assert "MissingAgent" in missing
