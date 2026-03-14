"""Integration tests for checkpoint skill generation quality.

Tests that the checkpoint skill is generated correctly across
different project configurations. Uses FakeLLMProvider (instant, CI-safe).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forge_cli.config_schema import (
    AgentsConfig,
    AtlassianConfig,
    ExecutionStrategy,
    ForgeConfig,
    LLMGatewayConfig,
    ProjectConfig,
    ProjectMode,
    TeamProfile,
    TechStack,
)
from forge_cli.generators.skills import generate_skills


def _make_config(**overrides) -> ForgeConfig:
    """Create a ForgeConfig with sensible defaults for testing."""
    defaults = dict(
        project=ProjectConfig(
            description="Test project",
            directory="/tmp/test",
        ),
        mode=ProjectMode.MVP,
        strategy=ExecutionStrategy.CO_PILOT,
        agents=AgentsConfig(team_profile=TeamProfile.LEAN),
    )
    defaults.update(overrides)
    return ForgeConfig(**defaults)


class TestCheckpointSkillGeneration:
    """Verify checkpoint skill is generated with correct content."""

    def test_checkpoint_skill_generated(self, tmp_path):
        config = _make_config()
        generate_skills(config, tmp_path)
        assert (tmp_path / "checkpoint.md").exists()

    def test_checkpoint_skill_frontmatter(self, tmp_path):
        config = _make_config()
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "name: checkpoint" in content
        assert "description:" in content
        assert "argument-hint:" in content

    def test_checkpoint_skill_save_command(self, tmp_path):
        config = _make_config()
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "save" in content.lower()
        assert "agent_name" in content
        assert "context_summary" in content
        assert "handoff_notes" in content
        assert ".forge/checkpoints" in content

    def test_checkpoint_skill_load_command(self, tmp_path):
        config = _make_config()
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "load" in content.lower()
        assert "ADOPT" in content or "adopt" in content.lower()

    def test_checkpoint_skill_stop_signal(self, tmp_path):
        config = _make_config()
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "check-stop" in content
        assert "STOP_REQUESTED" in content

    def test_checkpoint_skill_atomic_write(self, tmp_path):
        config = _make_config()
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert ".tmp" in content or "atomic" in content.lower()

    def test_checkpoint_skill_non_negotiable(self, tmp_path):
        config = _make_config()
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "NON-NEGOTIABLE" in content


class TestCheckpointSkillProjectTypes:
    """Verify checkpoint skill adapts to project type."""

    def test_cli_project_checkpoint_frequency(self, tmp_path):
        config = _make_config(
            project=ProjectConfig(
                description="CLI tool for data processing",
                directory="/tmp/test",
            ),
            tech_stack=TechStack(frameworks=["click"]),
        )
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "CLI" in content or "command" in content.lower()

    def test_web_backend_checkpoint_frequency(self, tmp_path):
        config = _make_config(
            project=ProjectConfig(
                description="REST API for task management",
                directory="/tmp/test",
            ),
            tech_stack=TechStack(frameworks=["fastapi"]),
        )
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "API" in content or "endpoint" in content.lower()

    def test_fullstack_checkpoint_frequency(self, tmp_path):
        config = _make_config(
            project=ProjectConfig(
                description="Full-stack task management app",
                directory="/tmp/test",
            ),
            tech_stack=TechStack(frameworks=["fastapi", "react"]),
        )
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "Full-Stack" in content or "visual" in content.lower() or "UI" in content

    def test_static_site_checkpoint_frequency(self, tmp_path):
        config = _make_config(
            project=ProjectConfig(
                description="Company marketing website with blog",
                directory="/tmp/test",
            ),
            tech_stack=TechStack(frameworks=["next.js"]),
        )
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        # Frontend-involved projects mention visual verification
        assert "page" in content.lower() or "component" in content.lower()


class TestCheckpointSkillStrategies:
    """Verify checkpoint skill adapts to strategy."""

    def test_auto_pilot_strategy(self, tmp_path):
        config = _make_config(strategy=ExecutionStrategy.AUTO_PILOT)
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "silent" in content.lower()

    def test_co_pilot_strategy(self, tmp_path):
        config = _make_config(strategy=ExecutionStrategy.CO_PILOT)
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "status report" in content.lower() or "silently" in content.lower()

    def test_micro_manage_strategy(self, tmp_path):
        config = _make_config(strategy=ExecutionStrategy.MICRO_MANAGE)
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "announce" in content.lower() or "human" in content.lower()


class TestCheckpointSkillWithNonNegotiables:
    """Verify non-negotiables are included when configured."""

    def test_non_negotiables_included(self, tmp_path):
        config = _make_config(
            non_negotiables=["All code must be type-safe", "100% test coverage"],
        )
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        assert "Non-Negotiable" in content or "non_negotiable" in content.lower()

    def test_no_non_negotiables_when_empty(self, tmp_path):
        config = _make_config(non_negotiables=[])
        generate_skills(config, tmp_path)
        content = (tmp_path / "checkpoint.md").read_text()
        # Should not have empty non-negotiables section
        assert "Non-Negotiables Verification" not in content
