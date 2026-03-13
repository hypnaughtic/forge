"""Integration tests for the co_planner quality case.

Tests that forge generates high-quality, customized files for the co-planner
project — an AI-powered diagram co-pilot with React Flow frontend and FastAPI
backend with multi-tier suggestion engine.

Uses the project context files (PLAN.md, ARCHITECTURE.md, specs/) to verify
that forge properly summarizes and incorporates detailed project requirements
into generated agent instructions, skills, and init plan.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from forge_cli.config_loader import load_config
from forge_cli.config_schema import (
    ExecutionStrategy,
    ForgeConfig,
    ProjectMode,
    RefinementConfig,
)
from forge_cli.generators.orchestrator import generate_all, run_refinement

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

QUALITY_CASE_DIR = Path(__file__).parent / "quality_cases" / "co_planner"
FORGE_DRY_RUN = os.environ.get("FORGE_TEST_DRY_RUN", "1") == "1"


def _load_co_planner_config() -> ForgeConfig:
    """Load the co_planner forge config."""
    config_path = QUALITY_CASE_DIR / "forge-config.yaml"
    config = load_config(str(config_path))
    # Resolve context files relative to the quality case directory
    config.project.context_files = [
        str(QUALITY_CASE_DIR / f) for f in config.project.context_files
    ]
    return config


def _get_refinement_provider(initial_score: int = 85, refined_score: int = 95):
    """Get a test LLM provider — fake for dry run, real for live."""
    if FORGE_DRY_RUN:
        from llm_gateway.testing import FakeLLMProvider

        call_count = 0

        def _response_factory(response_model, messages):
            """FakeLLMProvider factory: (response_model_type, messages) -> instance."""
            nonlocal call_count
            call_count += 1
            fields = response_model.model_fields
            if "score" in fields:
                score = refined_score if call_count > 2 else initial_score
                return response_model(
                    score=score,
                    reasoning=f"Score {score}: Comprehensive co-planner instructions.",
                    suggestions=["Add WebSocket protocol details", "Include RAG tier descriptions"],
                )
            if "content" in fields:
                original = messages[-1]["content"] if messages else ""
                marker = "CURRENT CONTENT:\n"
                idx = original.find(marker)
                if idx >= 0:
                    content = original[idx + len(marker):]
                    rules_idx = content.find("\nRULES:")
                    if rules_idx > 0:
                        content = content[:rules_idx]
                else:
                    content = "# Refined content for co-planner project"
                return response_model(
                    content=content,
                    changes_made=[
                        "Added co-planner specific context",
                        "Included WebSocket and suggestion engine details",
                    ],
                )
            if "summary" in fields:
                return response_model(
                    summary=(
                        "co-planner is an AI-powered diagram co-pilot with "
                        "React Flow canvas frontend and FastAPI backend. "
                        "Multi-tier suggestion engine with pattern matching, "
                        "graph-native RAG, LLM inference, and feedback loops."
                    ),
                )
            # Fallback: try constructing with text field
            if "text" in fields:
                return response_model(text="co-planner quality response")
            return response_model()

        return FakeLLMProvider(response_factory=_response_factory)
    return None


# ---------------------------------------------------------------------------
# Config validation tests
# ---------------------------------------------------------------------------


class TestCoplannerConfig:
    """Verify the co_planner forge config is valid and complete."""

    def test_config_loads(self):
        """Config file loads without errors."""
        config = _load_co_planner_config()
        assert config.project.description
        assert "co-planner" in config.project.description.lower()

    def test_mode_is_production_ready(self):
        """Mode should be production-ready."""
        config = _load_co_planner_config()
        assert config.mode == ProjectMode.PRODUCTION_READY

    def test_strategy_is_auto_pilot(self):
        """Strategy should be auto-pilot."""
        config = _load_co_planner_config()
        assert config.strategy == ExecutionStrategy.AUTO_PILOT

    def test_tech_stack_complete(self):
        """Tech stack includes all required technologies."""
        config = _load_co_planner_config()
        assert "python" in config.tech_stack.languages
        assert "typescript" in config.tech_stack.languages
        assert "fastapi" in config.tech_stack.frameworks
        assert "nextjs" in config.tech_stack.frameworks
        assert "postgresql" in config.tech_stack.databases

    def test_agents_custom_roster(self):
        """Custom team roster includes all required agents."""
        config = _load_co_planner_config()
        agents = config.get_active_agents()
        required = [
            "team-leader", "architect", "backend-developer",
            "frontend-developer", "qa-engineer", "devops-specialist",
            "critic",
        ]
        for agent in required:
            assert agent in agents, f"Missing required agent: {agent}"

    def test_non_negotiables_present(self):
        """Non-negotiables are configured."""
        config = _load_co_planner_config()
        assert len(config.non_negotiables) >= 3
        nn_text = " ".join(config.non_negotiables).lower()
        assert "llm-gateway" in nn_text
        assert "graceful degradation" in nn_text

    def test_context_files_exist(self):
        """All referenced context files exist."""
        config = _load_co_planner_config()
        for f in config.project.context_files:
            path = Path(f)
            assert path.exists(), f"Context file not found: {f}"

    def test_refinement_enabled(self):
        """Refinement is enabled with proper thresholds."""
        config = _load_co_planner_config()
        assert config.refinement.enabled is True
        assert config.refinement.score_threshold == 90


# ---------------------------------------------------------------------------
# Generation tests
# ---------------------------------------------------------------------------


class TestCoplannerGeneration:
    """Test that forge generates proper files for the co_planner project."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Generate co_planner project in temp directory."""
        self.config = _load_co_planner_config()
        self.config.project.directory = str(tmp_path)
        self.config.refinement.enabled = False  # Test generation only first
        self.project_dir = tmp_path
        # Pass fake provider for context summarization (avoids real LLM calls)
        provider = _get_refinement_provider()
        generate_all(self.config, llm_provider=provider)

    def test_claude_md_exists(self):
        assert (self.project_dir / "CLAUDE.md").exists()

    def test_team_init_plan_exists(self):
        assert (self.project_dir / "team-init-plan.md").exists()

    def test_agent_files_generated(self):
        agents_dir = self.project_dir / ".claude" / "agents"
        for agent in self.config.get_active_agents():
            assert (agents_dir / f"{agent}.md").exists(), f"Missing agent file: {agent}"

    def test_skills_generated(self):
        skills_dir = self.project_dir / ".claude" / "skills"
        assert skills_dir.is_dir()
        skills = list(skills_dir.glob("*.md"))
        assert len(skills) >= 5, f"Expected at least 5 skills, got {len(skills)}"

    def test_mcp_config_generated(self):
        mcp = self.project_dir / ".claude" / "mcp.json"
        assert mcp.exists()
        data = json.loads(mcp.read_text())
        assert "mcpServers" in data

    def test_settings_json_generated(self):
        """auto-pilot strategy should generate settings.json."""
        settings = self.project_dir / ".claude" / "settings.json"
        assert settings.exists()
        data = json.loads(settings.read_text())
        assert "permissions" in data

    def test_forge_dir_created(self):
        """Generation creates .forge directory."""
        assert (self.project_dir / ".forge").is_dir()

    def test_no_gitignore_created(self):
        """Generation does not create or modify .gitignore."""
        gitignore = self.project_dir / ".gitignore"
        assert not gitignore.exists()


