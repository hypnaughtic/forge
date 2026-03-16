"""E2E test fixtures for forge checkpoint/resume system.

Tests require tmux + Claude CLI and are skipped when FORGE_TEST_DRY_RUN=1.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from forge_cli.config_schema import (
    AgentsConfig,
    CompactionConfig,
    ExecutionStrategy,
    ForgeConfig,
    LLMGatewayConfig,
    ProjectConfig,
    ProjectMode,
    TeamProfile,
)
from forge_cli.generators.orchestrator import generate_all

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.feedback_collector import FeedbackCollector
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator, TmuxTestSession
from tests.e2e.transcript_analyzer import TranscriptAnalyzer


# -- Markers --
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "e2e: End-to-end tests requiring tmux + real Claude CLI")


# -- Skip if prerequisites missing --
@pytest.fixture(autouse=True)
def _require_e2e_env() -> None:
    if not shutil.which("tmux"):
        pytest.skip("tmux not available")
    if not shutil.which("claude"):
        pytest.skip("Claude CLI not available")
    if os.environ.get("FORGE_TEST_DRY_RUN", "1") == "1":
        pytest.skip("E2E tests require FORGE_TEST_DRY_RUN=0")


# -- tmux session fixture --
@pytest.fixture
def tmux(tmp_path: Path) -> TmuxTestSession:
    session_name = f"forge-e2e-{uuid4().hex[:8]}"
    session = TmuxTestSession(session_name, tmp_path)
    yield session
    session.kill()  # cleanup


# -- Project fixtures --
@pytest.fixture
def mvp_project(tmp_path: Path) -> tuple[Path, ForgeConfig]:
    """MVP co-pilot project with lean team."""
    config = ForgeConfig(
        project=ProjectConfig(
            description="E2E test: Task management REST API with user auth, "
                        "project boards, and real-time updates",
            directory=str(tmp_path),
        ),
        mode=ProjectMode.MVP,
        strategy=ExecutionStrategy.CO_PILOT,
        agents=AgentsConfig(team_profile=TeamProfile.LEAN),
        llm_gateway=LLMGatewayConfig(enabled=True, local_claude_model="claude-sonnet-4-20250514"),
    )
    generate_all(config)
    return tmp_path, config


@pytest.fixture
def production_project(tmp_path: Path) -> tuple[Path, ForgeConfig]:
    """Production-ready project with full team."""
    config = ForgeConfig(
        project=ProjectConfig(
            description="E2E test: Task management REST API with user auth",
            directory=str(tmp_path),
        ),
        mode=ProjectMode.PRODUCTION_READY,
        strategy=ExecutionStrategy.CO_PILOT,
        agents=AgentsConfig(team_profile=TeamProfile.FULL),
        llm_gateway=LLMGatewayConfig(enabled=True),
    )
    generate_all(config)
    return tmp_path, config


# -- LLM provider (real, not mocked) --
@pytest.fixture
def llm():
    """Real LLM provider for transcript analysis."""
    try:
        from llm_gateway import build_provider, GatewayConfig
        return build_provider(GatewayConfig(provider="local_claude"))
    except (ImportError, Exception):
        pytest.skip("llm-gateway not available for E2E tests")


# -- Orchestrator fixture --
@pytest.fixture
def orchestrator(tmp_path: Path, llm) -> ForgeSessionOrchestrator:
    transcript_dir = tmp_path / "transcripts"
    transcript_dir.mkdir()
    return ForgeSessionOrchestrator(tmp_path, None, llm, transcript_dir)


# -- Validator fixture --
@pytest.fixture
def validator(tmp_path: Path) -> CheckpointValidator:
    return CheckpointValidator(tmp_path)


# -- Feedback fixture --
@pytest.fixture
def feedback(tmp_path: Path) -> FeedbackCollector:
    feedback_dir = tmp_path / "feedback"
    feedback_dir.mkdir()
    return FeedbackCollector(feedback_dir)


# -- Compaction fixtures --

@pytest.fixture
def compaction_project(tmp_path: Path) -> tuple[Path, ForgeConfig]:
    """Project configured for compaction testing with low threshold."""
    config = ForgeConfig(
        project=ProjectConfig(
            description="Build a Python CLI calculator tool with add, subtract, "
                        "multiply, divide commands. Include input validation, "
                        "help text, and comprehensive unit tests.",
            directory=str(tmp_path),
        ),
        mode=ProjectMode.MVP,
        strategy=ExecutionStrategy.CO_PILOT,
        agents=AgentsConfig(team_profile=TeamProfile.LEAN),
        llm_gateway=LLMGatewayConfig(
            enabled=True,
            local_claude_model="claude-sonnet-4-20250514",
        ),
        compaction=CompactionConfig(
            compaction_threshold_tokens=500,
            enable_context_anchors=True,
            anchor_interval_minutes=1,
        ),
    )
    generate_all(config)
    return tmp_path, config


@pytest.fixture
def compaction_orchestrator(
    compaction_project: tuple[Path, ForgeConfig], llm,
) -> ForgeSessionOrchestrator:
    """Orchestrator wired to a compaction-configured project."""
    project_dir, config = compaction_project
    transcript_dir = project_dir / "transcripts"
    transcript_dir.mkdir()
    orch = ForgeSessionOrchestrator(project_dir, config, llm, transcript_dir)
    return orch


@pytest.fixture
def compaction_validator(
    compaction_project: tuple[Path, ForgeConfig],
) -> CheckpointValidator:
    """Validator for compaction-configured project."""
    project_dir, _ = compaction_project
    return CheckpointValidator(project_dir)


@pytest.fixture
def transcript_analyzer(llm) -> TranscriptAnalyzer:
    """TranscriptAnalyzer instance with real LLM provider."""
    return TranscriptAnalyzer(llm)
