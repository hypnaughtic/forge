"""Tests for configuration schema and validation."""

from forge_cli.config_schema import (
    AgentsConfig,
    AtlassianConfig,
    ExecutionStrategy,
    ForgeConfig,
    GitConfig,
    ProjectConfig,
    ProjectMode,
    RefinementConfig,
    TeamProfile,
)


class TestForgeConfig:
    def test_default_config(self):
        config = ForgeConfig()
        assert config.mode == ProjectMode.MVP
        assert config.strategy == ExecutionStrategy.CO_PILOT
        assert config.agents.team_profile == TeamProfile.AUTO
        assert config.atlassian.enabled is True
        assert config.agents.allow_sub_agent_spawning is True

    def test_resolve_team_profile_auto_mvp(self):
        config = ForgeConfig(mode=ProjectMode.MVP)
        assert config.resolve_team_profile() == "lean"

    def test_resolve_team_profile_auto_production(self):
        config = ForgeConfig(mode=ProjectMode.PRODUCTION_READY)
        assert config.resolve_team_profile() == "full"

    def test_resolve_team_profile_auto_no_compromise(self):
        config = ForgeConfig(mode=ProjectMode.NO_COMPROMISE)
        assert config.resolve_team_profile() == "full"

    def test_resolve_team_profile_explicit(self):
        config = ForgeConfig(agents=AgentsConfig(team_profile=TeamProfile.LEAN))
        assert config.resolve_team_profile() == "lean"

    def test_get_active_agents_lean(self):
        config = ForgeConfig(
            mode=ProjectMode.MVP,
            agents=AgentsConfig(team_profile=TeamProfile.LEAN),
            atlassian=AtlassianConfig(enabled=False),
        )
        agents = config.get_active_agents()
        assert "team-leader" in agents
        assert "backend-developer" in agents
        assert "frontend-engineer" in agents
        assert "scrum-master" not in agents

    def test_get_active_agents_with_atlassian_adds_scrum_master(self):
        config = ForgeConfig(
            agents=AgentsConfig(team_profile=TeamProfile.LEAN),
            atlassian=AtlassianConfig(enabled=True),
        )
        agents = config.get_active_agents()
        assert "scrum-master" in agents
        # scrum-master should be right after team-leader
        tl_idx = agents.index("team-leader")
        sm_idx = agents.index("scrum-master")
        assert sm_idx == tl_idx + 1

    def test_get_active_agents_exclude(self):
        config = ForgeConfig(
            agents=AgentsConfig(
                team_profile=TeamProfile.LEAN,
                exclude=["critic"],
            ),
            atlassian=AtlassianConfig(enabled=False),
        )
        agents = config.get_active_agents()
        assert "critic" not in agents

    def test_get_active_agents_additional(self):
        config = ForgeConfig(
            agents=AgentsConfig(
                team_profile=TeamProfile.LEAN,
                additional=["security-tester"],
            ),
            atlassian=AtlassianConfig(enabled=False),
        )
        agents = config.get_active_agents()
        assert "security-tester" in agents

    def test_get_active_agents_custom(self):
        config = ForgeConfig(
            agents=AgentsConfig(
                team_profile=TeamProfile.CUSTOM,
                include=["team-leader", "backend-developer", "qa-engineer"],
            ),
            atlassian=AtlassianConfig(enabled=False),
        )
        agents = config.get_active_agents()
        assert agents == ["team-leader", "backend-developer", "qa-engineer"]

    def test_full_profile_has_more_agents(self):
        lean = ForgeConfig(
            agents=AgentsConfig(team_profile=TeamProfile.LEAN),
            atlassian=AtlassianConfig(enabled=False),
        )
        full = ForgeConfig(
            agents=AgentsConfig(team_profile=TeamProfile.FULL),
            atlassian=AtlassianConfig(enabled=False),
        )
        assert len(full.get_active_agents()) > len(lean.get_active_agents())

    def test_default_config_empty_non_negotiables(self):
        config = ForgeConfig()
        assert config.non_negotiables == []

    def test_config_with_non_negotiables(self):
        config = ForgeConfig(
            non_negotiables=["All APIs must be authenticated", "No raw SQL queries"],
        )
        assert len(config.non_negotiables) == 2
        assert "All APIs must be authenticated" in config.non_negotiables
        assert "No raw SQL queries" in config.non_negotiables

    def test_default_refinement_disabled(self):
        config = ForgeConfig()
        assert config.refinement.enabled is False
        assert config.refinement.provider == "local_claude"
        assert config.refinement.model == "claude-opus-4-6"
        assert config.refinement.score_threshold == 90
        assert config.refinement.max_iterations == 5

    def test_refinement_config_values(self):
        config = ForgeConfig(
            refinement=RefinementConfig(
                enabled=True,
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                score_threshold=85,
                max_iterations=3,
                timeout_seconds=120,
                cost_limit_usd=5.0,
            ),
        )
        assert config.refinement.enabled is True
        assert config.refinement.provider == "anthropic"
        assert config.refinement.model == "claude-sonnet-4-20250514"
        assert config.refinement.max_tokens == 4096
        assert config.refinement.score_threshold == 85
        assert config.refinement.max_iterations == 3
        assert config.refinement.timeout_seconds == 120
        assert config.refinement.cost_limit_usd == 5.0

    def test_default_git_config(self):
        config = ForgeConfig()
        assert config.git.ssh_key_path == ""

    def test_git_config_with_ssh_key(self):
        config = ForgeConfig(git=GitConfig(ssh_key_path="~/.ssh/id_ed25519"))
        assert config.git.ssh_key_path == "~/.ssh/id_ed25519"

    def test_has_ssh_auth_false_by_default(self):
        config = ForgeConfig()
        assert config.has_ssh_auth() is False

    def test_has_ssh_auth_true_with_key(self):
        config = ForgeConfig(git=GitConfig(ssh_key_path="~/.ssh/id_ed25519"))
        assert config.has_ssh_auth() is True