# ---------------------------------------------------------------------------
# Content quality tests — verify project-specific content
# ---------------------------------------------------------------------------


class TestCoplannerContentQuality:
    """Verify generated files contain project-specific content."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.config = _load_co_planner_config()
        self.config.project.directory = str(tmp_path)
        self.config.refinement.enabled = False
        self.project_dir = tmp_path
        provider = _get_refinement_provider()
        generate_all(self.config, llm_provider=provider)

    def _read_agent(self, name: str) -> str:
        return (self.project_dir / ".claude" / "agents" / f"{name}.md").read_text()

    def _read_file(self, name: str) -> str:
        return (self.project_dir / name).read_text()

    def test_claude_md_mentions_project(self):
        """CLAUDE.md references co-planner project details."""
        content = self._read_file("CLAUDE.md")
        assert "co-planner" in content.lower() or "diagram" in content.lower()
        assert "auto-pilot" in content.lower() or "auto_pilot" in content.lower()

    def test_claude_md_mentions_tech_stack(self):
        """CLAUDE.md includes tech stack information."""
        content = self._read_file("CLAUDE.md")
        assert "fastapi" in content.lower()
        assert "python" in content.lower()

    def test_team_init_plan_has_phases(self):
        """team-init-plan.md has structured phases."""
        content = self._read_file("team-init-plan.md")
        assert "phase" in content.lower() or "iteration" in content.lower()

    def test_backend_developer_mentions_fastapi(self):
        """Backend developer agent mentions FastAPI."""
        content = self._read_agent("backend-developer")
        assert "fastapi" in content.lower()

    def test_frontend_developer_mentions_react(self):
        """Frontend developer agent mentions React/Next.js."""
        content = self._read_agent("frontend-developer")
        lower = content.lower()
        assert "react" in lower or "next" in lower or "frontend" in lower

    def test_architect_mentions_system_design(self):
        """Architect agent references system design concepts."""
        content = self._read_agent("architect")
        lower = content.lower()
        assert "api" in lower or "architecture" in lower or "design" in lower

    def test_qa_engineer_mentions_testing(self):
        """QA engineer references testing strategy."""
        content = self._read_agent("qa-engineer")
        lower = content.lower()
        assert "test" in lower

    def test_devops_mentions_docker(self):
        """DevOps agent references Docker."""
        content = self._read_agent("devops-specialist")
        assert "docker" in content.lower()

    def test_non_negotiables_in_agents(self):
        """Non-negotiables appear in agent files."""
        for agent in self.config.get_active_agents():
            content = self._read_agent(agent)
            # At least some agents should mention non-negotiables
            if agent in ("team-leader", "critic", "backend-developer"):
                assert "non-negotiable" in content.lower() or "llm-gateway" in content.lower(), (
                    f"{agent} missing non-negotiable references"
                )

    def test_llm_gateway_section_in_agents(self):
        """All agents have LLM Gateway section."""
        for agent in self.config.get_active_agents():
            content = self._read_agent(agent)
            assert "llm gateway" in content.lower() or "llm-gateway" in content.lower(), (
                f"{agent} missing LLM Gateway section"
            )

    def test_auto_pilot_strategy_in_agents(self):
        """Agents reflect auto-pilot strategy behavior."""
        tl = self._read_agent("team-leader")
        lower = tl.lower()
        # auto-pilot means agents should have full autonomy references
        assert "auto" in lower or "autonomy" in lower or "autonomous" in lower

    def test_sub_agent_spawning_sections(self):
        """Agents with sub-agent spawning have relevant sections."""
        tl = self._read_agent("team-leader")
        assert "sub-agent" in tl.lower() or "spawn" in tl.lower()

    def test_agent_naming_enabled(self):
        """Agent naming protocol is present."""
        tl = self._read_agent("team-leader")
        assert "naming" in tl.lower() or "codename" in tl.lower()


# ---------------------------------------------------------------------------
# Refinement tests (with dry-run fake provider)
# ---------------------------------------------------------------------------


@pytest.mark.timeout(60 if FORGE_DRY_RUN else 1200)
class TestCoplannerRefinement:
    """Test refinement pipeline for the co_planner project."""

    def test_refinement_runs(self, tmp_path):
        """Refinement completes and produces improved files."""
        config = _load_co_planner_config()
        config.project.directory = str(tmp_path)
        config.refinement = RefinementConfig(
            enabled=True,
            score_threshold=90,
            max_iterations=3,
        )

        provider = _get_refinement_provider(initial_score=85, refined_score=95)
        generate_all(config, llm_provider=provider)
        report = run_refinement(config, tmp_path, llm_provider=provider)

        assert report is not None
        assert len(report.files) > 0

    def test_refinement_report_saved(self, tmp_path):
        """Refinement report is saved to .forge directory."""
        config = _load_co_planner_config()
        config.project.directory = str(tmp_path)
        config.refinement = RefinementConfig(
            enabled=True,
            score_threshold=90,
            max_iterations=2,
        )

        provider = _get_refinement_provider(initial_score=80, refined_score=95)
        generate_all(config, llm_provider=provider)
        run_refinement(config, tmp_path, llm_provider=provider)

        # Check JSON report
        json_report = tmp_path / ".forge" / "refinement-report.json"
        assert json_report.exists()
        data = json.loads(json_report.read_text())
        assert "summary" in data
        assert "files" in data
        assert data["summary"]["total_files"] > 0

        # Check Markdown report
        md_report = tmp_path / ".forge" / "refinement-report.md"
        assert md_report.exists()
        content = md_report.read_text()
        assert "Refinement Report" in content
        assert "Initial score" in content

    def test_refinement_scores_tracked(self, tmp_path):
        """Per-file scores are tracked in the report."""
        config = _load_co_planner_config()
        config.project.directory = str(tmp_path)
        config.refinement = RefinementConfig(
            enabled=True,
            score_threshold=90,
            max_iterations=2,
        )

        provider = _get_refinement_provider(initial_score=85, refined_score=95)
        generate_all(config, llm_provider=provider)
        report = run_refinement(config, tmp_path, llm_provider=provider)

        for file_result in report.files:
            assert file_result.initial_score > 0
            assert file_result.final_score > 0
            assert len(file_result.iterations) > 0

    def test_all_files_pass_threshold(self, tmp_path):
        """With a good provider, all files should pass the threshold."""
        config = _load_co_planner_config()
        config.project.directory = str(tmp_path)
        config.refinement = RefinementConfig(
            enabled=True,
            score_threshold=90,
            max_iterations=3,
        )

        provider = _get_refinement_provider(initial_score=85, refined_score=95)
        generate_all(config, llm_provider=provider)
        report = run_refinement(config, tmp_path, llm_provider=provider)

        for file_result in report.files:
            assert file_result.final_score >= 90, (
                f"{file_result.file_path} scored {file_result.final_score}/100, "
                f"below 90% threshold"
            )


# ---------------------------------------------------------------------------
# Context summarization tests
# ---------------------------------------------------------------------------


class TestCoplannerContextSummarization:
    """Test project context summarization for co_planner."""

    def test_context_files_collected(self):
        """All context files are found and readable."""
        from forge_cli.generators.context_summarizer import collect_context_files

        config = _load_co_planner_config()
        files = collect_context_files(config)
        filenames = [f[0] for f in files]

        assert "PLAN.md" in filenames
        assert "ARCHITECTURE.md" in filenames
        # Spec files from specs/ directory
        spec_names = [f for f in filenames if f not in ("PLAN.md", "ARCHITECTURE.md")]
        assert len(spec_names) >= 5, f"Expected 5+ spec files, got: {spec_names}"

    def test_raw_context_includes_project_details(self):
        """Raw context includes project description and file contents."""
        from forge_cli.generators.context_summarizer import build_raw_context

        config = _load_co_planner_config()
        context = build_raw_context(config)

        assert "co-planner" in context.lower()
        assert "WebSocket" in context or "websocket" in context.lower()
        assert "suggestion" in context.lower()
        assert "pattern" in context.lower()

    def test_raw_context_includes_architecture(self):
        """Raw context includes architectural details from ARCHITECTURE.md."""
        from forge_cli.generators.context_summarizer import build_raw_context

        config = _load_co_planner_config()
        context = build_raw_context(config)

        assert "FastAPI" in context or "fastapi" in context.lower()
        assert "SuggestionEngine" in context or "suggestion_engine" in context.lower() or "suggestion engine" in context.lower()

    def test_context_summarization_saves_file(self, tmp_path):
        """Summarization saves project-context.md to .forge."""
        from forge_cli.generators.context_summarizer import summarize_context

        config = _load_co_planner_config()
        config.project.directory = str(tmp_path)

        provider = _get_refinement_provider()
        summary = summarize_context(config, tmp_path, llm_provider=provider)

        context_file = tmp_path / ".forge" / "project-context.md"
        assert context_file.exists()
        assert len(summary) > 100  # Should be substantial


# ---------------------------------------------------------------------------
# Structural integrity tests
# ---------------------------------------------------------------------------


class TestCoplannerStructuralIntegrity:
    """Verify structural requirements of generated files."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.config = _load_co_planner_config()
        self.config.project.directory = str(tmp_path)
        self.config.refinement.enabled = False
        self.project_dir = tmp_path
        provider = _get_refinement_provider()
        generate_all(self.config, llm_provider=provider)

    def test_all_agent_files_have_header(self):
        """All agent files start with the forge header comment."""
        agents_dir = self.project_dir / ".claude" / "agents"
        for agent in self.config.get_active_agents():
            content = (agents_dir / f"{agent}.md").read_text()
            assert "Generated by Forge" in content

    def test_all_agent_files_have_sections(self):
        """All agent files have required sections."""
        agents_dir = self.project_dir / ".claude" / "agents"
        for agent in self.config.get_active_agents():
            content = (agents_dir / f"{agent}.md").read_text()
            # All agents should have project context and base protocol
            assert "## " in content, f"{agent} has no sections"

    def test_agent_files_use_separators(self):
        """Agent files use --- section separators."""
        agents_dir = self.project_dir / ".claude" / "agents"
        for agent in self.config.get_active_agents():
            content = (agents_dir / f"{agent}.md").read_text()
            assert "---" in content, f"{agent} missing section separators"

    def test_team_init_plan_mentions_all_agents(self):
        """team-init-plan references all active agents."""
        content = (self.project_dir / "team-init-plan.md").read_text()
        for agent in self.config.get_active_agents():
            if agent == "team-leader":
                continue  # Team leader is the reader, not assigned
            assert agent in content, (
                f"team-init-plan.md missing reference to {agent}"
            )

    def test_claude_md_lists_agents(self):
        """CLAUDE.md lists all active agents."""
        content = (self.project_dir / "CLAUDE.md").read_text()
        for agent in self.config.get_active_agents():
            if agent == "team-leader":
                continue
            assert agent in content, f"CLAUDE.md missing reference to {agent}"

    def test_no_atlassian_sections(self):
        """Since atlassian is disabled, no atlassian sections should appear."""
        content = (self.project_dir / "CLAUDE.md").read_text()
        assert "## Atlassian Integration" not in content

    def test_settings_json_allows_all_tools(self):
        """auto-pilot settings should allow all tools."""
        settings = json.loads(
            (self.project_dir / ".claude" / "settings.json").read_text()
        )
        perms = settings.get("permissions", {})
        allow = perms.get("allow", [])
        assert len(allow) > 0, "auto-pilot should allow tools"


