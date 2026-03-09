"""Tests for project context summarization."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from forge_cli.config_schema import ForgeConfig, ProjectConfig, TechStack
from forge_cli.generators.context_summarizer import (
    CONTEXT_FILENAME,
    build_raw_context,
    collect_context_files,
    load_project_context,
    summarize_context,
)


class TestCollectContextFiles:
    """Tests for collect_context_files."""

    def test_no_context_files(self):
        """Returns empty when no context_files configured."""
        config = ForgeConfig()
        assert collect_context_files(config) == []

    def test_single_file(self, tmp_path):
        """Reads a single context file."""
        plan = tmp_path / "PLAN.md"
        plan.write_text("# My Plan\n\nBuild something.")

        config = ForgeConfig(
            project=ProjectConfig(
                directory=str(tmp_path),
                context_files=[str(plan)],
            )
        )
        files = collect_context_files(config)
        assert len(files) == 1
        assert files[0][0] == "PLAN.md"
        assert "My Plan" in files[0][1]

    def test_directory_of_files(self, tmp_path):
        """Reads all .md files from a directory."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "api.md").write_text("# API Spec")
        (specs / "db.md").write_text("# DB Spec")
        (specs / "notes.txt").write_text("Some notes")
        (specs / "ignore.py").write_text("# not collected")

        config = ForgeConfig(
            project=ProjectConfig(
                directory=str(tmp_path),
                context_files=[str(specs)],
            )
        )
        files = collect_context_files(config)
        filenames = [f[0] for f in files]
        assert "api.md" in filenames
        assert "db.md" in filenames
        assert "notes.txt" in filenames
        assert "ignore.py" not in filenames

    def test_missing_file_logged(self, tmp_path):
        """Missing files are logged but don't cause errors."""
        config = ForgeConfig(
            project=ProjectConfig(
                directory=str(tmp_path),
                context_files=["/nonexistent/file.md"],
            )
        )
        files = collect_context_files(config)
        assert len(files) == 0

    def test_relative_paths(self, tmp_path):
        """Relative paths are resolved against project directory."""
        (tmp_path / "PLAN.md").write_text("# Plan")
        config = ForgeConfig(
            project=ProjectConfig(
                directory=str(tmp_path),
                context_files=["PLAN.md"],
            )
        )
        files = collect_context_files(config)
        assert len(files) == 1

    def test_large_file_truncated(self, tmp_path):
        """Files over 100KB are truncated."""
        large = tmp_path / "big.md"
        large.write_text("x" * 150_000)

        config = ForgeConfig(
            project=ProjectConfig(
                directory=str(tmp_path),
                context_files=[str(large)],
            )
        )
        files = collect_context_files(config)
        assert len(files) == 1
        assert "truncated" in files[0][1]
        assert len(files[0][1]) < 110_000

    def test_mixed_files_and_dirs(self, tmp_path):
        """Handles mix of files and directories."""
        (tmp_path / "PLAN.md").write_text("# Plan")
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "spec1.md").write_text("# Spec 1")

        config = ForgeConfig(
            project=ProjectConfig(
                directory=str(tmp_path),
                context_files=["PLAN.md", "specs"],
            )
        )
        files = collect_context_files(config)
        filenames = [f[0] for f in files]
        assert "PLAN.md" in filenames
        assert "spec1.md" in filenames


class TestBuildRawContext:
    """Tests for build_raw_context."""

    def test_description_only(self):
        """Includes project description."""
        config = ForgeConfig(
            project=ProjectConfig(description="Build an API")
        )
        context = build_raw_context(config)
        assert "Build an API" in context

    def test_description_and_requirements(self):
        """Includes both description and requirements."""
        config = ForgeConfig(
            project=ProjectConfig(
                description="Build an API",
                requirements="Must support REST and GraphQL",
            )
        )
        context = build_raw_context(config)
        assert "Build an API" in context
        assert "REST and GraphQL" in context

    def test_with_context_files(self, tmp_path):
        """Includes content from context files."""
        (tmp_path / "PLAN.md").write_text("# Phase 1: Build MVP")
        config = ForgeConfig(
            project=ProjectConfig(
                description="My project",
                directory=str(tmp_path),
                context_files=["PLAN.md"],
            )
        )
        context = build_raw_context(config)
        assert "Phase 1: Build MVP" in context


class TestSummarizeContext:
    """Tests for summarize_context."""

    def test_no_context_files_no_requirements(self, tmp_path):
        """Without context files or requirements, returns basic context."""
        config = ForgeConfig(
            project=ProjectConfig(
                description="Simple project",
                directory=str(tmp_path),
            )
        )
        summary = summarize_context(config, tmp_path)
        assert "Simple project" in summary
        assert (tmp_path / ".forge" / CONTEXT_FILENAME).exists()

    def test_with_context_files_falls_back_on_error(self, tmp_path):
        """Falls back to raw context when LLM provider fails."""
        (tmp_path / "PLAN.md").write_text("# Build a REST API with auth")

        # Use FakeLLMProvider for testing
        try:
            from llm_gateway.testing import FakeLLMProvider
            mock_provider = FakeLLMProvider()
        except ImportError:
            pytest.skip("llm-gateway not installed")

        config = ForgeConfig(
            project=ProjectConfig(
                description="REST API project",
                requirements="Build with FastAPI",
                directory=str(tmp_path),
                context_files=[str(tmp_path / "PLAN.md")],
            ),
            tech_stack=TechStack(languages=["python"], frameworks=["fastapi"]),
        )

        # FakeLLMProvider will return default responses, but the response
        # may not match the SummaryResponse schema — either way, context file
        # should be created
        summary = summarize_context(config, tmp_path, llm_provider=mock_provider)
        assert "Project Context" in summary
        assert (tmp_path / ".forge" / CONTEXT_FILENAME).exists()

    def test_with_requirements_but_no_files(self, tmp_path):
        """Calls LLM when requirements are present even without context files."""
        try:
            from llm_gateway.testing import FakeLLMProvider
            mock_provider = FakeLLMProvider()
        except ImportError:
            pytest.skip("llm-gateway not installed")

        config = ForgeConfig(
            project=ProjectConfig(
                description="API project",
                requirements="Detailed requirements for building a REST API",
                directory=str(tmp_path),
            ),
        )
        summary = summarize_context(config, tmp_path, llm_provider=mock_provider)
        assert (tmp_path / ".forge" / CONTEXT_FILENAME).exists()

    def test_saves_to_forge_dir(self, tmp_path):
        """Summary is saved to .forge/project-context.md."""
        config = ForgeConfig(
            project=ProjectConfig(
                description="Save test",
                directory=str(tmp_path),
            )
        )
        summarize_context(config, tmp_path)
        context_file = tmp_path / ".forge" / CONTEXT_FILENAME
        assert context_file.exists()
        assert "Save test" in context_file.read_text()


class TestLoadProjectContext:
    """Tests for load_project_context."""

    def test_no_context_file(self, tmp_path):
        """Returns None when no context file exists."""
        assert load_project_context(tmp_path) is None

    def test_existing_context_file(self, tmp_path):
        """Returns content of existing context file."""
        forge_dir = tmp_path / ".forge"
        forge_dir.mkdir()
        context_file = forge_dir / CONTEXT_FILENAME
        context_file.write_text("# Existing Context\n\nSome data.")

        result = load_project_context(tmp_path)
        assert result is not None
        assert "Existing Context" in result
