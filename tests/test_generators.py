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
    GitConfig,
    ProjectConfig,
    ProjectMode,
    TeamProfile,
    TechStack,
)
from forge_cli.generators.agent_files import generate_agent_files
from forge_cli.generators.claude_md import generate_claude_md
from forge_cli.generators.mcp_config import generate_env_example, generate_mcp_config
from forge_cli.generators.settings_config import generate_settings_config
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

    def test_co_pilot_strategy_behavior_in_agent_files(self, tmp_path):
        config = _make_config(strategy=ExecutionStrategy.CO_PILOT)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Execution Strategy: Co-Pilot" in content
        assert "DO ask the human" in content
        assert "DO NOT ask the human" in content
        assert "full autonomy for all implementation work" in content.lower()

    def test_auto_pilot_strategy_behavior_in_agent_files(self, tmp_path):
        config = _make_config(strategy=ExecutionStrategy.AUTO_PILOT)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Execution Strategy: Auto-Pilot" in content
        assert "full autonomy" in content.lower()
        assert "never stop to ask permission" in content.lower()

    def test_micro_manage_strategy_behavior_in_agent_files(self, tmp_path):
        config = _make_config(strategy=ExecutionStrategy.MICRO_MANAGE)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Execution Strategy: Micro-Manage" in content
        assert "present every significant decision" in content.lower()

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

        generate_env_example(config, tmp_path)

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

    def test_team_leader_has_visual_when_frontend_project(self, tmp_path):
        """Team leader gets visual verification when project involves frontend."""
        config = _make_config()  # lean profile includes frontend-engineer
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "team-leader.md").read_text()
        assert "Visual Verification Protocol" in content
        assert "Iteration Visual Review (Team Leader-Specific)" in content

    def test_critic_has_visual_when_frontend_project(self, tmp_path):
        """Critic gets visual verification when project involves frontend."""
        config = _make_config()  # lean profile includes frontend-engineer
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "critic.md").read_text()
        assert "Visual Verification Protocol" in content
        assert "Visual Critique (Critic-Specific)" in content

    def test_team_leader_no_visual_when_no_frontend(self, tmp_path):
        """Team leader skips visual verification for backend-only projects."""
        config = _make_config(
            project=ProjectConfig(
                description="Backend microservice",
                requirements="Build a REST API with auth",
                directory="/tmp/test",
            ),
            agents=AgentsConfig(
                team_profile=TeamProfile.CUSTOM,
                include=["team-leader", "backend-developer", "devops-specialist", "critic"],
            ),
            tech_stack=TechStack(languages=["python"], frameworks=["fastapi"]),
        )
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "team-leader.md").read_text()
        assert "Visual Verification Protocol" not in content

    def test_critic_no_visual_when_no_frontend(self, tmp_path):
        """Critic skips visual verification for backend-only projects."""
        config = _make_config(
            project=ProjectConfig(
                description="Backend microservice",
                requirements="Build a REST API with auth",
                directory="/tmp/test",
            ),
            agents=AgentsConfig(
                team_profile=TeamProfile.CUSTOM,
                include=["team-leader", "backend-developer", "devops-specialist", "critic"],
            ),
            tech_stack=TechStack(languages=["python"], frameworks=["fastapi"]),
        )
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "critic.md").read_text()
        assert "Visual Verification Protocol" not in content

    def test_frontend_detection_via_tech_stack(self, tmp_path):
        """Visual verification activates for team-leader when tech stack has React."""
        config = _make_config(
            agents=AgentsConfig(
                team_profile=TeamProfile.CUSTOM,
                include=["team-leader", "backend-developer", "critic"],
            ),
            tech_stack=TechStack(languages=["python", "typescript"], frameworks=["react", "fastapi"]),
        )
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "team-leader.md").read_text()
        assert "Visual Verification Protocol" in content

    def test_frontend_detection_via_description(self, tmp_path):
        """Visual verification activates when project description mentions frontend."""
        config = _make_config(
            project=ProjectConfig(
                description="Full-stack web app with dashboard",
                requirements="Build a dashboard UI with analytics",
                directory="/tmp/test",
            ),
            agents=AgentsConfig(
                team_profile=TeamProfile.CUSTOM,
                include=["team-leader", "backend-developer", "critic"],
            ),
            tech_stack=TechStack(languages=["python"], frameworks=["fastapi"]),
        )
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "team-leader.md").read_text()
        assert "Visual Verification Protocol" in content


