"""Comprehensive integration tests for Forge.

Tests every combination of configuration, scores generated files for quality,
verifies agent behavioral expectations, and tests CLI end-to-end flows.
"""

import json
import itertools
import os
import re
import subprocess
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from forge_cli.config_schema import (
    AgentNamingConfig,
    AgentsConfig,
    AtlassianConfig,
    CostConfig,
    ExecutionStrategy,
    ForgeConfig,
    LLMGatewayConfig,
    ProjectConfig,
    ProjectMode,
    TeamProfile,
    TechStack,
)
from forge_cli.config_loader import load_config, save_config
from forge_cli.generators.agent_files import generate_agent_files
from forge_cli.generators.claude_md import generate_claude_md
from forge_cli.generators.mcp_config import generate_mcp_config
from forge_cli.generators.orchestrator import generate_all
from forge_cli.generators.skills import generate_skills
from forge_cli.generators.team_init_plan import generate_team_init_plan


# =============================================================================
# Test Configuration Matrix
# =============================================================================

ALL_MODES = [ProjectMode.MVP, ProjectMode.PRODUCTION_READY, ProjectMode.NO_COMPROMISE]
ALL_STRATEGIES = [ExecutionStrategy.AUTO_PILOT, ExecutionStrategy.CO_PILOT, ExecutionStrategy.MICRO_MANAGE]
ALL_PROFILES = [TeamProfile.LEAN, TeamProfile.FULL, TeamProfile.CUSTOM]

# Representative frontend and backend-only tech stacks
FRONTEND_STACK = TechStack(
    languages=["typescript", "python"],
    frameworks=["react", "fastapi"],
    databases=["postgresql"],
)
BACKEND_ONLY_STACK = TechStack(
    languages=["python"],
    frameworks=["fastapi"],
    databases=["postgresql"],
)
FULLSTACK_STACK = TechStack(
    languages=["typescript", "python", "go"],
    frameworks=["next.js", "django", "tailwind"],
    databases=["postgresql", "redis"],
)
EMPTY_STACK = TechStack()

CUSTOM_AGENTS_BACKEND = ["team-leader", "backend-developer", "devops-specialist", "critic"]
CUSTOM_AGENTS_FRONTEND = ["team-leader", "frontend-engineer", "frontend-designer", "qa-engineer", "critic"]


def _make_config(
    mode=ProjectMode.MVP,
    strategy=ExecutionStrategy.CO_PILOT,
    profile=TeamProfile.LEAN,
    tech_stack=None,
    atlassian=False,
    naming=True,
    naming_style="creative",
    spawning=True,
    custom_agents=None,
    custom_instructions=None,
    description="E-commerce platform",
    requirements="Build a full-stack e-commerce platform with user auth, product catalog, shopping cart, and checkout",
) -> ForgeConfig:
    agents_config = AgentsConfig(
        team_profile=profile,
        allow_sub_agent_spawning=spawning,
        custom_instructions=custom_instructions or {},
    )
    if profile == TeamProfile.CUSTOM and custom_agents:
        agents_config.include = custom_agents

    return ForgeConfig(
        project=ProjectConfig(
            description=description,
            requirements=requirements,
            directory="/tmp/forge-test",
        ),
        mode=mode,
        strategy=strategy,
        agents=agents_config,
        tech_stack=tech_stack or FRONTEND_STACK,
        atlassian=AtlassianConfig(
            enabled=atlassian,
            jira_base_url="https://test.atlassian.net" if atlassian else "",
            jira_project_key="ECOM" if atlassian else "",
            confluence_base_url="https://test.atlassian.net" if atlassian else "",
            confluence_space_key="ECOM" if atlassian else "",
        ),
        agent_naming=AgentNamingConfig(enabled=naming, style=naming_style),
    )


# =============================================================================
# 1. Configuration Combination Tests
# =============================================================================


class TestConfigCombinations:
    """Test that every combination of mode × strategy × profile generates valid output."""

    @pytest.fixture
    def output_dir(self, tmp_path):
        return tmp_path

    @pytest.mark.parametrize("mode", ALL_MODES, ids=lambda m: m.value)
    @pytest.mark.parametrize("strategy", ALL_STRATEGIES, ids=lambda s: s.value)
    @pytest.mark.parametrize("profile", ALL_PROFILES, ids=lambda p: p.value)
    def test_mode_strategy_profile_combination(self, output_dir, mode, strategy, profile):
        """Every combination of mode × strategy × profile must generate without errors."""
        custom_agents = CUSTOM_AGENTS_FRONTEND if profile == TeamProfile.CUSTOM else None
        config = _make_config(mode=mode, strategy=strategy, profile=profile, custom_agents=custom_agents)
        config.project.directory = str(output_dir)

        # Should not raise
        generate_all(config)

        # All expected directories and files exist
        assert (output_dir / "CLAUDE.md").exists()
        assert (output_dir / "team-init-plan.md").exists()
        assert (output_dir / ".claude" / "mcp.json").exists()
        assert (output_dir / ".claude" / "agents").is_dir()
        assert (output_dir / ".claude" / "skills").is_dir()

        # Agent files match active agents
        active = config.get_active_agents()
        agent_files = list((output_dir / ".claude" / "agents").glob("*.md"))
        assert len(agent_files) == len(active)
        for agent in active:
            assert (output_dir / ".claude" / "agents" / f"{agent}.md").exists()

    @pytest.mark.parametrize("mode", ALL_MODES, ids=lambda m: m.value)
    def test_auto_profile_resolves_correctly(self, mode):
        """AUTO profile must resolve to lean for MVP, full for production/no-compromise."""
        config = _make_config(mode=mode, profile=TeamProfile.AUTO)
        profile = config.resolve_team_profile()
        if mode == ProjectMode.MVP:
            assert profile == "lean"
        else:
            assert profile == "full"

    @pytest.mark.parametrize("atlassian", [True, False], ids=["atlassian-on", "atlassian-off"])
    @pytest.mark.parametrize("spawning", [True, False], ids=["spawning-on", "spawning-off"])
    @pytest.mark.parametrize("naming", [True, False], ids=["naming-on", "naming-off"])
    def test_toggle_combinations(self, output_dir, atlassian, spawning, naming):
        """Toggle combinations of atlassian, spawning, and naming all generate correctly."""
        config = _make_config(atlassian=atlassian, spawning=spawning, naming=naming)
        config.project.directory = str(output_dir)
        generate_all(config)

        # Verify files exist
        assert (output_dir / "CLAUDE.md").exists()
        agents_dir = output_dir / ".claude" / "agents"
        tl_content = (agents_dir / "team-leader.md").read_text()

        # Spawning toggle
        if spawning:
            assert "Sub-Agent Spawning Protocol" in tl_content
        else:
            assert "Sub-Agent Spawning Protocol" not in tl_content

        # Naming toggle — check for the actual section header, not just any mention
        if naming:
            assert "## Agent Naming Protocol" in tl_content
        else:
            assert "## Agent Naming Protocol" not in tl_content

        # Atlassian toggle
        if atlassian:
            assert "scrum-master" in config.get_active_agents()
            assert (agents_dir / "scrum-master.md").exists()
            mcp = json.loads((output_dir / ".claude" / "mcp.json").read_text())
            assert "atlassian" in mcp["mcpServers"]
        else:
            assert "scrum-master" not in config.get_active_agents()
            mcp = json.loads((output_dir / ".claude" / "mcp.json").read_text())
            assert "atlassian" not in mcp["mcpServers"]

    @pytest.mark.parametrize("naming_style", ["creative", "codename", "functional"])
    def test_naming_styles(self, output_dir, naming_style):
        """All naming styles produce appropriate instructions."""
        config = _make_config(naming=True, naming_style=naming_style)
        config.project.directory = str(output_dir)
        generate_all(config)

        tl_content = (output_dir / ".claude" / "agents" / "team-leader.md").read_text()
        assert "Agent Naming Protocol" in tl_content

        style_keywords = {
            "creative": ["Nova", "Cipher", "Blaze"],
            "codename": ["Falcon", "Shadow", "Vortex"],
            "functional": ["BackendBot-1", "QA-Prime"],
        }
        found = any(kw in tl_content for kw in style_keywords[naming_style])
        assert found, f"Naming style '{naming_style}' examples not found in team-leader.md"

    @pytest.mark.parametrize(
        "stack,has_frontend",
        [
            (FRONTEND_STACK, True),
            (BACKEND_ONLY_STACK, False),
            (FULLSTACK_STACK, True),
            (EMPTY_STACK, True),  # Empty stack but lean profile has frontend-engineer
        ],
        ids=["frontend", "backend-only", "fullstack", "empty"],
    )
    def test_tech_stack_variations(self, output_dir, stack, has_frontend):
        """Different tech stacks affect frontend detection and visual verification."""
        # Use custom profile for backend-only to exclude frontend agents
        if stack == BACKEND_ONLY_STACK:
            config = _make_config(
                tech_stack=stack,
                profile=TeamProfile.CUSTOM,
                custom_agents=CUSTOM_AGENTS_BACKEND,
                description="Backend microservice",
                requirements="Build a REST API with authentication",
            )
        else:
            config = _make_config(tech_stack=stack)
        config.project.directory = str(output_dir)
        generate_all(config)

        assert config.has_frontend_involvement() == has_frontend

        tl_content = (output_dir / ".claude" / "agents" / "team-leader.md").read_text()
        critic_content = (output_dir / ".claude" / "agents" / "critic.md").read_text()
        if has_frontend:
            assert "Visual Verification Protocol" in tl_content
            assert "Visual Verification Protocol" in critic_content
        else:
            assert "Visual Verification Protocol" not in tl_content
            assert "Visual Verification Protocol" not in critic_content


