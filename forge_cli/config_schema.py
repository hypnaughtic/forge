"""YAML configuration schema for forge project initialization."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProjectMode(str, Enum):
    MVP = "mvp"
    PRODUCTION_READY = "production-ready"
    NO_COMPROMISE = "no-compromise"


class ExecutionStrategy(str, Enum):
    AUTO_PILOT = "auto-pilot"
    CO_PILOT = "co-pilot"
    MICRO_MANAGE = "micro-manage"


class TeamProfile(str, Enum):
    AUTO = "auto"
    LEAN = "lean"
    FULL = "full"
    CUSTOM = "custom"


class ProjectConfig(BaseModel):
    description: str = ""
    requirements: str = ""
    context_files: list[str] = Field(default_factory=list)
    plan_file: str = ""  # Authoritative implementation blueprint (followed exactly)
    type: str = "new"  # new | existing
    existing_project_path: str = ""
    directory: str = "."


class CostConfig(BaseModel):
    max_development_cost: str | int = 50


class AgentsConfig(BaseModel):
    team_profile: TeamProfile = TeamProfile.AUTO
    exclude: list[str] = Field(default_factory=list)
    additional: list[str] = Field(default_factory=list)
    include: list[str] = Field(default_factory=list)
    allow_sub_agent_spawning: bool = True
    custom_instructions: dict[str, str] = Field(default_factory=dict)


class TechStack(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    infrastructure: list[str] = Field(default_factory=list)


class AtlassianConfig(BaseModel):
    enabled: bool = True
    jira_project_key: str = ""
    jira_base_url: str = ""
    confluence_space_key: str = ""
    confluence_base_url: str = ""
    create_sprint_board: bool = True
    create_confluence_space: bool = True
    scrum_ceremonies: bool = True


class AgentNamingConfig(BaseModel):
    enabled: bool = True
    style: str = "creative"  # creative | functional | codename


class LLMGatewayConfig(BaseModel):
    """Configuration for llm-gateway integration in generated projects."""

    enabled: bool = True
    local_claude_model: str = "claude-sonnet-4-20250514"
    enable_local_claude: bool = True
    cost_tracking: bool = True


class GitConfig(BaseModel):
    """Git authentication configuration for generated projects."""

    ssh_key_path: str = ""  # e.g. ~/.ssh/id_ed25519


class RefinementConfig(BaseModel):
    """Configuration for LLM-powered post-generation refinement."""

    enabled: bool = False
    provider: str = "local_claude"
    model: str = "claude-opus-4-6"
    max_tokens: int = 8192
    score_threshold: int = 90
    max_iterations: int = 5
    max_concurrency: int = 0  # 0 = unlimited (all files in parallel)
    timeout_seconds: int = 300
    cost_limit_usd: float = 10.0


class ForgeConfig(BaseModel):
    """Root configuration for a forge-initialized project."""

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    mode: ProjectMode = ProjectMode.MVP
    strategy: ExecutionStrategy = ExecutionStrategy.CO_PILOT
    cost: CostConfig = Field(default_factory=CostConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    tech_stack: TechStack = Field(default_factory=TechStack)
    atlassian: AtlassianConfig = Field(default_factory=AtlassianConfig)
    agent_naming: AgentNamingConfig = Field(default_factory=AgentNamingConfig)
    llm_gateway: LLMGatewayConfig = Field(default_factory=LLMGatewayConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    refinement: RefinementConfig = Field(default_factory=RefinementConfig)
    non_negotiables: list[str] = Field(default_factory=list)

    def has_ssh_auth(self) -> bool:
        """Check if SSH-based git authentication is configured."""
        return bool(self.git.ssh_key_path)

    def resolve_team_profile(self) -> str:
        """Resolve 'auto' team profile based on mode."""
        if self.agents.team_profile == TeamProfile.AUTO:
            if self.mode == ProjectMode.MVP:
                return "lean"
            return "full"
        return self.agents.team_profile.value

    def get_active_agents(self) -> list[str]:
        """Get the list of active agent types based on config."""
        profile = self.resolve_team_profile()

        lean_agents = [
            "team-leader",
            "research-strategist",
            "architect",
            "backend-developer",
            "frontend-engineer",
            "qa-engineer",
            "devops-specialist",
            "critic",
        ]
        full_agents = [
            "team-leader",
            "research-strategist",
            "architect",
            "backend-developer",
            "frontend-designer",
            "frontend-developer",
            "qa-engineer",
            "devops-specialist",
            "security-tester",
            "performance-engineer",
            "documentation-specialist",
            "critic",
        ]

        if profile == "lean":
            agents = lean_agents.copy()
        elif profile == "full":
            agents = full_agents.copy()
        elif profile == "custom":
            agents = self.agents.include.copy() if self.agents.include else lean_agents.copy()
        else:
            agents = lean_agents.copy()

        # Always add scrum-master if atlassian is enabled
        if self.atlassian.enabled and "scrum-master" not in agents:
            # Insert after team-leader
            idx = agents.index("team-leader") + 1 if "team-leader" in agents else 0
            agents.insert(idx, "scrum-master")

        # Apply excludes
        for agent in self.agents.exclude:
            if agent in agents:
                agents.remove(agent)

        # Apply additionals
        for agent in self.agents.additional:
            if agent not in agents:
                agents.append(agent)

        return agents

    def has_frontend_involvement(self) -> bool:
        """Detect if the project involves frontend/UI work.

        Checks tech stack frameworks, active agents, and project description
        for frontend indicators.
        """
        frontend_frameworks = {
            "react", "vue", "angular", "svelte", "next", "nextjs", "next.js",
            "nuxt", "nuxtjs", "nuxt.js", "gatsby", "remix", "astro",
            "tailwind", "tailwindcss", "bootstrap", "css", "sass", "scss",
            "html", "htmx", "alpine", "alpinejs", "solid", "solidjs",
            "qwik", "flutter", "swift", "swiftui", "jetpack compose",
            "react native", "electron", "tauri", "expo",
        }
        frontend_agents = {
            "frontend-engineer", "frontend-developer", "frontend-designer",
        }

        # Check frameworks
        for fw in self.tech_stack.frameworks:
            if fw.lower().strip() in frontend_frameworks:
                return True

        # Check languages for frontend indicators
        frontend_languages = {"javascript", "typescript", "html", "css", "dart", "swift"}
        for lang in self.tech_stack.languages:
            if lang.lower().strip() in frontend_languages:
                return True

        # Check if any frontend agent is in the active roster
        active = self.get_active_agents()
        if frontend_agents & set(active):
            return True

        # Check project description/requirements for frontend keywords
        import re
        text = f"{self.project.description} {self.project.requirements}".lower()

        # First check for explicit negation patterns — "no frontend", "no ui", etc.
        negation_patterns = [
            r"\bno\s+frontend\b", r"\bno\s+front-end\b", r"\bno\s+ui\b",
            r"\bwithout\s+frontend\b", r"\bno\s+web\s+ui\b",
        ]
        if any(re.search(p, text) for p in negation_patterns):
            return False

        # Use word boundaries for short keywords that could match inside other words
        frontend_patterns = [
            r"\bfrontend\b", r"\bfront-end\b", r"\bui\b", r"\buser interface\b",
            r"\bweb app\b", r"\bwebapp\b", r"\bdashboard\b", r"\blanding page\b",
            r"\bresponsive\b", r"\bmobile app\b", r"\bspa\b", r"\bsingle page\b",
        ]
        return any(re.search(p, text) for p in frontend_patterns)

    def has_web_backend(self) -> bool:
        """Detect if the project has a web backend (API server, web framework).

        Returns True for projects that run an HTTP server (FastAPI, Django,
        Express, etc.).  Returns False for CLI tools, static sites, and
        library projects.
        """
        web_frameworks = {
            "fastapi", "django", "flask", "express", "nestjs", "koa",
            "hapi", "gin", "echo", "fiber", "spring", "spring boot",
            "rails", "laravel", "phoenix", "actix", "axum", "rocket",
            "drf", "django rest framework", "aspnet", "asp.net",
        }
        for fw in self.tech_stack.frameworks:
            if fw.lower().strip() in web_frameworks:
                return True

        import re
        text = f"{self.project.description} {self.project.requirements}".lower()
        backend_patterns = [
            r"\bapi\b", r"\brest\b", r"\brestful\b", r"\bendpoint",
            r"\bserver\b", r"\bmicroservice", r"\bbackend\b",
            r"\bhttp server\b", r"\bweb server\b",
        ]
        # Exclude patterns that would false-positive for CLI/static projects
        cli_negatives = [r"\bcli\b", r"\bcommand.line\b", r"\bstatic site\b"]
        has_backend_keywords = any(re.search(p, text) for p in backend_patterns)
        has_cli_keywords = any(re.search(p, text) for p in cli_negatives)
        # If description says both "API" and "CLI", trust the explicit web framework
        if has_backend_keywords and not has_cli_keywords:
            return True
        return False

    def is_cli_project(self) -> bool:
        """Detect if the project is a CLI tool (no web server, no frontend).

        Returns True for command-line tools, data pipelines, and similar
        projects that run in a terminal rather than serving web requests.
        """
        cli_frameworks = {
            "click", "typer", "argparse", "commander", "yargs",
            "clap", "cobra", "oclif", "inquirer",
        }
        for fw in self.tech_stack.frameworks:
            if fw.lower().strip() in cli_frameworks:
                return True

        import re
        text = f"{self.project.description} {self.project.requirements}".lower()
        cli_patterns = [
            r"\bcli\b", r"\bcommand.line\b", r"\bterminal\b",
            r"\bpipeline tool\b", r"\bdata pipeline\b",
        ]
        if any(re.search(p, text) for p in cli_patterns):
            return not self.has_frontend_involvement() and not self.has_web_backend()
        return False
