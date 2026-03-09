"""Generate CLAUDE.md for the project workspace."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from forge_cli.config_schema import ForgeConfig


def _plan_file_claude_md(config: ForgeConfig) -> str:
    """Generate plan file reference for CLAUDE.md."""
    if not config.project.plan_file:
        return ""

    return dedent(f"""\

    ## Implementation Blueprint

    Follow **`{config.project.plan_file}`** as the authoritative implementation plan.
    The agent team executes this plan — it defines WHAT to build and in what order.
    Forge agent instruction files define HOW the team operates (roles, workflows, quality gates).
    Do NOT deviate from the plan unless the user explicitly instructs otherwise.
    """)


def generate_claude_md(config: ForgeConfig, project_dir: Path) -> None:
    """Generate CLAUDE.md in the project root."""
    agents = config.get_active_agents()
    non_leader_agents = [a for a in agents if a != "team-leader"]

    tech_parts = []
    if config.tech_stack.languages:
        tech_parts.append(", ".join(config.tech_stack.languages))
    if config.tech_stack.frameworks:
        tech_parts.append(", ".join(config.tech_stack.frameworks))
    tech_str = " | ".join(tech_parts) if tech_parts else "(auto-detect)"

    agent_roster = "\n".join(
        f"- **{a}**: `.claude/agents/{a}.md`" for a in non_leader_agents
    )

    atlassian_section = ""
    if config.atlassian.enabled:
        atlassian_section = dedent(f"""\

        ## Atlassian Integration

        Jira and Confluence are configured via `.claude/mcp.json`. All agents have access.
        - **Jira**: {config.atlassian.jira_base_url or '[see mcp.json]'} — Project: {config.atlassian.jira_project_key or '[see mcp.json]'}
        - **Confluence**: {config.atlassian.confluence_base_url or '[see mcp.json]'} — Space: {config.atlassian.confluence_space_key or '[see mcp.json]'}

        The Scrum Master agent manages the Jira board, sprint planning, and Confluence documentation.
        All agents must update ticket status and add comments as they work.
        Documentation is a side effect of development — make reasoning visible in Confluence.
        """)

    spawning_section = ""
    if config.agents.allow_sub_agent_spawning:
        spawning_section = dedent("""\

        ## Sub-Agent Spawning

        Agents are authorized to spawn sub-agents for parallel task execution.
        - All sub-agents MUST use instruction files from `.claude/agents/`
        - Sub-agents report to their spawning agent, not directly to Team Leader
        - Cross-specialty spawning is allowed (e.g., backend agent spawns frontend sub-agent to check impacts)
        - Maximum spawning depth: 2-3 levels
        """)

    sub_team_critic_line = ""
    if config.agents.allow_sub_agent_spawning:
        sub_team_critic_line = "\n    - **Sub-Team Critics**: Every agent that spawns sub-agents must also spawn a Critic for its micro-team"

    workflow_section = ""
    if config.atlassian.enabled:
        project_key = config.atlassian.jira_project_key or "PROJ"
        workflow_section = dedent(f"""\

        ## Workflow Enforcement

        - **Jira-First**: No agent starts coding without a Jira ticket. Zero tolerance for dark work.
        - **Branch Naming**: `<type>-<{project_key}-N>-<description>` — every branch maps to a Jira ticket
        - **PR-Before-Merge**: All code changes go through Pull Requests with at least one approval{sub_team_critic_line}
        - **Traceability**: Jira ticket -> branch -> PR -> merged code. Every PR references its ticket.
        - **Release Management**: Major releases get a GitHub release tag and Confluence release notes update
        """)
    else:
        workflow_section = dedent(f"""\

        ## Workflow Enforcement

        - **PR-Before-Merge**: All code changes go through Pull Requests with at least one approval
        - **Hierarchical Branching**: Sub-task branches PR into parent feature branches, feature branches PR into default{sub_team_critic_line}
        - **Release Management**: Major releases get a GitHub release tag with generated release notes
        """)

    naming_section = ""
    if config.agent_naming.enabled:
        naming_section = dedent(f"""\

        ## Agent Naming

        Each agent assigns itself a unique name upon initialization ({config.agent_naming.style} style).
        Agent names are used in: git commits, branch names, Jira updates, Confluence edits, and all communications.
        This enables traceability — humans can see exactly which agent did what.
        """)

    llm_gateway_section = ""
    if config.llm_gateway.enabled:
        local_note = ""
        if config.llm_gateway.enable_local_claude:
            local_note = f"\n    - **Local Claude**: enabled (model: {config.llm_gateway.local_claude_model}) — free local inference for dev/test"
        llm_gateway_section = dedent(f"""\

        ## LLM Gateway

        All LLM calls in this project MUST use [llm-gateway](https://github.com/Rushabh1798/llm-gateway).
        Direct vendor SDK imports (anthropic, openai) are forbidden.
        - **Provider switching**: `LLM_PROVIDER` env var (anthropic, local_claude, fake)
        - **Structured output**: Pydantic response models for every call
        - **Cost tracking**: {'enabled' if config.llm_gateway.cost_tracking else 'disabled'} — per-call and cumulative USD tracking{local_note}
        - **Testing**: use `FakeLLMProvider` for deterministic unit tests
        """)

    git_auth_section = ""
    if config.has_ssh_auth():
        git_auth_section = dedent(f"""\

        ## Git Authentication

        SSH key: `{config.git.ssh_key_path}` (configured in `.git/config` via `core.sshCommand`)
        - Git push/fetch/clone use SSH — no Keychain prompts
        - GitHub CLI (`gh`) uses `GH_TOKEN` env var
        - If remotes show HTTPS URLs, convert: `git remote set-url origin git@github.com:OWNER/REPO.git`
        """)

    non_negotiables_section = ""
    if config.non_negotiables:
        rules = "\n    ".join(f"- {rule}" for rule in config.non_negotiables)
        non_negotiables_section = dedent(f"""\

        ## Non-Negotiable Requirements

        These requirements are ABSOLUTE. Every agent, every deliverable must comply.
        No exceptions. No trade-offs. Any violation is an automatic blocker.

        {rules}
        """)

    content = dedent(f"""\
    # Forge — Team Leader Context

    > Auto-generated by Forge. Regenerate with: `forge generate`

    ## Project Configuration

    - **Project**: {config.project.description}
    - **Mode**: {config.mode.value} | **Strategy**: {config.strategy.value}
    - **Cost Cap**: ${config.cost.max_development_cost}
    - **Team Profile**: {config.resolve_team_profile()} ({', '.join(agents)})
    - **Tech Stack**: {tech_str}
    {non_negotiables_section}
    ## Your Identity

    You are the **Team Leader** of a Forge agent team. You ARE this interactive
    Claude Code session. The user talks directly to you.

    When the user asks a question, answer directly. When they give a directive, act on it.

    **CRITICAL: Command Priority**
    User commands take ABSOLUTE priority. When the user types anything, respond
    immediately. Agent work continues in the background.

    ## Getting Started

    Read `team-init-plan.md` for the complete initialization blueprint. It contains:
    1. The startup sequence
    2. Iteration 1 task decomposition
    3. Agent spawning instructions
    4. Quality gates and success criteria
    {_plan_file_claude_md(config)}
    ## Agent Roster

    Available agents (spawn via Agent tool with instruction files as context):
    {agent_roster}

    ## Spawning an Agent

    To spawn an agent, use the **Agent tool** with:
    - The agent's instruction file from `.claude/agents/{{agent-type}}.md` as system context
    - A clear task description
    - Any relevant context (API contracts, design specs, etc.)

    Example: To spawn the backend developer, use the Agent tool and include the
    contents of `.claude/agents/backend-developer.md` in the system prompt.
    {atlassian_section}{spawning_section}{workflow_section}{naming_section}{llm_gateway_section}{git_auth_section}
    {"## Visual Verification" + chr(10) + chr(10) + "    Playwright MCP is configured in `.claude/mcp.json` for browser automation and screenshots." + chr(10) + "    - Frontend agents and QA must **visually verify** their work via screenshots before marking tasks complete" + chr(10) + "    - Use Playwright CLI or MCP to capture screenshots, then use the Read tool to view them" + chr(10) + "    - Screenshots are saved to `docs/screenshots/` for human review" + chr(10) + "    - Smoke tests must include screenshot evidence of a working UI" if config.has_frontend_involvement() else "## Verification" + chr(10) + chr(10) + ("    - **CLI output verification**: Capture and review command outputs for all subcommands" + chr(10) + "    - Verify help text is complete and accurate, error messages are helpful" + chr(10) + "    - Playwright MCP is configured for API documentation screenshots if applicable" if config.is_cli_project() else "    - **API documentation verification**: Verify OpenAPI/Swagger docs are generated and accurate" + chr(10) + "    - Playwright MCP is configured in `.claude/mcp.json` — use for API docs screenshots" + chr(10) + "    - Smoke tests must verify all endpoints respond correctly with proper status codes")}

    ## Project Requirements

    {config.project.requirements or config.project.description}

    ## Team Leader Instructions

    Your full instruction set is in `.claude/agents/team-leader.md`. Key responsibilities:
    - 7-phase iteration lifecycle (PLAN → EXECUTE → TEST → INTEGRATE → REVIEW → CRITIQUE → DECISION)
    - Quality gates: {'70%' if config.mode.value == 'mvp' else '90%' if config.mode.value == 'production-ready' else '100%'}
    - Smoke test protocol (mandatory for ALL modes)
    - Progressive work advancement (don't wait for all agents to finish)
    - Parallel work streams with sync points
    """)

    output_path = project_dir / "CLAUDE.md"
    output_path.write_text(content)