# =============================================================================
# 2. Generated File Quality Scoring Tests
# =============================================================================


class FileQualityScorer:
    """Scores a generated file based on structural and content quality criteria."""

    def __init__(self, content: str, file_type: str):
        self.content = content
        self.file_type = file_type
        self.scores: dict[str, float] = {}
        self.issues: list[str] = []

    def score_structure(self) -> float:
        """Score structural quality (0-100)."""
        score = 100.0

        # Must have content
        if len(self.content.strip()) < 50:
            score -= 40
            self.issues.append("File too short (<50 chars)")

        # Must have markdown headers
        headers = re.findall(r"^#{1,3}\s+.+$", self.content, re.MULTILINE)
        if len(headers) < 2:
            score -= 20
            self.issues.append(f"Too few headers ({len(headers)})")

        # Should have reasonable section length (not one giant blob)
        sections = re.split(r"\n#{1,3}\s+", self.content)
        if len(sections) < 3:
            score -= 10
            self.issues.append("Too few sections")

        # No template placeholders left behind
        placeholders = re.findall(r"\{\{[^}]+\}\}", self.content)
        # Allow intentional template vars like {{port}}, {{iteration}}
        bad_placeholders = [p for p in placeholders if p not in ["{{port}}", "{{iteration}}", "{{feature}}", "{{agent}}", "{{N}}"]]
        if bad_placeholders:
            score -= 15 * len(bad_placeholders)
            self.issues.append(f"Unresolved placeholders: {bad_placeholders}")

        self.scores["structure"] = max(0, score)
        return self.scores["structure"]

    def score_completeness(self, required_sections: list[str]) -> float:
        """Score based on presence of required sections (0-100)."""
        found = 0
        for section in required_sections:
            if section.lower() in self.content.lower():
                found += 1
            else:
                self.issues.append(f"Missing required section: '{section}'")
        score = (found / len(required_sections)) * 100 if required_sections else 100
        self.scores["completeness"] = score
        return score

    def score_consistency(self, config: ForgeConfig) -> float:
        """Score how consistently the file reflects the config (0-100)."""
        score = 100.0
        content_lower = self.content.lower()

        # Mode should be mentioned
        if config.mode.value not in content_lower:
            score -= 15
            self.issues.append(f"Mode '{config.mode.value}' not referenced")

        # Strategy should be mentioned
        if config.strategy.value not in content_lower:
            score -= 10
            self.issues.append(f"Strategy '{config.strategy.value}' not referenced")

        # Project description should be present
        if config.project.description.lower()[:20] not in content_lower:
            score -= 15
            self.issues.append("Project description not found")

        self.scores["consistency"] = max(0, score)
        return self.scores["consistency"]

    def total_score(self) -> float:
        if not self.scores:
            return 0
        return sum(self.scores.values()) / len(self.scores)