class TestWorkflowEnforcementSection:
    """Test _workflow_enforcement_section output."""

    def test_workflow_section_present_without_atlassian(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Workflow Enforcement Protocol" in content
        assert "Hierarchical PR Workflow" in content
        assert "No direct merges" in content
        assert "<type>/<agent-name>/" in content

    def test_workflow_section_with_atlassian(self, tmp_path):
        config = _make_config(atlassian=AtlassianConfig(enabled=True, jira_project_key="TEST"))
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Workflow Enforcement Protocol" in content
        assert "feat-TEST-42" in content
        assert "Jira ticket" in content

    def test_release_management_with_confluence(self, tmp_path):
        config = _make_config(atlassian=AtlassianConfig(enabled=True, jira_project_key="TEST"))
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Confluence release notes" in content

    def test_release_management_without_confluence(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Release Management" in content
        assert "Confluence release notes" not in content

    def test_pr_review_quality_standards(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "PR Review Quality Standards" in content
        assert "Big PRs" in content
        assert "Straightforward PRs" in content


class TestSubTeamCriticInSpawning:
    """Test leadership and mandatory critic in spawning section."""

    def test_leadership_in_spawning(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Leadership Responsibilities" in content
        assert "leader of your micro-team" in content

    def test_mandatory_critic_in_spawning(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Mandatory Sub-Team Critic" in content
        assert "critic.md" in content

    def test_no_leadership_when_spawning_disabled(self, tmp_path):
        config = _make_config(agents=AgentsConfig(team_profile=TeamProfile.LEAN, allow_sub_agent_spawning=False))
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Leadership Responsibilities" not in content
        assert "Mandatory Sub-Team Critic" not in content

    def test_critic_sub_team_role_section(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "critic.md").read_text()
        assert "Sub-Team Critic Role" in content
        assert "Your Leader" in content
        assert "Escalation" in content


class TestJiraBeforeWork:
    """Test Jira-before-work mandate in Atlassian section."""

    def test_jira_before_work_present(self, tmp_path):
        config = _make_config(atlassian=AtlassianConfig(enabled=True, jira_project_key="TEST"))
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "MANDATORY: Jira Task Before Work" in content
        assert "No code without a ticket" in content
        assert "Linking PRs" in content

    def test_no_jira_before_work_without_atlassian(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Jira Task Before Work" not in content


class TestNewSkills:
    """Test new PR workflow and release management skills."""

    def test_create_pr_skill_generated(self, tmp_path):
        config = _make_config()
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        generate_skills(config, skills_dir)

        assert (skills_dir / "create-pr.md").exists()
        content = (skills_dir / "create-pr.md").read_text()
        assert "create-pr" in content
        assert "Pull Request" in content

    def test_release_skill_generated(self, tmp_path):
        config = _make_config()
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        generate_skills(config, skills_dir)

        assert (skills_dir / "release.md").exists()
        content = (skills_dir / "release.md").read_text()
        assert "release" in content
        assert "GitHub release" in content

    def test_pr_skill_references_jira(self, tmp_path):
        config = _make_config(atlassian=AtlassianConfig(enabled=True, jira_project_key="PROJ"))
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        generate_skills(config, skills_dir)

        content = (skills_dir / "create-pr.md").read_text()
        assert "PROJ" in content

    def test_release_skill_confluence_conditional(self, tmp_path):
        config_on = _make_config(atlassian=AtlassianConfig(enabled=True, jira_project_key="PROJ"))
        skills_on = tmp_path / "on" / ".claude" / "skills"
        skills_on.mkdir(parents=True)
        generate_skills(config_on, skills_on)

        config_off = _make_config()
        skills_off = tmp_path / "off" / ".claude" / "skills"
        skills_off.mkdir(parents=True)
        generate_skills(config_off, skills_off)

        content_on = (skills_on / "release.md").read_text()
        content_off = (skills_off / "release.md").read_text()

        assert "Confluence" in content_on
        assert "Confluence" not in content_off


class TestNonNegotiables:
    """Tests for non-negotiables injection across all generated files."""

    NN_RULES = ["All APIs must be authenticated", "100% test coverage on core modules"]

    def _config_with_nn(self, **overrides):
        return _make_config(non_negotiables=self.NN_RULES, **overrides)

    def test_non_negotiables_in_team_leader(self, tmp_path):
        config = self._config_with_nn()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        generate_agent_files(config, agents_dir)

        content = (agents_dir / "team-leader.md").read_text()
        assert "Non-Negotiable Requirements (ENFORCEMENT)" in content
        assert "All APIs must be authenticated" in content
        assert "Reject any work that violates" in content

    def test_non_negotiables_in_critic(self, tmp_path):
        config = self._config_with_nn()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        generate_agent_files(config, agents_dir)

        content = (agents_dir / "critic.md").read_text()
        assert "Non-Negotiable Requirements (EVALUATION)" in content
        assert "PASS/FAIL" in content
        assert "automatic BLOCKER" in content

    def test_non_negotiables_in_other_agent(self, tmp_path):
        config = self._config_with_nn()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Non-Negotiable Requirements (COMPLIANCE)" in content
        assert "All APIs must be authenticated" in content
        assert "Verify compliance before reporting" in content

    def test_non_negotiables_absent_when_empty(self, tmp_path):
        config = _make_config()  # no non_negotiables
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        generate_agent_files(config, agents_dir)

        for agent_file in agents_dir.iterdir():
            content = agent_file.read_text()
            assert "Non-Negotiable Requirements" not in content

    def test_non_negotiables_in_claude_md(self, tmp_path):
        config = self._config_with_nn()
        config.project.directory = str(tmp_path)
        generate_claude_md(config, tmp_path)

        content = (tmp_path / "CLAUDE.md").read_text()
        assert "Non-Negotiable Requirements" in content
        assert "All APIs must be authenticated" in content
        assert "ABSOLUTE" in content

    def test_non_negotiables_absent_in_claude_md_when_empty(self, tmp_path):
        config = _make_config()
        config.project.directory = str(tmp_path)
        generate_claude_md(config, tmp_path)

        content = (tmp_path / "CLAUDE.md").read_text()
        assert "Non-Negotiable Requirements" not in content

    def test_non_negotiables_in_team_init_plan(self, tmp_path):
        config = self._config_with_nn()
        config.project.directory = str(tmp_path)
        generate_team_init_plan(config, tmp_path)

        content = (tmp_path / "team-init-plan.md").read_text()
        assert "Non-Negotiable Requirements" in content
        assert "All APIs must be authenticated" in content
        assert "BLOCKER" in content
        # Quick reference table row
        assert "2 rules" in content

    def test_non_negotiables_absent_in_team_init_plan_when_empty(self, tmp_path):
        config = _make_config()
        config.project.directory = str(tmp_path)
        generate_team_init_plan(config, tmp_path)

        content = (tmp_path / "team-init-plan.md").read_text()
        assert "Non-Negotiable Requirements" not in content
        assert "None" in content  # Quick reference row shows "None"


class TestSettingsConfigGeneration:
    """Tests for strategy-enforced .claude/settings.json generation."""

    def test_auto_pilot_generates_settings_with_all_tools(self, tmp_path):
        config = _make_config(strategy=ExecutionStrategy.AUTO_PILOT)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        generate_settings_config(config, claude_dir)

        settings_path = claude_dir / "settings.json"
        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        allow = data["permissions"]["allow"]
        expected = [
            "Bash(*)", "Read(*)", "Edit(*)", "Write(*)",
            "WebFetch(*)", "WebSearch(*)", "Agent(*)",
            "Glob(*)", "Grep(*)", "mcp__*",
        ]
        for tool in expected:
            assert tool in allow, f"Missing {tool} in auto-pilot allow list"

    def test_co_pilot_generates_settings_with_all_tools(self, tmp_path):
        """Co-pilot gets full tool access — same as auto-pilot.
        The difference is behavioral (instructions), not permission-based."""
        config = _make_config(strategy=ExecutionStrategy.CO_PILOT)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        generate_settings_config(config, claude_dir)

        settings_path = claude_dir / "settings.json"
        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        allow = data["permissions"]["allow"]
        expected = [
            "Bash(*)", "Read(*)", "Edit(*)", "Write(*)",
            "WebFetch(*)", "WebSearch(*)", "Agent(*)",
            "Glob(*)", "Grep(*)", "mcp__*",
        ]
        for tool in expected:
            assert tool in allow, f"Missing {tool} in co-pilot allow list"

    def test_micro_manage_does_not_generate_settings(self, tmp_path):
        config = _make_config(strategy=ExecutionStrategy.MICRO_MANAGE)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        generate_settings_config(config, claude_dir)

        assert not (claude_dir / "settings.json").exists()

    def test_merges_with_existing_settings(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.json"
        existing = {
            "permissions": {
                "allow": ["CustomTool(*)"],
                "deny": ["DangerousTool(*)"],
            }
        }
        settings_path.write_text(json.dumps(existing))

        config = _make_config(strategy=ExecutionStrategy.AUTO_PILOT)
        generate_settings_config(config, claude_dir)

        data = json.loads(settings_path.read_text())
        assert "CustomTool(*)" in data["permissions"]["allow"]
        assert "Bash(*)" in data["permissions"]["allow"]

    def test_deduplicates_allow_rules(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.json"
        existing = {
            "permissions": {
                "allow": ["Read(*)", "Bash(*)"],
                "deny": [],
            }
        }
        settings_path.write_text(json.dumps(existing))

        config = _make_config(strategy=ExecutionStrategy.AUTO_PILOT)
        generate_settings_config(config, claude_dir)

        data = json.loads(settings_path.read_text())
        allow = data["permissions"]["allow"]
        assert allow.count("Read(*)") == 1
        assert allow.count("Bash(*)") == 1

    def test_preserves_existing_deny_rules(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.json"
        existing = {
            "permissions": {
                "allow": [],
                "deny": ["DangerousTool(*)"],
            }
        }
        settings_path.write_text(json.dumps(existing))

        config = _make_config(strategy=ExecutionStrategy.CO_PILOT)
        generate_settings_config(config, claude_dir)

        data = json.loads(settings_path.read_text())
        assert "DangerousTool(*)" in data["permissions"]["deny"]

    def test_preserves_other_settings_keys(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.json"
        existing = {
            "customKey": "customValue",
            "permissions": {"allow": [], "deny": []},
        }
        settings_path.write_text(json.dumps(existing))

        config = _make_config(strategy=ExecutionStrategy.AUTO_PILOT)
        generate_settings_config(config, claude_dir)

        data = json.loads(settings_path.read_text())
        assert data["customKey"] == "customValue"

    def test_handles_malformed_existing_settings(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.json"
        settings_path.write_text("{ not valid json !!!")

        config = _make_config(strategy=ExecutionStrategy.AUTO_PILOT)
        generate_settings_config(config, claude_dir)

        data = json.loads(settings_path.read_text())
        assert "permissions" in data
        assert len(data["permissions"]["allow"]) == 10

    def test_auto_pilot_deny_list_empty(self, tmp_path):
        config = _make_config(strategy=ExecutionStrategy.AUTO_PILOT)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        generate_settings_config(config, claude_dir)

        data = json.loads((claude_dir / "settings.json").read_text())
        assert data["permissions"]["deny"] == []

    def test_co_pilot_includes_bash_edit_write(self, tmp_path):
        """Co-pilot has full tool access — behavioral difference only."""
        config = _make_config(strategy=ExecutionStrategy.CO_PILOT)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        generate_settings_config(config, claude_dir)

        data = json.loads((claude_dir / "settings.json").read_text())
        allow = data["permissions"]["allow"]
        assert "Bash(*)" in allow
        assert "Edit(*)" in allow
        assert "Write(*)" in allow

    def test_co_pilot_and_auto_pilot_same_permissions(self, tmp_path):
        """Co-pilot and auto-pilot produce identical settings.json permissions."""
        claude_ap = tmp_path / "ap" / ".claude"
        claude_ap.mkdir(parents=True)
        generate_settings_config(
            _make_config(strategy=ExecutionStrategy.AUTO_PILOT), claude_ap,
        )

        claude_cp = tmp_path / "cp" / ".claude"
        claude_cp.mkdir(parents=True)
        generate_settings_config(
            _make_config(strategy=ExecutionStrategy.CO_PILOT), claude_cp,
        )

        ap_data = json.loads((claude_ap / "settings.json").read_text())
        cp_data = json.loads((claude_cp / "settings.json").read_text())
        assert ap_data == cp_data


class TestGitAuthGeneration:
    """Tests for git SSH authentication feature across all generators."""

    def _ssh_config(self, **overrides):
        defaults = dict(git=GitConfig(ssh_key_path="~/.ssh/id_ed25519"))
        defaults.update(overrides)
        return _make_config(**defaults)

    # --- Agent files ---

    def test_git_auth_in_agent_files_when_ssh_configured(self, tmp_path):
        config = self._ssh_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Git Authentication (SSH)" in content

    def test_git_auth_absent_when_no_ssh(self, tmp_path):
        config = _make_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "Git Authentication (SSH)" not in content

    def test_git_auth_contains_ssh_key_path(self, tmp_path):
        config = self._ssh_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "~/.ssh/id_ed25519" in content

    def test_git_auth_mentions_gh_token(self, tmp_path):
        config = self._ssh_config()
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        generate_agent_files(config, agents_dir)

        content = (agents_dir / "backend-developer.md").read_text()
        assert "GH_TOKEN" in content

    # --- CLAUDE.md ---

    def test_git_auth_in_claude_md_when_configured(self, tmp_path):
        config = self._ssh_config()
        generate_claude_md(config, tmp_path)

        content = (tmp_path / "CLAUDE.md").read_text()
        assert "## Git Authentication" in content
        assert "~/.ssh/id_ed25519" in content

    def test_git_auth_absent_in_claude_md_when_default(self, tmp_path):
        config = _make_config()
        generate_claude_md(config, tmp_path)

        content = (tmp_path / "CLAUDE.md").read_text()
        assert "## Git Authentication" not in content

    # --- team-init-plan.md ---

    def test_git_auth_phase_0_in_team_init_plan(self, tmp_path):
        config = self._ssh_config()
        generate_team_init_plan(config, tmp_path)

        content = (tmp_path / "team-init-plan.md").read_text()
        assert "Phase 0: Git Authentication Setup" in content
        assert "~/.ssh/id_ed25519" in content
        assert "core.sshCommand" in content

    def test_git_auth_phase_0_absent_when_default(self, tmp_path):
        config = _make_config()
        generate_team_init_plan(config, tmp_path)

        content = (tmp_path / "team-init-plan.md").read_text()
        assert "Phase 0" not in content

    def test_git_auth_in_quick_reference_table(self, tmp_path):
        config = self._ssh_config()
        generate_team_init_plan(config, tmp_path)

        content = (tmp_path / "team-init-plan.md").read_text()
        assert "SSH (~/.ssh/id_ed25519)" in content

    # --- Skills ---

    def test_pr_skill_mentions_gh_token_when_ssh(self, tmp_path):
        config = self._ssh_config()
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        generate_skills(config, skills_dir)

        content = (skills_dir / "create-pr.md").read_text()
        assert "GH_TOKEN" in content

    def test_release_skill_mentions_gh_token_when_ssh(self, tmp_path):
        config = self._ssh_config()
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        generate_skills(config, skills_dir)

        content = (skills_dir / "release.md").read_text()
        assert "GH_TOKEN" in content

    # --- .env.example ---

    def test_env_example_with_gh_token(self, tmp_path):
        config = self._ssh_config()
        generate_env_example(config, tmp_path)

        content = (tmp_path / ".env.example").read_text()
        assert "GH_TOKEN" in content

    def test_env_example_with_atlassian_only(self, tmp_path):
        config = _make_config(atlassian=AtlassianConfig(enabled=True))
        generate_env_example(config, tmp_path)

        content = (tmp_path / ".env.example").read_text()
        assert "ATLASSIAN_URL" in content
        assert "GH_TOKEN" not in content

    def test_env_example_with_both(self, tmp_path):
        config = _make_config(
            atlassian=AtlassianConfig(enabled=True),
            git=GitConfig(ssh_key_path="~/.ssh/id_ed25519"),
        )
        generate_env_example(config, tmp_path)

        content = (tmp_path / ".env.example").read_text()
        assert "GH_TOKEN" in content
        assert "ATLASSIAN_URL" in content

    def test_env_example_not_generated_when_nothing_needed(self, tmp_path):
        config = _make_config()
        generate_env_example(config, tmp_path)

        assert not (tmp_path / ".env.example").exists()

    def test_env_example_idempotent(self, tmp_path):
        config = self._ssh_config()
        generate_env_example(config, tmp_path)
        generate_env_example(config, tmp_path)

        content = (tmp_path / ".env.example").read_text()
        assert content.count("GH_TOKEN") == 1
