"""Unit tests for forge_cli/tokens.py — token counting and reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forge_cli.tokens import (
    TokenReport,
    build_token_report,
    count_tokens,
    display_token_table,
    save_token_report,
)


class TestCountTokens:
    def test_count_basic(self):
        result = count_tokens("Hello, world!")
        assert isinstance(result, int)
        assert result > 0

    def test_count_empty(self):
        result = count_tokens("")
        assert result == 0

    def test_count_long_text(self):
        text = "The quick brown fox jumps over the lazy dog. " * 100
        result = count_tokens(text)
        assert result > 100


class TestBuildTokenReport:
    def test_empty_project(self, tmp_path):
        from forge_cli.config_schema import ForgeConfig
        config = ForgeConfig()
        report = build_token_report(config, tmp_path)
        assert isinstance(report, TokenReport)
        assert report.total_generated_tokens == 0
        # Only global CLAUDE.md might be present (depends on machine)
        non_global = [f for f in report.files if f.file_type != "global_claude_md"]
        assert non_global == []

    def test_with_agent_files(self, tmp_path):
        from forge_cli.config_schema import ForgeConfig
        config = ForgeConfig()

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "team-leader.md").write_text("# Team Leader\n" * 50)
        (agents_dir / "backend-developer.md").write_text("# Backend Dev\n" * 30)

        report = build_token_report(config, tmp_path)
        assert len(report.files) >= 2
        agent_files = [f for f in report.files if f.file_type == "agent"]
        assert len(agent_files) == 2
        assert report.total_generated_tokens > 0

    def test_with_claude_md(self, tmp_path):
        from forge_cli.config_schema import ForgeConfig
        config = ForgeConfig()

        (tmp_path / "CLAUDE.md").write_text("# Project Context\n" * 20)

        report = build_token_report(config, tmp_path)
        claude_files = [f for f in report.files if f.file_type == "claude_md"]
        assert len(claude_files) == 1
        assert claude_files[0].tokens > 0

    def test_agent_budgets_computed(self, tmp_path):
        from forge_cli.config_schema import ForgeConfig
        config = ForgeConfig()

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "team-leader.md").write_text("# TL instructions\n" * 50)
        (agents_dir / "backend-developer.md").write_text("# BD instructions\n" * 30)
        (tmp_path / "CLAUDE.md").write_text("# Context\n")
        (tmp_path / "team-init-plan.md").write_text("# Plan\n" * 20)

        report = build_token_report(config, tmp_path)
        assert len(report.agent_budgets) == 2

        tl_budget = next(b for b in report.agent_budgets if b.agent_type == "team-leader")
        bd_budget = next(b for b in report.agent_budgets if b.agent_type == "backend-developer")

        # TL should have plan tokens, BD should not
        assert tl_budget.team_init_plan_tokens > 0
        assert bd_budget.team_init_plan_tokens == 0
        # Total should be sum
        assert tl_budget.total_startup_tokens == (
            tl_budget.agent_file_tokens
            + tl_budget.claude_md_tokens
            + tl_budget.team_init_plan_tokens
            + tl_budget.system_overhead_tokens
        )

    def test_compaction_threshold_from_config(self, tmp_path):
        from forge_cli.config_schema import ForgeConfig
        config = ForgeConfig()
        config.compaction.compaction_threshold_tokens = 50_000

        report = build_token_report(config, tmp_path)
        assert report.compaction_threshold_tokens == 50_000

    def test_skills_counted(self, tmp_path):
        from forge_cli.config_schema import ForgeConfig
        config = ForgeConfig()

        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "checkpoint.md").write_text("# Checkpoint skill\n" * 10)
        (skills_dir / "context-reload.md").write_text("# Context reload\n" * 10)

        report = build_token_report(config, tmp_path)
        skill_files = [f for f in report.files if f.file_type == "skill"]
        assert len(skill_files) == 2


class TestSaveTokenReport:
    def test_saves_json(self, tmp_path):
        report = TokenReport(
            total_generated_tokens=1000,
            timestamp="2026-03-14T10:00:00Z",
            provider="anthropic",
            tokenizer_name="anthropic",
        )
        path = save_token_report(report, tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["total_generated_tokens"] == 1000
        assert data["provider"] == "anthropic"


class TestDisplayTokenTable:
    def test_displays_without_error(self, tmp_path):
        """display_token_table should not raise."""
        from rich.console import Console
        from io import StringIO

        output = StringIO()
        console = Console(file=output, width=120)

        report = TokenReport(
            total_generated_tokens=5000,
            compaction_threshold_tokens=100_000,
            timestamp="2026-03-14T10:00:00Z",
            provider="anthropic",
            tokenizer_name="anthropic",
        )
        # Should not raise
        display_token_table(report, console)
        text = output.getvalue()
        assert "100,000" in text or "Compaction" in text
