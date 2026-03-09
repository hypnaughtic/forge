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


class TestProjectTypeDetection:
    """Tests for has_frontend_involvement, has_web_backend, is_cli_project."""

    def _make_config(self, agents_include=None, **kwargs):
        from forge_cli.config_schema import ProjectConfig, TechStack
        project_kw = {}
        tech_kw = {}
        for k, v in kwargs.items():
            if k in ("description", "requirements"):
                project_kw[k] = v
            elif k in ("languages", "frameworks", "databases", "infrastructure"):
                tech_kw[k] = v
        agents_cfg = AgentsConfig(
            team_profile=TeamProfile.CUSTOM,
            include=agents_include or ["team-leader", "backend-developer"],
        )
        return ForgeConfig(
            project=ProjectConfig(**project_kw) if project_kw else ProjectConfig(),
            tech_stack=TechStack(**tech_kw) if tech_kw else TechStack(),
            agents=agents_cfg,
        )

    # --- has_web_backend ---
    def test_has_web_backend_fastapi(self):
        config = self._make_config(frameworks=["FastAPI"])
        assert config.has_web_backend() is True

    def test_has_web_backend_django(self):
        config = self._make_config(frameworks=["Django"])
        assert config.has_web_backend() is True

    def test_has_web_backend_from_description(self):
        config = self._make_config(description="REST API for orders")
        assert config.has_web_backend() is True

    def test_has_web_backend_false_for_cli(self):
        config = self._make_config(
            frameworks=["Click"],
            description="CLI data pipeline tool, no frontend",
        )
        assert config.has_web_backend() is False

    def test_has_web_backend_false_for_static_site(self):
        config = self._make_config(
            frameworks=["Astro", "React"],
            description="Static portfolio website",
        )
        assert config.has_web_backend() is False

    # --- is_cli_project ---
    def test_is_cli_project_click(self):
        config = self._make_config(
            frameworks=["Click"],
            description="CLI data pipeline tool, no frontend",
        )
        assert config.is_cli_project() is True

    def test_is_cli_project_typer(self):
        config = self._make_config(frameworks=["Typer"])
        assert config.is_cli_project() is True

    def test_is_cli_project_from_description(self):
        config = self._make_config(description="command-line utility")
        assert config.is_cli_project() is True

    def test_is_cli_project_false_for_web_app(self):
        config = self._make_config(
            frameworks=["FastAPI", "React"],
            description="Full-stack web application",
        )
        assert config.is_cli_project() is False

    def test_is_cli_project_false_for_static_site(self):
        config = self._make_config(
            frameworks=["Astro"],
            description="Portfolio website",
        )
        assert config.is_cli_project() is False

    # --- has_frontend_involvement negation ---
    def test_has_frontend_negation_no_frontend(self):
        config = self._make_config(
            description="CLI tool, no frontend",
        )
        assert config.has_frontend_involvement() is False

    def test_has_frontend_negation_without_frontend(self):
        config = self._make_config(
            requirements="Build API without frontend",
        )
        assert config.has_frontend_involvement() is False

    def test_has_frontend_true_for_react(self):
        config = self._make_config(frameworks=["React"])
        assert config.has_frontend_involvement() is True

    def test_has_frontend_true_for_dashboard_desc(self):
        config = self._make_config(description="Admin dashboard")
        assert config.has_frontend_involvement() is True
