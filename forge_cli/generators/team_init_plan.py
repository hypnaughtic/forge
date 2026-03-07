"""Generate team-init-plan.md — the bootstrap document for the first Claude session."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from forge_cli.config_schema import ForgeConfig


def _non_negotiables_init_section(config: ForgeConfig) -> str:
    """Generate non-negotiables section for team-init-plan.md."""
    if not config.non_negotiables:
        return ""

    rules = "\n    ".join(f"- {rule}" for rule in config.non_negotiables)
    return dedent(f"""\

    ## Non-Negotiable Requirements

    Communicate these to every agent during spawning. The Critic evaluates every
    deliverable against these. Any violation is an automatic BLOCKER.

    {rules}
    """)


def generate_team_init_plan(config: ForgeConfig, project_dir: Path) -> None:
    """Generate team-init-plan.md in the project root."""
    agents = config.get_active_agents()
    non_leader_agents = [a for a in agents if a != "team-leader"]

    agent_spawn_list = "\n".join(
        f"   - `{a}` — Read `.claude/agents/{a}.md`, spawn with Agent tool"
        for a in non_leader_agents
    )

    mode_desc = {
        "mvp": "MVP — Working prototype, speed over polish, 70% quality threshold",
        "production-ready": "Production Ready — Robust, maintainable, 90% quality threshold",
        "no-compromise": "No Compromise — Launch-ready, maximum quality, 100% threshold",
    }.get(config.mode.value, config.mode.value)

    strategy_desc = {
        "auto-pilot": "Auto-Pilot — Make all decisions autonomously, respect cost caps",
        "co-pilot": "Co-Pilot — Technical decisions autonomous, design decisions need human approval",
        "micro-manage": "Micro-Manage — Present every significant decision to human",
    }.get(config.strategy.value, config.strategy.value)

    atlassian_init = ""
    if config.atlassian.enabled:
        atlassian_init = dedent(f"""\

        ### Phase 2b: Atlassian Setup (Scrum Master)

        Once the Scrum Master agent is spawned:
        1. Create or verify the Jira project ({config.atlassian.jira_project_key or '[project key]'})
        2. Set up the sprint board with columns: To Do → In Progress → In Review → Testing → Done
        3. Create the first sprint
        4. Create Confluence space ({config.atlassian.confluence_space_key or '[space key]'}) with pages:
           - **Project Dashboard**: Overview, team roster, current sprint status
           - **Architecture**: System design, API contracts, ADRs
           - **Sprint Log**: Running log of sprint planning, standups, retros
           - **Meeting Notes**: For ceremony records
        5. Create Jira tickets for all Iteration 1 tasks
        6. The board should be immediately viewable by humans

        **Environment Setup**: Ensure the Atlassian MCP server is running.
        Required env vars (see `.env.example`):
        - `ATLASSIAN_URL`
        - `ATLASSIAN_USERNAME`
        - `ATLASSIAN_API_TOKEN`
        """)

    naming_init = ""
    if config.agent_naming.enabled:
        naming_init = dedent(f"""\

        ### Agent Naming

        Each agent must assign itself a unique name upon initialization ({config.agent_naming.style} style).
        - Names are used in git commits, Jira, Confluence, and all communications
        - Team Leader collects all agent names and maintains a roster
        - Name collisions must be resolved immediately
        - Sub-agents should derive names from their parent (e.g., parent 'Nova' → sub-agent 'Nova-Spark')
        """)

    spawning_init = ""
    if config.agents.allow_sub_agent_spawning:
        spawning_init = dedent("""\

        ### Sub-Agent Spawning

        Agents are authorized to spawn sub-agents for parallel execution:
        - Sub-agents MUST use instruction files from `.claude/agents/`
        - Sub-agents report to their spawning parent, not directly to Team Leader
        - Cross-specialty spawning is allowed (e.g., backend spawns frontend to check impacts)
        - Max spawning depth: 2-3 levels
        - Each sub-agent follows the full protocol from its instruction file
        """)

    sub_team_critic_rule = ""
    if config.agents.allow_sub_agent_spawning:
        sub_team_critic_rule = "\n    4. **Sub-Team Critics**: Every agent that spawns sub-agents must also spawn a Critic for its micro-team"

    workflow_init = ""
    if config.atlassian.enabled:
        project_key = config.atlassian.jira_project_key or "PROJ"
        next_num = 5 if config.agents.allow_sub_agent_spawning else 4
        workflow_init = dedent(f"""\

        ### Workflow Rules

        These rules are enforced from the first commit:

        1. **Jira-First**: No agent starts coding without a Jira ticket. Create tickets before work begins.
        2. **Branch Naming**: `<type>-<{project_key}-N>-<description>` — every branch maps to a Jira ticket
        3. **PR Workflow**: All code changes go through Pull Requests. At least one approval required.{sub_team_critic_rule}
        {next_num}. **PR Review Quality**: Big PRs (new features, cross-cutting changes) require actual testing by the reviewer
        {next_num + 1}. **Release Management**: After major milestones, create a GitHub release with tag and update Confluence release notes
        """)
    else:
        next_num = 3 if config.agents.allow_sub_agent_spawning else 2
        workflow_init = dedent(f"""\

        ### Workflow Rules

        These rules are enforced from the first commit:

        1. **PR Workflow**: All code changes go through Pull Requests. At least one approval required.{sub_team_critic_rule}
        {next_num}. **PR Review Quality**: Big PRs (new features, cross-cutting changes) require actual testing by the reviewer
        {next_num + 1}. **Hierarchical Branches**: Sub-task branches PR into parent feature branches, feature branches into default
        """)

    workspace_note = ""
    if config.project.type == "new":
        workspace_note = dedent("""\

        ### Workspace Setup

        This is a **new project**. The workspace directory may be empty or only contain forge-generated files.
        - Check if `.git/` exists — if not, you may create one or multiple repositories as needed
        - If the architecture calls for microservices, consider a polyrepo or monorepo structure
        - Create README.md, .gitignore, and project configuration files as part of Iteration 1
        """)
    else:
        workspace_note = dedent("""\

        ### Workspace Setup

        This is an **existing project**. Respect existing conventions:
        - Read existing README, CONTRIBUTING, and configuration files
        - Follow existing code patterns and project structure
        - Do not restructure existing code unless explicitly required
        - Treat the existing `.git/` repository as the single source of truth
        """)

    content = dedent(f"""\
    # Team Initialization Plan

    > Generated by Forge. This is the bootstrap document for the first Claude Code session.
    > Read this file completely before taking any action.

    ## Overview

    **Project**: {config.project.description}
    **Mode**: {mode_desc}
    **Strategy**: {strategy_desc}
    **Cost Cap**: ${config.cost.max_development_cost}
    **Team Size**: {len(agents)} agents

    ## Project Requirements

    {config.project.requirements or config.project.description}
    {_non_negotiables_init_section(config)}
    ## Initialization Sequence

    ### Phase 1: Read and Internalize

    1. Read this file completely (you're doing that now)
    2. Read `CLAUDE.md` for your Team Leader context and configuration
    3. Read `.claude/agents/team-leader.md` for your full instruction set
    4. Internalize the project requirements above — every agent you spawn should understand these

    ### Phase 2: Spawn the Team

    Spawn agents in this order (respecting dependencies):

    **First wave** (no dependencies):
    {agent_spawn_list}

    **Spawning instructions**:
    - Use the **Agent tool** to spawn each agent
    - Include the contents of their instruction file (`.claude/agents/{{agent}}.md`) as context
    - Give each agent a clear initial task based on Iteration 1 plan below
    - Wait for agents to acknowledge initialization and report their chosen names
    {naming_init}{atlassian_init}{spawning_init}{workflow_init}{workspace_note}
    ### Phase 3: Iteration 1 — Bootstrap

    The first iteration should establish the project foundation:

    #### Research & Strategy (Research Strategist)
    - Research technology options based on requirements and tech stack preferences
    - Produce: technical strategy, iteration plan (3-7 iterations), risk assessment

    #### Architecture (Architect)
    - Design system architecture based on strategy
    - Define API contracts, data models, project structure
    - Establish coding patterns and conventions

    #### Infrastructure (DevOps Specialist)
    - Set up Docker Compose for local development
    - Create CI/CD pipeline configuration
    - Set up project scaffolding (build tools, linting, testing framework)
    {'- Install and configure llm-gateway: `pip install ' + "'llm-gateway @ git+https://github.com/Rushabh1798/llm-gateway.git'" + '`' + chr(10) + '    - Configure LLM_PROVIDER env var in .env and Docker Compose' if config.llm_gateway.enabled else ''}

    #### Implementation (Backend + Frontend)
    - Implement core feature(s) based on iteration 1 scope
    - Follow architecture patterns from Architect
    - Use API contracts for frontend-backend integration
    {'- All LLM calls MUST use llm-gateway (never import vendor SDKs directly)' if config.llm_gateway.enabled else ''}

    #### Quality (QA Engineer)
    - Set up testing framework
    - Set up Playwright for visual verification: `npx playwright install chromium`
    - Write tests for iteration 1 deliverables
    - Capture screenshot baselines for all key pages
    - Define quality gates (including visual regression)

    #### Review (Critic)
    - Review all iteration 1 deliverables
    - Check requirements compliance, architecture compliance, code quality

    ### Phase 4: Verify and Proceed

    Before marking Iteration 1 complete:
    1. All tasks have deliverables
    2. All tests pass
    3. **Smoke test**: Application starts, endpoints respond, UI loads
    4. **Visual verification**: Screenshots of all key pages captured and reviewed
    5. Code review completed
    6. Quality threshold met ({'70%' if config.mode.value == 'mvp' else '90%' if config.mode.value == 'production-ready' else '100%'})
    7. Tag: `iteration-1-verified`

    ## Agent File Locations

    All agent instruction files are in `.claude/agents/`:
    {chr(10).join(f'- `.claude/agents/{a}.md`' for a in agents)}

    Skills are in `.claude/skills/`:
    - Check `.claude/skills/` for available reusable skills

    MCP configuration: `.claude/mcp.json` (if Atlassian integration is enabled)

    ## Quick Reference

    | Config | Value |
    |---|---|
    | Mode | {config.mode.value} |
    | Strategy | {config.strategy.value} |
    | Quality Threshold | {'70%' if config.mode.value == 'mvp' else '90%' if config.mode.value == 'production-ready' else '100%'} |
    | Sub-agent Spawning | {'Enabled' if config.agents.allow_sub_agent_spawning else 'Disabled'} |
    | Atlassian | {'Enabled' if config.atlassian.enabled else 'Disabled'} |
    | Agent Naming | {config.agent_naming.style if config.agent_naming.enabled else 'Disabled'} |
    | LLM Gateway | {'Enabled (local_claude: ' + ('on' if config.llm_gateway.enable_local_claude else 'off') + ')' if config.llm_gateway.enabled else 'Disabled'} |
    | Non-Negotiables | {f'{len(config.non_negotiables)} rules' if config.non_negotiables else 'None'} |

    ---

    **Start now.** Read CLAUDE.md, then begin Phase 2: Spawn the Team.
    """)

    output_path = project_dir / "team-init-plan.md"
    output_path.write_text(content)