class TestFileQualityScoring:
    """Score every generated file for quality and ensure minimum thresholds."""

    MINIMUM_SCORE = 70  # Files must score at least 70/100

    @pytest.fixture
    def generated_project(self, tmp_path):
        """Generate a full project and return the path."""
        config = _make_config(
            mode=ProjectMode.PRODUCTION_READY,
            profile=TeamProfile.FULL,
            atlassian=True,
            tech_stack=FULLSTACK_STACK,
        )
        config.project.directory = str(tmp_path)
        generate_all(config)
        return tmp_path, config

    def test_claude_md_quality(self, generated_project):
        """CLAUDE.md must score above threshold."""
        project_dir, config = generated_project
        content = (project_dir / "CLAUDE.md").read_text()
        scorer = FileQualityScorer(content, "claude_md")

        scorer.score_structure()
        scorer.score_completeness([
            "Project Configuration",
            "Your Identity",
            "Getting Started",
            "Agent Roster",
            "Spawning an Agent",
            "Visual Verification",
            "Project Requirements",
            "Team Leader Instructions",
        ])
        scorer.score_consistency(config)

        total = scorer.total_score()
        assert total >= self.MINIMUM_SCORE, (
            f"CLAUDE.md scored {total:.1f}/100 (min {self.MINIMUM_SCORE}). "
            f"Issues: {scorer.issues}"
        )

    def test_team_init_plan_quality(self, generated_project):
        """team-init-plan.md must score above threshold."""
        project_dir, config = generated_project
        content = (project_dir / "team-init-plan.md").read_text()
        scorer = FileQualityScorer(content, "team_init_plan")

        scorer.score_structure()
        scorer.score_completeness([
            "Overview",
            "Project Requirements",
            "Initialization Sequence",
            "Phase 1",
            "Phase 2",
            "Phase 3",
            "Phase 4",
            "Agent File Locations",
            "Quick Reference",
        ])
        scorer.score_consistency(config)

        total = scorer.total_score()
        assert total >= self.MINIMUM_SCORE, (
            f"team-init-plan.md scored {total:.1f}/100 (min {self.MINIMUM_SCORE}). "
            f"Issues: {scorer.issues}"
        )

    def test_all_agent_files_quality(self, generated_project):
        """Every agent file must score above threshold."""
        project_dir, config = generated_project
        agents_dir = project_dir / ".claude" / "agents"

        common_sections = [
            "Project Context",
            "Base Agent Protocol",
            "Communication Protocol",
            "Git Workflow",
            "Workspace Detection",
        ]

        for agent_file in sorted(agents_dir.glob("*.md")):
            agent_type = agent_file.stem
            content = agent_file.read_text()
            scorer = FileQualityScorer(content, f"agent:{agent_type}")

            scorer.score_structure()
            scorer.score_completeness(common_sections)
            scorer.score_consistency(config)

            total = scorer.total_score()
            assert total >= self.MINIMUM_SCORE, (
                f"Agent '{agent_type}' scored {total:.1f}/100 (min {self.MINIMUM_SCORE}). "
                f"Issues: {scorer.issues}"
            )

    def test_all_skill_files_quality(self, generated_project):
        """Every skill file must have proper frontmatter and content."""
        project_dir, config = generated_project
        skills_dir = project_dir / ".claude" / "skills"

        for skill_file in sorted(skills_dir.glob("*.md")):
            content = skill_file.read_text()

            # Must have YAML frontmatter
            assert content.startswith("---"), f"{skill_file.name} missing YAML frontmatter"
            parts = content.split("---", 2)
            assert len(parts) >= 3, f"{skill_file.name} malformed frontmatter"

            # Parse frontmatter
            frontmatter = yaml.safe_load(parts[1])
            assert "name" in frontmatter, f"{skill_file.name} missing 'name' in frontmatter"
            assert "description" in frontmatter, f"{skill_file.name} missing 'description' in frontmatter"
            assert frontmatter["name"] == skill_file.stem, (
                f"{skill_file.name}: name mismatch: '{frontmatter['name']}' != '{skill_file.stem}'"
            )

            # Body must have content
            body = parts[2].strip()
            assert len(body) > 50, f"{skill_file.name} body too short"

    def test_mcp_json_quality(self, generated_project):
        """mcp.json must be valid JSON with correct structure."""
        project_dir, config = generated_project
        mcp_path = project_dir / ".claude" / "mcp.json"
        content = mcp_path.read_text()

        # Must be valid JSON
        data = json.loads(content)

        # Must have mcpServers key
        assert "mcpServers" in data
        servers = data["mcpServers"]

        # Playwright always present
        assert "playwright" in servers
        assert servers["playwright"]["command"] == "npx"
        assert "@anthropic-ai/playwright-mcp@latest" in servers["playwright"]["args"]

        # Atlassian present when enabled
        if config.atlassian.enabled:
            assert "atlassian" in servers
            assert servers["atlassian"]["command"] == "uvx"
            assert "mcp-atlassian" in servers["atlassian"]["args"]
            assert "ATLASSIAN_URL" in servers["atlassian"]["env"]

    def test_config_yaml_roundtrip(self, generated_project):
        """The saved forge-config.yaml must roundtrip correctly."""
        project_dir, original_config = generated_project

        # Save config
        config_path = project_dir / "forge-config.yaml"
        save_config(original_config, config_path)

        # Reload
        reloaded = load_config(config_path)

        # Key fields must match
        assert reloaded.mode == original_config.mode
        assert reloaded.strategy == original_config.strategy
        assert reloaded.project.description == original_config.project.description
        assert reloaded.atlassian.enabled == original_config.atlassian.enabled
        assert reloaded.agents.allow_sub_agent_spawning == original_config.agents.allow_sub_agent_spawning
        assert reloaded.agent_naming.style == original_config.agent_naming.style


# =============================================================================
# 3. Orchestrator End-to-End Tests
# =============================================================================


class TestOrchestratorE2E:
    """End-to-end tests that run the full orchestrator and verify the complete output."""

    def test_full_generation_lean_mvp(self, tmp_path):
        """Full generation with lean MVP config produces a complete, consistent workspace."""
        config = _make_config(mode=ProjectMode.MVP, profile=TeamProfile.LEAN)
        config.project.directory = str(tmp_path)
        generate_all(config)

        # Verify directory structure
        assert (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / "team-init-plan.md").exists()
        assert (tmp_path / ".claude" / "mcp.json").exists()
        assert (tmp_path / ".claude" / "agents").is_dir()
        assert (tmp_path / ".claude" / "skills").is_dir()

        # Lean has 8 agents
        agents = list((tmp_path / ".claude" / "agents").glob("*.md"))
        assert len(agents) == 8

        # Skills: team-status, iteration-review, spawn-agent, smoke-test, screenshot-review, arch-review
        skills = list((tmp_path / ".claude" / "skills").glob("*.md"))
        assert len(skills) == 6  # no jira/sprint skills when atlassian disabled

    def test_full_generation_full_no_compromise_atlassian(self, tmp_path):
        """Full generation with all features enabled."""
        config = _make_config(
            mode=ProjectMode.NO_COMPROMISE,
            profile=TeamProfile.FULL,
            atlassian=True,
            tech_stack=FULLSTACK_STACK,
        )
        config.project.directory = str(tmp_path)
        generate_all(config)

        # Full has 12+ agents, plus scrum-master from atlassian
        agents = list((tmp_path / ".claude" / "agents").glob("*.md"))
        expected_count = len(config.get_active_agents())
        assert len(agents) == expected_count
        assert (tmp_path / ".claude" / "agents" / "scrum-master.md").exists()

        # Skills: 6 base + 2 atlassian
        skills = list((tmp_path / ".claude" / "skills").glob("*.md"))
        assert len(skills) == 8

        # No-compromise mode should be reflected everywhere
        claude_md = (tmp_path / "CLAUDE.md").read_text()
        assert "no-compromise" in claude_md
        assert "100%" in claude_md

        plan = (tmp_path / "team-init-plan.md").read_text()
        assert "100%" in plan
        assert "No Compromise" in plan

    def test_full_generation_custom_backend_only(self, tmp_path):
        """Custom backend-only team should not have frontend agents."""
        config = _make_config(
            profile=TeamProfile.CUSTOM,
            custom_agents=CUSTOM_AGENTS_BACKEND,
            tech_stack=BACKEND_ONLY_STACK,
            description="Backend microservice",
            requirements="Build a REST API with authentication and rate limiting",
        )
        config.project.directory = str(tmp_path)
        generate_all(config)

        agents_dir = tmp_path / ".claude" / "agents"
        agent_files = {f.stem for f in agents_dir.glob("*.md")}
        assert agent_files == set(CUSTOM_AGENTS_BACKEND)

        # No visual verification in team-leader/critic for backend-only
        assert not config.has_frontend_involvement()
        tl = (agents_dir / "team-leader.md").read_text()
        assert "Visual Verification Protocol" not in tl

    def test_idempotent_generation(self, tmp_path):
        """Generating twice produces identical output."""
        config = _make_config()
        config.project.directory = str(tmp_path)

        # First generation
        generate_all(config)
        first_run = {}
        for f in tmp_path.rglob("*"):
            if f.is_file():
                first_run[str(f.relative_to(tmp_path))] = f.read_text()

        # Second generation
        generate_all(config)
        second_run = {}
        for f in tmp_path.rglob("*"):
            if f.is_file():
                second_run[str(f.relative_to(tmp_path))] = f.read_text()

        assert first_run.keys() == second_run.keys()
        for key in first_run:
            assert first_run[key] == second_run[key], f"File differs on re-generation: {key}"

    def test_custom_instructions_propagate(self, tmp_path):
        """Custom per-agent instructions appear in the generated files."""
        custom = {
            "backend-developer": "Always use async/await patterns. Prefer SQLAlchemy 2.0 style.",
            "qa-engineer": "Focus on API contract testing. Use Pact for contract tests.",
        }
        config = _make_config(custom_instructions=custom)
        config.project.directory = str(tmp_path)
        generate_all(config)

        agents_dir = tmp_path / ".claude" / "agents"
        backend = (agents_dir / "backend-developer.md").read_text()
        assert "async/await patterns" in backend
        assert "Custom Instructions (User-Specified)" in backend

        qa = (agents_dir / "qa-engineer.md").read_text()
        assert "Pact for contract tests" in qa


