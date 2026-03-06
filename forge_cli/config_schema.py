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
        # Use word boundaries for short keywords that could match inside other words
        frontend_patterns = [
            r"\bfrontend\b", r"\bfront-end\b", r"\bui\b", r"\buser interface\b",
            r"\bweb app\b", r"\bwebapp\b", r"\bdashboard\b", r"\blanding page\b",
            r"\bresponsive\b", r"\bmobile app\b", r"\bspa\b", r"\bsingle page\b",
        ]
        return any(re.search(p, text) for p in frontend_patterns)
