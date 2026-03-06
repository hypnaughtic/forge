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
