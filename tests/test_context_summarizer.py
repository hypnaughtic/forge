"""Tests for project context summarization."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge_cli.config_schema import ForgeConfig, ProjectConfig, TechStack
from forge_cli.generators.context_summarizer import (
    CONTEXT_FILENAME,
    MAX_FILE_SIZE,
    _build_summarize_prompt,
    _read_file,
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

    def test_plan_file_included(self, tmp_path):
        """Plan file content is included in raw context."""
        (tmp_path / "PLAN.md").write_text("# Implementation Plan\n\nPhase 1: Setup")
        config = ForgeConfig(
            project=ProjectConfig(
                description="My project",
                directory=str(tmp_path),
                plan_file="PLAN.md",
            )
        )
        context = build_raw_context(config)
        assert "Implementation Plan" in context
        assert "Phase 1: Setup" in context

    def test_plan_file_and_context_files_both_included(self, tmp_path):
        """Both plan file and context files are included."""
        (tmp_path / "PLAN.md").write_text("# Plan\n\nBuild MVP first")
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "api.md").write_text("# API Spec\n\nREST endpoints")

        config = ForgeConfig(
            project=ProjectConfig(
                description="My project",
                directory=str(tmp_path),
                plan_file="PLAN.md",
                context_files=["specs"],
            )
        )
        context = build_raw_context(config)
        assert "Build MVP first" in context
        assert "REST endpoints" in context

    def test_missing_plan_file_not_error(self, tmp_path):
        """Missing plan file is logged but doesn't cause errors."""
        config = ForgeConfig(
            project=ProjectConfig(
                description="My project",
                directory=str(tmp_path),
                plan_file="/nonexistent/plan.md",
            )
        )
        context = build_raw_context(config)
        assert "My project" in context  # Description still present


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