# ---------------------------------------------------------------------------
# Cross-file consistency tests
# ---------------------------------------------------------------------------


class TestCoplannerCrossFileConsistency:
    """Verify consistency across generated files."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.config = _load_co_planner_config()
        self.config.project.directory = str(tmp_path)
        self.config.refinement.enabled = False
        self.project_dir = tmp_path
        provider = _get_refinement_provider()
        generate_all(self.config, llm_provider=provider)

    def test_mode_consistent_across_files(self):
        """production-ready mode is referenced consistently."""
        claude_md = (self.project_dir / "CLAUDE.md").read_text()
        assert "production-ready" in claude_md

    def test_strategy_consistent_across_files(self):
        """auto-pilot strategy is referenced consistently."""
        claude_md = (self.project_dir / "CLAUDE.md").read_text()
        assert "auto-pilot" in claude_md

    def test_cost_cap_in_claude_md(self):
        """Cost cap is mentioned in CLAUDE.md."""
        claude_md = (self.project_dir / "CLAUDE.md").read_text()
        assert "$100" in claude_md or "100" in claude_md

    def test_agent_instruction_files_referenced_in_claude_md(self):
        """CLAUDE.md references agent instruction file paths."""
        claude_md = (self.project_dir / "CLAUDE.md").read_text()
        assert ".claude/agents/" in claude_md


# ---------------------------------------------------------------------------
# Context summarization quality scoring tests
# ---------------------------------------------------------------------------


class TestCoplannerContextQuality:
    """Score the quality of project context summarization.

    When FORGE_TEST_DRY_RUN=0, uses Sonnet via llm-gateway to score the
    summarization against the original source material. Verifies that the
    LLM-generated summary captures all key points without losing details.
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Generate context summary for scoring."""
        from forge_cli.generators.context_summarizer import (
            build_raw_context,
            summarize_context,
        )

        self.config = _load_co_planner_config()
        self.config.project.directory = str(tmp_path)
        self.project_dir = tmp_path

        # Build raw context for comparison
        self.raw_context = build_raw_context(self.config)

        # Generate summary
        provider = _get_refinement_provider()
        self.summary = summarize_context(
            self.config, tmp_path, llm_provider=provider,
        )
        self.context_file = tmp_path / ".forge" / "project-context.md"

    def test_summary_not_empty(self):
        """Summary should be substantial."""
        assert len(self.summary) > 200

    def test_summary_saved_to_file(self):
        """Summary is persisted to .forge/project-context.md."""
        assert self.context_file.exists()
        assert self.context_file.read_text() == self.summary

    def test_summary_mentions_project_name(self):
        """Summary includes the project name."""
        assert "co-planner" in self.summary.lower() or "co_planner" in self.summary.lower()

    def test_summary_mentions_key_technologies(self):
        """Summary references core technologies from the project."""
        lower = self.summary.lower()
        # In dry-run mode, fake provider returns a canned summary that may not
        # have all technologies. Check for at least 2 of the 4 key techs.
        found = [tech for tech in ["fastapi", "react", "websocket", "postgresql"] if tech in lower]
        if FORGE_DRY_RUN:
            assert len(found) >= 2, f"Summary missing key technologies. Found only: {found}"
        else:
            assert len(found) == 4, f"Summary missing key technologies: {set(['fastapi', 'react', 'websocket', 'postgresql']) - set(found)}"

    def test_summary_mentions_suggestion_engine(self):
        """Summary captures the multi-tier suggestion engine concept."""
        lower = self.summary.lower()
        assert "suggestion" in lower, "Summary missing suggestion engine concept"

    def test_raw_context_includes_all_spec_files(self):
        """Raw context includes content from all spec files."""
        # These are key terms from spec files that must be in raw context
        key_terms = [
            "feedback",    # feedback-loop.md
            "pattern",     # pattern-library.md
            "rag",         # rag-architecture.md
            "cache",       # suggestion-cache.md
            "pipeline",    # suggestion-pipeline.md
            "prediction",  # prediction-quality.md
        ]
        lower = self.raw_context.lower()
        for term in key_terms:
            assert term in lower, f"Raw context missing spec content for: {term}"

    @pytest.mark.skipif(FORGE_DRY_RUN, reason="LLM scoring requires real provider")
    @pytest.mark.timeout(300)
    def test_llm_scores_summary_quality(self, tmp_path):
        """Use Sonnet to score the summary against the original material.

        The summary must score >= 90% on completeness to pass.
        Uses Sonnet (not Opus) for cost-effective scoring in tests.
        """
        from pydantic import BaseModel, Field as PydanticField

        class ContextQualityScore(BaseModel):
            completeness: int = PydanticField(
                ge=0, le=100,
                description="How well the summary captures ALL details from source (0-100)",
            )
            accuracy: int = PydanticField(
                ge=0, le=100,
                description="How accurate the summary is vs source material (0-100)",
            )
            specificity: int = PydanticField(
                ge=0, le=100,
                description="Preserves exact technical details, numbers, names (0-100)",
            )
            missing_items: list[str] = PydanticField(
                default_factory=list,
                description="Key items from source that are missing in summary",
            )
            overall_score: int = PydanticField(
                ge=0, le=100,
                description="Weighted overall quality score (0-100)",
            )
            reasoning: str = PydanticField(
                description="Detailed reasoning for the score",
            )

        try:
            from llm_gateway import LLMClient, GatewayConfig
        except ImportError:
            pytest.skip("llm-gateway not installed")

        # Use Sonnet for scoring (cost-effective for test evaluation)
        gw_config = GatewayConfig(
            provider="local_claude",
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            timeout_seconds=120,
        )

        import asyncio

        async def _score():
            llm = LLMClient(config=gw_config)
            try:
                resp = await llm.complete(
                    messages=[{
                        "role": "user",
                        "content": f"""Score the quality of this project context summary.