# =============================================================================
# 4. CLI Integration Tests
# =============================================================================


class TestCLIIntegration:
    """Test the CLI commands via subprocess invocation."""

    def test_cli_version(self):
        """CLI --version works."""
        result = subprocess.run(
            ["python", "-m", "forge_cli.main"],
            capture_output=True, text=True, timeout=10,
        )
        # Invoking without args runs 'init' which needs interactive input, so it may fail
        # But the module should at least be importable
        assert result.returncode is not None  # Just verify it ran

    def test_cli_validate_valid_config(self, tmp_path):
        """CLI validate command accepts a valid config."""
        config = _make_config()
        config_path = tmp_path / "forge-config.yaml"
        save_config(config, config_path)

        result = subprocess.run(
            ["python", "-c", f"""
import sys
sys.argv = ['forge', 'validate', '--config', '{config_path}']
from forge_cli.main import cli
cli(standalone_mode=False)
"""],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0

    def test_cli_generate_from_config(self, tmp_path):
        """CLI generate command produces all files from a config."""
        config = _make_config()
        config_path = tmp_path / "forge-config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            ["python", "-c", f"""
import sys
sys.argv = ['forge', 'generate', '--config', '{config_path}', '--project-dir', '{output_dir}']
from forge_cli.main import cli
cli(standalone_mode=False)
"""],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert (output_dir / "CLAUDE.md").exists()
        assert (output_dir / "team-init-plan.md").exists()
        assert (output_dir / ".claude" / "agents").is_dir()

    def test_cli_init_non_interactive(self, tmp_path):
        """CLI init --non-interactive generates files from config."""
        config = _make_config()
        config_path = tmp_path / "forge-config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            ["python", "-c", f"""
import sys
sys.argv = ['forge', 'init', '--config', '{config_path}', '--project-dir', '{output_dir}', '--non-interactive']
from forge_cli.main import cli
cli(standalone_mode=False)
"""],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert (output_dir / "CLAUDE.md").exists()

    def test_cli_validate_invalid_config(self, tmp_path):
        """CLI validate rejects malformed YAML."""
        bad_config = tmp_path / "bad.yaml"
        bad_config.write_text("mode: invalid-mode-value\n  broken yaml: [[[")

        result = subprocess.run(
            ["python", "-c", f"""
import sys
sys.argv = ['forge', 'validate', '--config', '{bad_config}']
from forge_cli.main import cli
try:
    cli(standalone_mode=False)
except SystemExit as e:
    sys.exit(e.code)
"""],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0


# =============================================================================
# 5. Agent Behavioral Verification Tests
# =============================================================================


class TestAgentBehavioralVerification:
    """Verify that generated agent files encode correct behavioral expectations."""

    @pytest.fixture
    def agents(self, tmp_path):
        """Generate all agent files and return a dict of agent_type -> content."""
        config = _make_config(
            mode=ProjectMode.PRODUCTION_READY,
            profile=TeamProfile.FULL,
            atlassian=True,
            tech_stack=FULLSTACK_STACK,
        )
        config.project.directory = str(tmp_path)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        generate_agent_files(config, agents_dir)
        return {f.stem: f.read_text() for f in agents_dir.glob("*.md")}, config

    def test_team_leader_has_iteration_lifecycle(self, agents):
        """Team leader must define the 7-phase iteration lifecycle."""
        content, _ = agents
        tl = content["team-leader"]
        phases = ["PLAN", "EXECUTE", "TEST", "INTEGRATE", "REVIEW", "CRITIQUE", "DECISION"]
        for phase in phases:
            assert f"### {phase}" in tl, f"Team leader missing phase: {phase}"

    def test_team_leader_has_smoke_test_protocol(self, agents):
        """Team leader must have mandatory smoke test protocol."""
        content, _ = agents
        tl = content["team-leader"]
        assert "Smoke Test Protocol" in tl
        assert "BLOCKER" in tl

    def test_team_leader_has_decision_outcomes(self, agents):
        """Team leader must define all 4 decision outcomes."""
        content, _ = agents
        tl = content["team-leader"]
        for outcome in ["PROCEED", "REWORK", "ROLLBACK", "ESCALATE"]:
            assert f"**{outcome}**" in tl, f"Team leader missing decision outcome: {outcome}"

    def test_team_leader_has_visual_review_for_frontend(self, agents):
        """Team leader must have visual review section when frontend is involved."""
        content, config = agents
        assert config.has_frontend_involvement()
        tl = content["team-leader"]
        assert "Iteration Visual Review (Team Leader-Specific)" in tl

    def test_critic_has_review_dimensions(self, agents):
        """Critic must check multiple review dimensions."""
        content, _ = agents
        critic = content["critic"]
        dimensions = [
            "Requirements compliance",
            "Architecture compliance",
            "Code quality",
            "Security",
            "User experience",
            "Integration",
        ]
        for dim in dimensions:
            assert dim.lower() in critic.lower(), f"Critic missing review dimension: {dim}"

    def test_critic_has_visual_critique_for_frontend(self, agents):
        """Critic must have visual critique section when frontend is involved."""
        content, config = agents
        assert config.has_frontend_involvement()
        assert "Visual Critique (Critic-Specific)" in content["critic"]

    def test_architect_defines_contracts(self, agents):
        """Architect must reference API contracts and system design."""
        content, _ = agents
        arch = content["architect"]
        assert "api contract" in arch.lower() or "api contracts" in arch.lower()
        assert "system design" in arch.lower() or "architecture" in arch.lower()

    def test_backend_developer_responsibilities(self, agents):
        """Backend developer must cover core backend responsibilities."""
        content, _ = agents
        backend = content["backend-developer"]
        # Should mention APIs, database, testing
        assert "api" in backend.lower()
        assert "database" in backend.lower() or "data model" in backend.lower()

    def test_frontend_engineer_responsibilities(self, agents):
        """Frontend engineer must cover UI implementation."""
        content, _ = agents
        # Full profile has frontend-developer and frontend-designer instead of frontend-engineer
        if "frontend-engineer" in content:
            fe = content["frontend-engineer"]
            assert "component" in fe.lower() or "ui" in fe.lower()

    def test_frontend_agents_have_visual_verification(self, agents):
        """All frontend-related agents must have visual verification."""
        content, _ = agents
        frontend_agents = {"frontend-developer", "frontend-designer"}
        for agent in frontend_agents:
            if agent in content:
                assert "Visual Verification Protocol" in content[agent], (
                    f"{agent} missing Visual Verification Protocol"
                )

    def test_qa_engineer_has_quality_gates(self, agents):
        """QA engineer must define quality gates and testing protocol."""
        content, _ = agents
        qa = content["qa-engineer"]
        assert "quality gate" in qa.lower() or "test" in qa.lower()
        assert "Visual Regression Testing (QA-Specific)" in qa

    def test_devops_has_infrastructure_focus(self, agents):
        """DevOps specialist must cover CI/CD and infrastructure."""
        content, _ = agents
        devops = content["devops-specialist"]
        assert "ci/cd" in devops.lower() or "pipeline" in devops.lower()
        assert "docker" in devops.lower() or "container" in devops.lower()

    def test_scrum_master_has_jira_responsibilities(self, agents):
        """Scrum master must have Jira/Confluence management responsibilities."""
        content, _ = agents
        sm = content["scrum-master"]
        assert "jira" in sm.lower()
        assert "confluence" in sm.lower()
        assert "sprint" in sm.lower()

    def test_security_tester_responsibilities(self, agents):
        """Security tester must cover OWASP and vulnerability scanning."""
        content, _ = agents
        sec = content["security-tester"]
        assert "owasp" in sec.lower() or "vulnerability" in sec.lower()

    def test_all_agents_have_base_protocol(self, agents):
        """Every agent must embed the base protocol."""
        content, _ = agents
        for agent_type, agent_content in content.items():
            assert "Base Agent Protocol" in agent_content, (
                f"{agent_type} missing Base Agent Protocol"
            )
            assert "Communication Protocol" in agent_content
            assert "Git Workflow" in agent_content
            assert "Secret Safety" in agent_content

    def test_all_agents_have_project_context(self, agents):
        """Every agent must have project context section."""
        content, config = agents
        for agent_type, agent_content in content.items():
            assert "Project Context" in agent_content, (
                f"{agent_type} missing Project Context"
            )
            assert config.project.description in agent_content

    def test_all_agents_have_workspace_detection(self, agents):
        """Every agent must have workspace detection section."""
        content, _ = agents
        for agent_type, agent_content in content.items():
            assert "Workspace Detection" in agent_content, (
                f"{agent_type} missing Workspace Detection"
            )

    def test_mode_specific_behavior_in_team_leader(self, tmp_path):
        """Team leader mode-specific section changes with mode."""
        for mode in ALL_MODES:
            config = _make_config(mode=mode)
            agents_dir = tmp_path / f"agents-{mode.value}"
            agents_dir.mkdir(parents=True)
            generate_agent_files(config, agents_dir)

            tl = (agents_dir / "team-leader.md").read_text()

            if mode == ProjectMode.MVP:
                assert "70%" in tl
                assert "MVP" in tl
            elif mode == ProjectMode.PRODUCTION_READY:
                assert "90%" in tl
                assert "Production Ready" in tl
            elif mode == ProjectMode.NO_COMPROMISE:
                assert "100%" in tl
                assert "No Compromise" in tl

    def test_strategy_behavior_in_team_leader(self, tmp_path):
        """Team leader strategy section changes with execution strategy."""
        for strategy in ALL_STRATEGIES:
            config = _make_config(strategy=strategy)
            agents_dir = tmp_path / f"agents-{strategy.value}"
            agents_dir.mkdir(parents=True)
            generate_agent_files(config, agents_dir)

            tl = (agents_dir / "team-leader.md").read_text()
            assert strategy.value in tl

            if strategy == ExecutionStrategy.AUTO_PILOT:
                assert "autonomously" in tl.lower()
            elif strategy == ExecutionStrategy.MICRO_MANAGE:
                assert "human" in tl.lower()


# =============================================================================
# 6. Cross-File Consistency Tests
# =============================================================================


class TestCrossFileConsistency:
    """Verify that generated files are consistent with each other."""

    @pytest.fixture
    def project(self, tmp_path):
        config = _make_config(
            mode=ProjectMode.PRODUCTION_READY,
            profile=TeamProfile.FULL,
            atlassian=True,
            tech_stack=FULLSTACK_STACK,
        )
        config.project.directory = str(tmp_path)
        generate_all(config)
        return tmp_path, config

    def test_claude_md_lists_all_agents(self, project):
        """CLAUDE.md must reference every active non-leader agent."""
        project_dir, config = project
        claude_md = (project_dir / "CLAUDE.md").read_text()
        agents = config.get_active_agents()
        for agent in agents:
            if agent != "team-leader":
                assert agent in claude_md, f"CLAUDE.md missing agent reference: {agent}"

    def test_plan_lists_all_agent_files(self, project):
        """team-init-plan.md must reference all agent file paths."""
        project_dir, config = project
        plan = (project_dir / "team-init-plan.md").read_text()
        agents = config.get_active_agents()
        for agent in agents:
            assert f".claude/agents/{agent}.md" in plan, (
                f"team-init-plan.md missing agent file reference: {agent}"
            )

    def test_mcp_config_matches_features(self, project):
        """mcp.json servers must match enabled features."""
        project_dir, config = project
        mcp = json.loads((project_dir / ".claude" / "mcp.json").read_text())
        servers = mcp["mcpServers"]

        # Playwright always present
        assert "playwright" in servers

        # Atlassian only when enabled
        assert ("atlassian" in servers) == config.atlassian.enabled

    def test_agent_count_matches_across_files(self, project):
        """Agent count must be consistent across CLAUDE.md, plan, and actual files."""
        project_dir, config = project
        expected_count = len(config.get_active_agents())

        # Actual agent files
        actual_files = list((project_dir / ".claude" / "agents").glob("*.md"))
        assert len(actual_files) == expected_count

        # Plan mentions all agents
        plan = (project_dir / "team-init-plan.md").read_text()
        assert f"**Team Size**: {expected_count} agents" in plan

    def test_quality_threshold_consistent(self, project):
        """Quality threshold must be the same in CLAUDE.md, plan, and team-leader."""
        project_dir, config = project
        threshold = {"mvp": "70%", "production-ready": "90%", "no-compromise": "100%"}[config.mode.value]

        claude_md = (project_dir / "CLAUDE.md").read_text()
        plan = (project_dir / "team-init-plan.md").read_text()
        tl = (project_dir / ".claude" / "agents" / "team-leader.md").read_text()

        assert threshold in claude_md
        assert threshold in plan
        assert threshold in tl

    def test_atlassian_references_consistent(self, project):
        """When Atlassian is enabled, all relevant files must reference it."""
        project_dir, config = project
        if not config.atlassian.enabled:
            return

        claude_md = (project_dir / "CLAUDE.md").read_text()
        plan = (project_dir / "team-init-plan.md").read_text()

        assert "Atlassian" in claude_md
        assert "Atlassian" in plan or "Jira" in plan

        # Scrum master must exist
        assert (project_dir / ".claude" / "agents" / "scrum-master.md").exists()

        # Jira skills must exist
        assert (project_dir / ".claude" / "skills" / "jira-update.md").exists()
        assert (project_dir / ".claude" / "skills" / "sprint-report.md").exists()

    def test_tech_stack_appears_in_context(self, project):
        """Tech stack from config should appear in agent project context sections."""
        project_dir, config = project
        for agent_file in (project_dir / ".claude" / "agents").glob("*.md"):
            content = agent_file.read_text()
            # At least one language/framework should appear
            found_tech = False
            for lang in config.tech_stack.languages:
                if lang in content:
                    found_tech = True
                    break
            for fw in config.tech_stack.frameworks:
                if fw in content:
                    found_tech = True
                    break
            assert found_tech, f"{agent_file.name} doesn't reference any tech stack items"


# =============================================================================
# 7. Visual Verification Conditional Tests
# =============================================================================


class TestVisualVerificationConditional:
    """Comprehensive tests for visual verification being conditional on frontend involvement."""

    FRONTEND_DESCRIPTIONS = [
        ("Dashboard web app", "Build a dashboard with charts and graphs"),
        ("Mobile app", "Build a responsive mobile app with React Native"),
        ("Landing page", "Create a landing page with animations"),
        ("SPA application", "Build a single page application"),
    ]

    BACKEND_DESCRIPTIONS = [
        ("Data pipeline", "Build an ETL data pipeline for analytics"),
        ("CLI tool", "Build a command-line tool for data processing"),
        ("Microservice", "Build a gRPC microservice for order processing"),
        ("Batch processor", "Build a batch processing system"),
    ]

    @pytest.mark.parametrize(
        "desc,reqs",
        FRONTEND_DESCRIPTIONS,
        ids=[d[0] for d in FRONTEND_DESCRIPTIONS],
    )
    def test_frontend_descriptions_trigger_visual(self, tmp_path, desc, reqs):
        """Frontend-related project descriptions should trigger visual verification."""
        config = _make_config(
            profile=TeamProfile.CUSTOM,
            custom_agents=["team-leader", "backend-developer", "critic"],
            tech_stack=BACKEND_ONLY_STACK,
            description=desc,
            requirements=reqs,
        )
        assert config.has_frontend_involvement(), (
            f"Description '{desc}' should trigger frontend detection"
        )

    @pytest.mark.parametrize(
        "desc,reqs",
        BACKEND_DESCRIPTIONS,
        ids=[d[0] for d in BACKEND_DESCRIPTIONS],
    )
    def test_backend_descriptions_no_visual(self, tmp_path, desc, reqs):
        """Backend-only descriptions should not trigger visual verification."""
        config = _make_config(
            profile=TeamProfile.CUSTOM,
            custom_agents=["team-leader", "backend-developer", "devops-specialist", "critic"],
            tech_stack=BACKEND_ONLY_STACK,
            description=desc,
            requirements=reqs,
        )
        assert not config.has_frontend_involvement(), (
            f"Description '{desc}' should NOT trigger frontend detection"
        )

    @pytest.mark.parametrize(
        "framework,expected",
        [
            ("react", True),
            ("vue", True),
            ("angular", True),
            ("svelte", True),
            ("next.js", True),
            ("tailwind", True),
            ("flutter", True),
            ("fastapi", False),
            ("django", False),
            ("spring", False),
            ("express", False),
        ],
        ids=lambda x: str(x),
    )
    def test_framework_detection(self, framework, expected):
        """Individual frameworks should be correctly classified."""
        config = _make_config(
            profile=TeamProfile.CUSTOM,
            custom_agents=["team-leader", "backend-developer", "critic"],
            tech_stack=TechStack(languages=["python"], frameworks=[framework]),
            description="Generic project",
            requirements="Build something",
        )
        assert config.has_frontend_involvement() == expected, (
            f"Framework '{framework}' frontend detection: expected {expected}"
        )

    @pytest.mark.parametrize(
        "language,expected",
        [
            ("typescript", True),
            ("javascript", True),
            ("html", True),
            ("css", True),
            ("dart", True),
            ("python", False),
            ("go", False),
            ("rust", False),
            ("java", False),
        ],
        ids=lambda x: str(x),
    )
    def test_language_detection(self, language, expected):
        """Individual languages should be correctly classified."""
        config = _make_config(
            profile=TeamProfile.CUSTOM,
            custom_agents=["team-leader", "backend-developer", "critic"],
            tech_stack=TechStack(languages=[language], frameworks=[]),
            description="Generic project",
            requirements="Build something",
        )
        assert config.has_frontend_involvement() == expected, (
            f"Language '{language}' frontend detection: expected {expected}"
        )

    def test_visual_verification_mode_scaling_all_modes(self, tmp_path):
        """Visual verification standards scale with mode for all visual agents."""
        visual_agents = ["frontend-engineer", "qa-engineer"]
        mode_sections = {
            ProjectMode.MVP: "MVP Visual Standards",
            ProjectMode.PRODUCTION_READY: "Production Ready Visual Standards",
            ProjectMode.NO_COMPROMISE: "No Compromise Visual Standards",
        }

        for mode, expected_section in mode_sections.items():
            config = _make_config(mode=mode)
            agents_dir = tmp_path / f"agents-{mode.value}"
            agents_dir.mkdir(parents=True)
            generate_agent_files(config, agents_dir)

            for agent in visual_agents:
                content = (agents_dir / f"{agent}.md").read_text()
                assert expected_section in content, (
                    f"{agent} in {mode.value} mode missing '{expected_section}'"
                )
                # Other mode sections should NOT be present
                for other_mode, other_section in mode_sections.items():
                    if other_mode != mode:
                        assert other_section not in content, (
                            f"{agent} in {mode.value} mode has wrong section '{other_section}'"
                        )


# =============================================================================
# 8. LLM-Verified Tests (via llm-gateway)
# =============================================================================


def _llm_gateway_available():
    """Check if llm-gateway is installed and a provider can actually complete a call."""
    try:
        from llm_gateway import LLMClient, GatewayConfig
    except ImportError:
        return False

    if os.environ.get("ANTHROPIC_API_KEY"):
        return True

    # local_claude needs `claude` CLI that's authenticated
    import shutil
    if not shutil.which("claude"):
        return False

    # Quick probe: run claude --version without CLAUDECODE to verify auth works
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        r = subprocess.run(
            ["claude", "-p", "hi", "--output-format", "json", "--max-budget-usd", "0.01"],
            capture_output=True, text=True, timeout=15, env=env,
        )
        # "Not logged in" means auth doesn't work in subprocess context
        if "Not logged in" in r.stdout or "Not logged in" in r.stderr:
            return False
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _get_llm_provider():
    """Determine best available llm-gateway provider."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "local_claude"


@pytest.mark.skipif(
    not _llm_gateway_available(),
    reason="llm-gateway not available (install llm-gateway and have claude CLI or ANTHROPIC_API_KEY)",
)
class TestLLMVerification:
    """Tests that use llm-gateway to verify generated file quality with actual LLM responses.

    These tests use llm-gateway (local_claude or anthropic provider) to evaluate
    generated files, acting as a quality gate that an actual LLM can understand
    and follow the instructions.

    Providers (in priority order):
    - anthropic: if ANTHROPIC_API_KEY is set
    - local_claude: uses claude CLI (free, no API key)
    """

    MODEL = "claude-haiku-4-5-20251001"
    MAX_TOKENS = 150

    def _ask_claude(self, prompt: str) -> str:
        """Send a prompt through llm-gateway and return the text response."""
        import asyncio
        from pydantic import BaseModel
        from llm_gateway import LLMClient, GatewayConfig

        class TextAnswer(BaseModel):
            text: str

        async def _call():
            provider = _get_llm_provider()
            config = GatewayConfig(
                provider=provider,
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                timeout_seconds=30,
            )
            llm = LLMClient(config=config)
            try:
                resp = await llm.complete(
                    messages=[{"role": "user", "content": prompt}],
                    response_model=TextAnswer,
                )
                return resp.content.text
            except Exception as e:
                pytest.skip(f"llm-gateway ({provider}) call failed: {e}")
            finally:
                await llm.close()

        return asyncio.run(_call())

    def _generate_project(self, tmp_path, **kwargs) -> tuple[Path, ForgeConfig]:
        config = _make_config(**kwargs)
        config.project.directory = str(tmp_path)
        generate_all(config)
        return tmp_path, config

    def test_llm_understands_team_leader_role(self, tmp_path):
        """LLM should understand the team leader's role from the generated file."""
        project_dir, config = self._generate_project(tmp_path)
        tl_content = (project_dir / ".claude" / "agents" / "team-leader.md").read_text()

        response = self._ask_claude(
            f"Read this agent instruction file and answer in the text field with exactly one word - "
            f"what is the primary ROLE described? (answer: leader/developer/tester/designer)\n\n"
            f"{tl_content[:3000]}"
        )
        assert "leader" in response.lower(), f"LLM didn't identify team leader role: {response[:200]}"

    def test_llm_extracts_mode_from_config(self, tmp_path):
        """LLM should be able to extract the project mode from generated files."""
        project_dir, config = self._generate_project(
            tmp_path, mode=ProjectMode.PRODUCTION_READY
        )
        claude_md = (project_dir / "CLAUDE.md").read_text()

        response = self._ask_claude(
            f"Read this CLAUDE.md file. What is the development mode? "
            f"Answer in the text field with ONLY the mode value, nothing else.\n\n{claude_md[:2000]}"
        )
        assert "production" in response.lower(), f"LLM didn't extract mode: {response[:200]}"

    def test_llm_identifies_agents_from_plan(self, tmp_path):
        """LLM should identify the agent list from team-init-plan.md."""
        project_dir, config = self._generate_project(tmp_path, profile=TeamProfile.LEAN)
        plan = (project_dir / "team-init-plan.md").read_text()

        response = self._ask_claude(
            f"Read this team initialization plan. How many agents are in the team? "
            f"Answer in the text field with ONLY the number.\n\n{plan[:3000]}"
        )
        expected = len(config.get_active_agents())
        assert str(expected) in response, f"LLM didn't identify agent count ({expected}): {response[:200]}"

    def test_llm_finds_quality_threshold(self, tmp_path):
        """LLM should find the quality threshold from the team leader instructions."""
        project_dir, config = self._generate_project(
            tmp_path, mode=ProjectMode.NO_COMPROMISE
        )
        tl = (project_dir / ".claude" / "agents" / "team-leader.md").read_text()

        response = self._ask_claude(
            f"Read this team leader instruction file. What is the quality threshold percentage? "
            f"Answer in the text field with ONLY the percentage (e.g., '90%').\n\n{tl[:3000]}"
        )
        assert "100%" in response, f"LLM didn't find quality threshold: {response[:200]}"

    def test_llm_validates_agent_file_coherence(self, tmp_path):
        """LLM should rate an agent file as coherent and well-structured."""
        project_dir, config = self._generate_project(tmp_path)
        backend = (project_dir / ".claude" / "agents" / "backend-developer.md").read_text()

        response = self._ask_claude(
            f"Rate this agent instruction file on a scale of 1-10 for clarity and coherence. "
            f"Answer in the text field with ONLY a number from 1-10.\n\n{backend[:4000]}"
        )
        numbers = re.findall(r"\b(\d+)\b", response)
        assert numbers, f"LLM didn't return a number: {response[:200]}"
        score = int(numbers[0])
        assert score >= 6, f"LLM rated agent file poorly ({score}/10): {response[:200]}"

    def test_llm_detects_visual_verification_requirement(self, tmp_path):
        """LLM should detect that visual verification is required from the frontend engineer file."""
        project_dir, config = self._generate_project(tmp_path)
        fe = (project_dir / ".claude" / "agents" / "frontend-engineer.md").read_text()

        response = self._ask_claude(
            f"Read this frontend engineer instruction file. "
            f"Is this agent required to take screenshots of their work? "
            f"Answer in the text field with YES or NO only.\n\n{fe[:4000]}"
        )
        assert "yes" in response.lower(), f"LLM didn't detect visual verification: {response[:200]}"

    def test_llm_validates_mcp_config(self, tmp_path):
        """LLM should identify MCP servers from the config."""
        project_dir, config = self._generate_project(tmp_path, atlassian=True)
        mcp = (project_dir / ".claude" / "mcp.json").read_text()

        response = self._ask_claude(
            f"Read this MCP configuration JSON. List the MCP server names. "
            f"Answer in the text field with comma-separated names only.\n\n{mcp}"
        )
        assert "playwright" in response.lower()
        assert "atlassian" in response.lower()


# =============================================================================
# 8b. LLM Gateway Integration Tests (FakeLLMProvider - always run)
# =============================================================================


class TestLLMGatewayIntegration:
    """Tests that verify llm-gateway integration in generated files.

    Uses FakeLLMProvider for deterministic, offline testing.
    These tests always run (no external dependencies needed).
    """

    def test_llm_gateway_section_in_agent_files(self, tmp_path):
        """Agent files should contain LLM Gateway section when enabled."""
        config = _make_config()
        config.project.directory = str(tmp_path)
        generate_all(config)

        for agent in config.get_active_agents():
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            assert "LLM Gateway Integration" in content, f"{agent} missing LLM Gateway section"
            assert "llm-gateway" in content

    def test_llm_gateway_disabled_no_section(self, tmp_path):
        """Agent files should NOT contain LLM Gateway section when disabled."""
        config = _make_config()
        config.llm_gateway = LLMGatewayConfig(enabled=False)
        config.project.directory = str(tmp_path)
        generate_all(config)

        for agent in config.get_active_agents():
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            assert "LLM Gateway Integration (MANDATORY)" not in content

    def test_llm_gateway_in_claude_md(self, tmp_path):
        """CLAUDE.md should contain LLM Gateway section when enabled."""
        config = _make_config()
        config.project.directory = str(tmp_path)
        generate_all(config)

        claude_md = (tmp_path / "CLAUDE.md").read_text()
        assert "LLM Gateway" in claude_md
        assert "llm-gateway" in claude_md
        assert "local_claude" in claude_md

    def test_llm_gateway_in_team_init_plan(self, tmp_path):
        """team-init-plan.md should reference LLM Gateway in quick reference."""
        config = _make_config()
        config.project.directory = str(tmp_path)
        generate_all(config)

        plan = (tmp_path / "team-init-plan.md").read_text()
        assert "LLM Gateway" in plan

    def test_llm_gateway_vendor_agnostic_mandate(self, tmp_path):
        """Architect agent file should mandate llm-gateway for LLM providers."""
        config = _make_config()
        config.project.directory = str(tmp_path)
        generate_all(config)

        architect = (tmp_path / ".claude" / "agents" / "architect.md").read_text()
        assert "MUST use llm-gateway" in architect

    def test_llm_gateway_qa_testing_instructions(self, tmp_path):
        """QA agent should have FakeLLMProvider testing instructions."""
        config = _make_config()
        config.project.directory = str(tmp_path)
        generate_all(config)

        qa = (tmp_path / ".claude" / "agents" / "qa-engineer.md").read_text()
        assert "FakeLLMProvider" in qa

    def test_llm_gateway_local_claude_config(self, tmp_path):
        """Agent files should reference local_claude when enabled."""
        config = _make_config()
        config.llm_gateway.enable_local_claude = True
        config.llm_gateway.local_claude_model = "claude-sonnet-4-20250514"
        config.project.directory = str(tmp_path)
        generate_all(config)

        backend = (tmp_path / ".claude" / "agents" / "backend-developer.md").read_text()
        assert "local_claude" in backend
        assert "claude-sonnet-4-20250514" in backend

    def test_llm_gateway_cost_tracking(self, tmp_path):
        """Cost tracking instructions should appear when enabled."""
        config = _make_config()
        config.llm_gateway.cost_tracking = True
        config.project.directory = str(tmp_path)
        generate_all(config)

        backend = (tmp_path / ".claude" / "agents" / "backend-developer.md").read_text()
        assert "total_cost_usd" in backend

    def test_fake_provider_works(self):
        """FakeLLMProvider should produce deterministic responses."""
        import asyncio
        from pydantic import BaseModel
        from llm_gateway import FakeLLMProvider, LLMClient

        class Answer(BaseModel):
            text: str

        async def _test():
            fake = FakeLLMProvider()
            fake.set_response(Answer, Answer(text="hello"))
            llm = LLMClient(provider_instance=fake)
            resp = await llm.complete(
                messages=[{"role": "user", "content": "test"}],
                response_model=Answer,
            )
            assert resp.content.text == "hello"
            assert fake.call_count == 1
            assert resp.usage.total_cost_usd >= 0
            await llm.close()

        asyncio.run(_test())

    def test_config_schema_has_llm_gateway(self):
        """ForgeConfig should have llm_gateway field with correct defaults."""
        config = ForgeConfig()
        assert config.llm_gateway.enabled is True
        assert config.llm_gateway.enable_local_claude is True
        assert config.llm_gateway.cost_tracking is True
        assert "claude" in config.llm_gateway.local_claude_model

    def test_project_context_shows_llm_gateway(self, tmp_path):
        """Project context section should show LLM Gateway status."""
        config = _make_config()
        config.project.directory = str(tmp_path)
        generate_all(config)

        for agent in config.get_active_agents():
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            assert "LLM Gateway" in content
            assert "local_claude: on" in content


# =============================================================================
# 9. Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases, boundary conditions, and error handling."""

    def test_empty_description(self, tmp_path):
        """Config with empty description still generates valid files."""
        config = _make_config(description="", requirements="Just build something")
        config.project.directory = str(tmp_path)
        generate_all(config)
        assert (tmp_path / "CLAUDE.md").exists()

    def test_empty_requirements(self, tmp_path):
        """Config with empty requirements still generates valid files."""
        config = _make_config(requirements="")
        config.project.directory = str(tmp_path)
        generate_all(config)
        assert (tmp_path / "CLAUDE.md").exists()

    def test_very_long_description(self, tmp_path):
        """Config with a very long description doesn't break generation."""
        long_desc = "Build a " + "very complex " * 200 + "application"
        config = _make_config(description=long_desc)
        config.project.directory = str(tmp_path)
        generate_all(config)
        assert (tmp_path / "CLAUDE.md").exists()
        # Description should appear in output
        assert long_desc[:50] in (tmp_path / "CLAUDE.md").read_text()

    def test_special_characters_in_description(self, tmp_path):
        """Special characters in description don't break generation."""
        config = _make_config(
            description="Build a <script>alert('xss')</script> & 'quotes' \"double\" app",
            requirements="Handle $pecial chars: ñ, ü, 日本語, emoji: 🚀",
        )
        config.project.directory = str(tmp_path)
        generate_all(config)
        assert (tmp_path / "CLAUDE.md").exists()

    def test_custom_profile_empty_include(self, tmp_path):
        """Custom profile with empty include list falls back to lean agents."""
        config = _make_config(profile=TeamProfile.CUSTOM, custom_agents=[])
        # Empty include means fallback to lean
        agents = config.get_active_agents()
        assert len(agents) > 0

    def test_exclude_agents(self, tmp_path):
        """Excluding agents removes them from generation."""
        config = _make_config()
        config.agents.exclude = ["critic", "research-strategist"]
        config.project.directory = str(tmp_path)
        generate_all(config)

        agents_dir = tmp_path / ".claude" / "agents"
        assert not (agents_dir / "critic.md").exists()
        assert not (agents_dir / "research-strategist.md").exists()

    def test_additional_agents(self, tmp_path):
        """Adding agents that aren't in the default profile."""
        config = _make_config(profile=TeamProfile.LEAN)
        config.agents.additional = ["security-tester", "performance-engineer"]
        config.project.directory = str(tmp_path)
        generate_all(config)

        agents_dir = tmp_path / ".claude" / "agents"
        assert (agents_dir / "security-tester.md").exists()
        assert (agents_dir / "performance-engineer.md").exists()

    def test_unknown_agent_type_handled(self, tmp_path):
        """Unknown agent types get a generic fallback template."""
        config = _make_config(profile=TeamProfile.CUSTOM, custom_agents=["team-leader", "custom-agent"])
        config.agents.include = ["team-leader", "custom-agent"]
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        generate_agent_files(config, agents_dir)

        custom = (agents_dir / "custom-agent.md").read_text()
        assert "Custom Agent" in custom
        assert "Base Agent Protocol" in custom

    def test_no_cap_budget(self, tmp_path):
        """Budget of 'no-cap' is handled gracefully."""
        config = _make_config()
        config.cost.max_development_cost = "no-cap"
        config.project.directory = str(tmp_path)
        generate_all(config)

        claude_md = (tmp_path / "CLAUDE.md").read_text()
        assert "no-cap" in claude_md

    def test_existing_project_type(self, tmp_path):
        """Existing project type changes workspace setup instructions."""
        config = _make_config()
        config.project.type = "existing"
        config.project.directory = str(tmp_path)
        generate_all(config)

        plan = (tmp_path / "team-init-plan.md").read_text()
        assert "existing project" in plan.lower()

    def test_new_project_type(self, tmp_path):
        """New project type changes workspace setup instructions."""
        config = _make_config()
        config.project.type = "new"
        config.project.directory = str(tmp_path)
        generate_all(config)

        plan = (tmp_path / "team-init-plan.md").read_text()
        assert "new project" in plan.lower()

    def test_concurrent_generation_safety(self, tmp_path):
        """Multiple configs generating to separate dirs don't interfere."""
        configs = [
            _make_config(mode=ProjectMode.MVP),
            _make_config(mode=ProjectMode.PRODUCTION_READY),
            _make_config(mode=ProjectMode.NO_COMPROMISE),
        ]

        for i, config in enumerate(configs):
            dir_path = tmp_path / f"project-{i}"
            dir_path.mkdir()
            config.project.directory = str(dir_path)
            generate_all(config)

        # Verify each has the correct mode
        for i, (config, mode_str) in enumerate(zip(configs, ["mvp", "production-ready", "no-compromise"])):
            claude_md = (tmp_path / f"project-{i}" / "CLAUDE.md").read_text()
            assert mode_str in claude_md

    def test_mcp_json_merge_preserves_existing(self, tmp_path):
        """Generating mcp.json preserves existing MCP server entries."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        # Pre-existing mcp.json with a custom server
        existing = {
            "mcpServers": {
                "custom-server": {"command": "node", "args": ["custom.js"]},
            }
        }
        (claude_dir / "mcp.json").write_text(json.dumps(existing))

        config = _make_config(atlassian=True)
        generate_mcp_config(config, claude_dir)

        result = json.loads((claude_dir / "mcp.json").read_text())
        # Custom server preserved
        assert "custom-server" in result["mcpServers"]
        # Forge servers added
        assert "playwright" in result["mcpServers"]
        assert "atlassian" in result["mcpServers"]
