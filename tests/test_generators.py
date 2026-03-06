"""Tests for file generators."""

import json
import tempfile
from pathlib import Path

from forge_cli.config_schema import (
    AgentNamingConfig,
    AgentsConfig,
    AtlassianConfig,
    ExecutionStrategy,
    ForgeConfig,
    ProjectConfig,
    ProjectMode,
    TeamProfile,
)
from forge_cli.generators.agent_files import generate_agent_files
from forge_cli.generators.claude_md import generate_claude_md
from forge_cli.generators.mcp_config import generate_mcp_config
from forge_cli.generators.skills import generate_skills
from forge_cli.generators.team_init_plan import generate_team_init_plan


def _make_config(**overrides) -> ForgeConfig:
    defaults = dict(
        project=ProjectConfig(
            description="Test Project",
            requirements="Build a REST API with auth",
            directory="/tmp/test-forge",
        ),
        mode=ProjectMode.MVP,
        strategy=ExecutionStrategy.CO_PILOT,
        agents=AgentsConfig(team_profile=TeamProfile.LEAN),
        atlassian=AtlassianConfig(enabled=False),
        agent_naming=AgentNamingConfig(enabled=True, style="creative"),
    )
    defaults.update(overrides)
    return ForgeConfig(**defaults)


class TestAgentFileGeneration:
    def test_generates_all_agent_files(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        active = config.get_active_agents()
        for agent in active:
            agent_file = agents_dir / f"{agent}.md"
            assert agent_file.exists(), f"Missing agent file: {agent}.md"

    def test_agent_files_contain_project_context(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Test Project" in content
        assert "mvp" in content
        assert "co-pilot" in content

    def test_agent_files_contain_base_protocol(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Base Agent Protocol" in content
        assert "Git Workflow" in content
        assert "Secret Safety" in content

    def test_agent_files_contain_sub_agent_spawning(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Sub-Agent Spawning Protocol" in content

    def test_agent_files_no_spawning_when_disabled(self, tmp_path):
        config = _make_config(agents=AgentsConfig(team_profile=TeamProfile.LEAN, allow_sub_agent_spawning=False))
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Sub-Agent Spawning Protocol" not in content

    def test_agent_files_contain_naming_protocol(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Agent Naming Protocol" in content

    def test_agent_files_contain_atlassian_when_enabled(self, tmp_path):
        config = _make_config(atlassian=AtlassianConfig(enabled=True, jira_project_key="TEST"))
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Atlassian Integration" in content
        assert "TEST" in content

    def test_scrum_master_generated_with_atlassian(self, tmp_path):
        config = _make_config(atlassian=AtlassianConfig(enabled=True))
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        assert (agents_dir / "scrum-master.md").exists()
        content = (agents_dir / "scrum-master.md").read_text()
        assert "Sprint Management" in content
        assert "The Human Experience" in content

    def test_custom_instructions_included(self, tmp_path):
        config = _make_config(
            agents=AgentsConfig(
                team_profile=TeamProfile.LEAN,
                custom_instructions={"backend-developer": "Always use PostgreSQL for the database."},
            )
        )
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Always use PostgreSQL" in content


class TestClaudeMdGeneration:
    def test_generates_claude_md(self, tmp_path):
        config = _make_config()
        config.project.directory = str(tmp_path)

        generate_claude_md(config, tmp_path)

        assert (tmp_path / "CLAUDE.md").exists()

    def test_claude_md_contains_project_info(self, tmp_path):
        config = _make_config()
        config.project.directory = str(tmp_path)

        generate_claude_md(config, tmp_path)

        content = (tmp_path / "CLAUDE.md").read_text()
        assert "Test Project" in content
        assert "Team Leader" in content
        assert "team-init-plan.md" in content

    def test_claude_md_lists_agents(self, tmp_path):
        config = _make_config()
        config.project.directory = str(tmp_path)

        generate_claude_md(config, tmp_path)

        content = (tmp_path / "CLAUDE.md").read_text()
        assert "backend-developer" in content
        assert ".claude/agents/" in content


class TestMcpConfigGeneration:
    def test_generates_mcp_json(self, tmp_path):
        config = _make_config(
            atlassian=AtlassianConfig(
                enabled=True,
                jira_base_url="https://test.atlassian.net",
            )
        )
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        generate_mcp_config(config, claude_dir)

        mcp_path = claude_dir / "mcp.json"
        assert mcp_path.exists()

        data = json.loads(mcp_path.read_text())
        assert "mcpServers" in data
        assert "atlassian" in data["mcpServers"]
        assert data["mcpServers"]["atlassian"]["env"]["ATLASSIAN_URL"] == "https://test.atlassian.net"

    def test_always_has_playwright(self, tmp_path):
        config = _make_config(atlassian=AtlassianConfig(enabled=False))
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        generate_mcp_config(config, claude_dir)

        mcp_path = claude_dir / "mcp.json"
        assert mcp_path.exists()
        data = json.loads(mcp_path.read_text())
        assert "playwright" in data["mcpServers"]
        assert "atlassian" not in data["mcpServers"]

    def test_has_both_when_atlassian_enabled(self, tmp_path):
        config = _make_config(
            atlassian=AtlassianConfig(enabled=True, jira_base_url="https://test.atlassian.net")
        )
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        generate_mcp_config(config, claude_dir)

        data = json.loads((claude_dir / "mcp.json").read_text())
        assert "playwright" in data["mcpServers"]
        assert "atlassian" in data["mcpServers"]

    def test_generates_env_example(self, tmp_path):
        config = _make_config(
            atlassian=AtlassianConfig(enabled=True, jira_base_url="https://test.atlassian.net")
        )
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        generate_mcp_config(config, claude_dir)

        env_example = tmp_path / ".env.example"
        assert env_example.exists()
        content = env_example.read_text()
        assert "ATLASSIAN_URL" in content


class TestSkillsGeneration:
    def test_generates_core_skills(self, tmp_path):
        config = _make_config()
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        generate_skills(config, skills_dir)

        assert (skills_dir / "team-status.md").exists()
        assert (skills_dir / "iteration-review.md").exists()
        assert (skills_dir / "smoke-test.md").exists()
        assert (skills_dir / "arch-review.md").exists()

    def test_generates_spawn_skill_when_enabled(self, tmp_path):
        config = _make_config()
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        generate_skills(config, skills_dir)

        assert (skills_dir / "spawn-agent.md").exists()

    def test_generates_jira_skills_when_atlassian_enabled(self, tmp_path):
        config = _make_config(atlassian=AtlassianConfig(enabled=True))
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        generate_skills(config, skills_dir)

        assert (skills_dir / "jira-update.md").exists()
        assert (skills_dir / "sprint-report.md").exists()


class TestTeamInitPlanGeneration:
    def test_generates_team_init_plan(self, tmp_path):
        config = _make_config()
        config.project.directory = str(tmp_path)

        generate_team_init_plan(config, tmp_path)

        assert (tmp_path / "team-init-plan.md").exists()

    def test_plan_contains_initialization_sequence(self, tmp_path):
        config = _make_config()
        config.project.directory = str(tmp_path)

        generate_team_init_plan(config, tmp_path)

        content = (tmp_path / "team-init-plan.md").read_text()
        assert "Initialization Sequence" in content
        assert "Phase 1" in content
        assert "Phase 2" in content
        assert "team-leader.md" in content

    def test_plan_includes_atlassian_setup(self, tmp_path):
        config = _make_config(atlassian=AtlassianConfig(enabled=True, jira_project_key="PROJ"))
        config.project.directory = str(tmp_path)

        generate_team_init_plan(config, tmp_path)

        content = (tmp_path / "team-init-plan.md").read_text()
        assert "Atlassian Setup" in content
        assert "PROJ" in content

    def test_plan_references_requirements(self, tmp_path):
        config = _make_config()
        config.project.directory = str(tmp_path)

        generate_team_init_plan(config, tmp_path)

        content = (tmp_path / "team-init-plan.md").read_text()
        assert "Build a REST API with auth" in content


class TestVisualVerification:
    def test_frontend_agents_contain_visual_verification(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        for agent in ["frontend-engineer", "qa-engineer"]:
            content = (agents_dir / f"{agent}.md").read_text()
            assert "Visual Verification Protocol" in content, f"{agent} missing Visual Verification"

    def test_non_frontend_agents_no_visual_verification(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        for agent in ["backend-developer", "devops-specialist"]:
            content = (agents_dir / f"{agent}.md").read_text()
            assert "Visual Verification Protocol" not in content, f"{agent} should not have Visual Verification"

    def test_visual_verification_mode_scaled_mvp(self, tmp_path):
        config = _make_config()  # default is MVP
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "frontend-engineer.md").read_text()
        assert "MVP Visual Standards" in content
        assert "Production Ready Visual Standards" not in content

    def test_visual_verification_mode_scaled_production(self, tmp_path):
        config = _make_config(mode=ProjectMode.PRODUCTION_READY)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "frontend-engineer.md").read_text()
        assert "Production Ready Visual Standards" in content
        assert "visual regression baselines" in content.lower()

    def test_visual_verification_mode_scaled_no_compromise(self, tmp_path):
        config = _make_config(mode=ProjectMode.NO_COMPROMISE)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "frontend-engineer.md").read_text()
        assert "No Compromise Visual Standards" in content
        assert "Cross-browser testing" in content
        assert "Accessibility audit" in content

    def test_qa_agent_has_visual_regression_section(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "qa-engineer.md").read_text()
        assert "Visual Regression Testing (QA-Specific)" in content
        assert "BLOCKER" in content

    def test_screenshot_review_skill_generated(self, tmp_path):
        config = _make_config()
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        generate_skills(config, skills_dir)

        assert (skills_dir / "screenshot-review.md").exists()
        content = (skills_dir / "screenshot-review.md").read_text()
        assert "screenshot" in content.lower()