ORIGINAL SOURCE MATERIAL:
{self.raw_context[:30000]}

GENERATED SUMMARY:
{self.summary}

SCORING CRITERIA:
- completeness (40%): Does the summary capture ALL key details from the source?
  Check: project name, all features, all technologies, all architectural components,
  all spec file contents, all phases/milestones, all API endpoints, all data models.
- accuracy (30%): Is every claim in the summary actually present in the source?
  No hallucinated details, no incorrect information.
- specificity (30%): Does the summary preserve EXACT technical details?
  Library names, version numbers, specific algorithms (WL hash, VF2), debounce times,
  cache tiers, coverage targets, endpoint paths.

For missing_items: list every important detail from the source that is NOT in the summary.

overall_score = 0.4*completeness + 0.3*accuracy + 0.3*specificity

Be strict. A score of 90+ means the summary is nearly as comprehensive as the original.""",
                    }],
                    response_model=ContextQualityScore,
                    max_tokens=4096,
                )
                return resp.content
            finally:
                await llm.close()

        score = asyncio.run(_score())

        # Log the score for debugging
        print(f"\nContext Quality Score: {score.overall_score}/100")
        print(f"  Completeness: {score.completeness}/100")
        print(f"  Accuracy: {score.accuracy}/100")
        print(f"  Specificity: {score.specificity}/100")
        if score.missing_items:
            print(f"  Missing items: {score.missing_items[:5]}")
        print(f"  Reasoning: {score.reasoning[:200]}")

        assert score.overall_score >= 90, (
            f"Context summary quality {score.overall_score}/100 below 90% threshold.\n"
            f"Missing: {score.missing_items[:5]}\n"
            f"Reasoning: {score.reasoning}"
        )