class TestCollectContextFilesProgress:
    """Tests for collect_context_files on_progress callback."""

    def test_on_progress_called_for_single_file(self, tmp_path):
        """on_progress fires when reading a single context file (line 58)."""
        (tmp_path / "spec.md").write_text("# Spec")
        config = ForgeConfig(
            project=ProjectConfig(
                directory=str(tmp_path),
                context_files=[str(tmp_path / "spec.md")],
            )
        )
        progress_calls: list[str] = []
        collect_context_files(config, on_progress=progress_calls.append)

        assert len(progress_calls) == 1
        assert "spec.md" in progress_calls[0]

    def test_on_progress_called_for_directory_files(self, tmp_path):
        """on_progress fires for each file in a directory (line 65)."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "a.md").write_text("# A")
        (docs / "b.txt").write_text("B content")

        config = ForgeConfig(
            project=ProjectConfig(
                directory=str(tmp_path),
                context_files=[str(docs)],
            )
        )
        progress_calls: list[str] = []
        collect_context_files(config, on_progress=progress_calls.append)

        assert len(progress_calls) == 2
        filenames = [c.split()[-1] for c in progress_calls]
        assert "a.md" in filenames
        assert "b.txt" in filenames


class TestReadFileEdgeCases:
    """Tests for _read_file error handling (lines 80-81)."""

    def test_read_file_oserror_logs_warning(self, tmp_path, caplog):
        """OSError during file read logs warning and skips file."""
        bad_file = tmp_path / "unreadable.md"
        bad_file.write_text("content")
        bad_file.chmod(0o000)

        files: list[tuple[str, str]] = []
        with caplog.at_level(logging.WARNING):
            _read_file(bad_file, files)

        assert len(files) == 0
        assert "Could not read" in caplog.text
        # Restore permissions for cleanup
        bad_file.chmod(0o644)

    def test_read_file_with_replacement_chars(self, tmp_path):
        """Binary file with invalid UTF-8 uses errors='replace'."""
        binary_file = tmp_path / "binary.md"
        # Write raw bytes with invalid UTF-8 sequences
        binary_file.write_bytes(b"Hello \xff\xfe World \x80\x81")

        files: list[tuple[str, str]] = []
        _read_file(binary_file, files)

        assert len(files) == 1
        # The replacement character U+FFFD should appear
        assert "\ufffd" in files[0][1]
        assert "Hello" in files[0][1]


class TestBuildRawContextEdgeCases:
    """Tests for build_raw_context plan file edge cases."""

    def test_plan_file_with_on_progress_callback(self, tmp_path):
        """on_progress callback is called when reading plan file (line 109)."""
        (tmp_path / "plan.md").write_text("# Plan\n\nPhase 1")
        config = ForgeConfig(
            project=ProjectConfig(
                description="Test",
                directory=str(tmp_path),
                plan_file="plan.md",
            )
        )
        progress_calls: list[str] = []
        context = build_raw_context(config, on_progress=progress_calls.append)

        assert any("plan.md" in call for call in progress_calls)
        assert "Phase 1" in context

    def test_plan_file_truncated_when_too_large(self, tmp_path):
        """Plan file content is truncated when exceeding MAX_FILE_SIZE (line 113)."""
        large_plan = tmp_path / "large-plan.md"
        large_plan.write_text("x" * (MAX_FILE_SIZE + 50_000))

        config = ForgeConfig(
            project=ProjectConfig(
                description="Test",
                directory=str(tmp_path),
                plan_file="large-plan.md",
            )
        )
        context = build_raw_context(config)

        assert "truncated" in context
        # The plan section should contain the truncated content
        assert "Implementation Plan" in context

    def test_plan_file_read_error_logs_warning(self, tmp_path, caplog):
        """OSError reading plan file logs warning (lines 115-116)."""
        plan_file = tmp_path / "restricted.md"
        plan_file.write_text("Secret plan")
        plan_file.chmod(0o000)

        config = ForgeConfig(
            project=ProjectConfig(
                description="Test project",
                directory=str(tmp_path),
                plan_file="restricted.md",
            )
        )
        with caplog.at_level(logging.WARNING):
            context = build_raw_context(config)

        assert "Could not read plan file" in caplog.text
        # Description should still be present
        assert "Test project" in context
        # Restore permissions for cleanup
        plan_file.chmod(0o644)


class TestBuildSummarizePrompt:
    """Tests for _build_summarize_prompt plan_note branch (line 131)."""

    def test_prompt_includes_plan_note_when_plan_file_set(self):
        """plan_note is included when config has a plan_file."""
        config = ForgeConfig(
            project=ProjectConfig(
                description="Test",
                plan_file="PLAN.md",
            )
        )
        prompt = _build_summarize_prompt("raw context here", config)

        assert "plan file has been provided" in prompt
        assert "authoritative" in prompt.lower()

    def test_prompt_no_plan_note_without_plan_file(self):
        """plan_note is absent when config has no plan_file."""
        config = ForgeConfig(
            project=ProjectConfig(description="Test")
        )
        prompt = _build_summarize_prompt("raw context here", config)

        assert "plan file has been provided" not in prompt


class TestSummarizeContextEdgeCases:
    """Tests for summarize_context fallback paths."""

    def test_dry_run_auto_creates_fake_provider(self, tmp_path):
        """FORGE_TEST_DRY_RUN=1 auto-injects FakeLLMProvider (lines 237-241)."""
        config = ForgeConfig(
            project=ProjectConfig(
                description="Test project",
                requirements="Build something",
                directory=str(tmp_path),
            )
        )

        with patch.dict(os.environ, {"FORGE_TEST_DRY_RUN": "1"}):
            # Call without explicit llm_provider — should auto-detect dry-run
            summary = summarize_context(config, tmp_path)

        assert "Project Context" in summary
        assert (tmp_path / ".forge" / CONTEXT_FILENAME).exists()

    def test_no_llm_gateway_falls_back_to_raw_context(self, tmp_path):
        """Falls back to raw context when llm_gateway is not importable (lines 250-254)."""
        config = ForgeConfig(
            project=ProjectConfig(
                description="Fallback test",
                requirements="Some requirements",
                directory=str(tmp_path),
            )
        )

        # Simulate llm_gateway not being installed by patching the import
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "llm_gateway" or name.startswith("llm_gateway."):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch.dict(os.environ, {"FORGE_TEST_DRY_RUN": "0"}):
            with patch.object(builtins, "__import__", side_effect=mock_import):
                summary = summarize_context(config, tmp_path, llm_provider=None)

        assert "Project Context" in summary
        assert "Fallback test" in summary
        assert (tmp_path / ".forge" / CONTEXT_FILENAME).exists()

    def test_summarize_with_plan_file_and_llm_provider(self, tmp_path):
        """Exercises _build_summarize_prompt with plan_file via full summarize path."""
        try:
            from llm_gateway.testing import FakeLLMProvider
            mock_provider = FakeLLMProvider()
        except ImportError:
            pytest.skip("llm-gateway not installed")

        (tmp_path / "plan.md").write_text("# Build Plan\n\nPhase 1: Foundation")
        config = ForgeConfig(
            project=ProjectConfig(
                description="Plan project",
                requirements="Detailed reqs",
                directory=str(tmp_path),
                plan_file="plan.md",
            ),
        )
        summary = summarize_context(config, tmp_path, llm_provider=mock_provider)
        assert "Project Context" in summary
        assert (tmp_path / ".forge" / CONTEXT_FILENAME).exists()
