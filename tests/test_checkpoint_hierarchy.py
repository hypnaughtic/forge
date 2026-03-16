"""Unit tests for hierarchical checkpoint paths and multi-agent scanning."""

from __future__ import annotations

from pathlib import Path

import pytest

from forge_cli.models import AgentCheckpoint
from forge_cli.checkpoint import (
    read_all_checkpoints,
    read_checkpoint,
    write_checkpoint,
)


class TestHierarchicalPaths:
    def test_write_creates_type_subdirectory(self, tmp_path):
        cp = AgentCheckpoint(agent_type="backend-developer", agent_name="Nova")
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(cp, checkpoints_dir)

        assert (checkpoints_dir / "backend-developer" / "Nova.json").exists()
        assert not (checkpoints_dir / "backend-developer.json").exists()

    def test_read_with_type_and_name(self, tmp_path):
        cp = AgentCheckpoint(agent_type="dev", agent_name="Alpha", iteration=5)
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(cp, checkpoints_dir)

        result = read_checkpoint("dev", checkpoints_dir, agent_name="Alpha")
        assert result is not None
        assert result.iteration == 5

    def test_multiple_agents_same_type(self, tmp_path):
        """Multiple agents of the same type in the same directory."""
        checkpoints_dir = tmp_path / "checkpoints"
        for name in ["Alpha", "Beta", "Gamma"]:
            write_checkpoint(
                AgentCheckpoint(agent_type="backend-developer", agent_name=name),
                checkpoints_dir,
            )

        # All three should exist
        for name in ["Alpha", "Beta", "Gamma"]:
            assert (checkpoints_dir / "backend-developer" / f"{name}.json").exists()

        result = read_all_checkpoints(checkpoints_dir)
        assert len(result) == 3
        assert set(result.keys()) == {"Alpha", "Beta", "Gamma"}

    def test_read_all_multiple_types(self, tmp_path):
        """Agents of different types all discoverable."""
        checkpoints_dir = tmp_path / "checkpoints"
        agents = [
            ("team-leader", "Commander"),
            ("backend-developer", "Nova"),
            ("frontend-engineer", "Pixel"),
            ("qa-engineer", "Spark"),
        ]
        for agent_type, name in agents:
            write_checkpoint(
                AgentCheckpoint(agent_type=agent_type, agent_name=name),
                checkpoints_dir,
            )

        result = read_all_checkpoints(checkpoints_dir)
        assert len(result) == 4
        assert result["Commander"].agent_type == "team-leader"
        assert result["Pixel"].agent_type == "frontend-engineer"

    def test_four_level_hierarchy_checkpoints(self, tmp_path):
        """Write checkpoints for a 4-level tree, verify all found."""
        checkpoints_dir = tmp_path / "checkpoints"
        hierarchy = [
            ("team-leader", "Commander", None),
            ("sub-tl", "Atlas", "Commander"),
            ("sub-tl", "Nova", "Commander"),
            ("dev", "Pixel", "Atlas"),
            ("dev", "Spark", "Atlas"),
            ("dev", "Blaze", "Nova"),
            ("dev", "Echo", "Nova"),
            ("worker", "W1", "Pixel"),
            ("worker", "W2", "Spark"),
            ("worker", "W3", "Blaze"),
            ("worker", "W4", "Echo"),
        ]
        for agent_type, name, parent in hierarchy:
            write_checkpoint(
                AgentCheckpoint(
                    agent_type=agent_type,
                    agent_name=name,
                    parent_agent=parent,
                ),
                checkpoints_dir,
            )

        result = read_all_checkpoints(checkpoints_dir)
        assert len(result) == 11
        # Verify all names present
        expected_names = {name for _, name, _ in hierarchy}
        assert set(result.keys()) == expected_names
        # Verify parent_agent preserved
        assert result["Atlas"].parent_agent == "Commander"
        assert result["W1"].parent_agent == "Pixel"

    def test_overwrite_same_agent(self, tmp_path):
        """Writing same agent twice overwrites the checkpoint."""
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(
            AgentCheckpoint(agent_type="dev", agent_name="Alpha", iteration=1),
            checkpoints_dir,
        )
        write_checkpoint(
            AgentCheckpoint(agent_type="dev", agent_name="Alpha", iteration=5),
            checkpoints_dir,
        )

        result = read_checkpoint("dev", checkpoints_dir, agent_name="Alpha")
        assert result.iteration == 5

    def test_empty_checkpoints_dir(self, tmp_path):
        result = read_all_checkpoints(tmp_path / "nonexistent")
        assert result == {}
