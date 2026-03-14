"""Generate team-init-plan.md — the bootstrap document for the first Claude session."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from forge_cli.config_schema import ForgeConfig, WorkspaceType


def _plan_file_section(config: ForgeConfig) -> str:
    """Generate plan file blueprint section for team-init-plan.md."""
    if not config.project.plan_file:
        return ""

    return dedent(f"""\

    ## Implementation Blueprint

    A plan file has been provided: **`{config.project.plan_file}`**

    This plan is the **AUTHORITATIVE implementation blueprint**. All agents MUST:
    - Read this plan before starting any work
    - Follow the plan's phases, milestones, and deliverables exactly as specified
    - Use the agentic team structure to parallelize work defined in the plan
    - NOT deviate from the plan's architecture or technology decisions unless the
      user explicitly instructs otherwise during the session
    - Treat this plan as the source of truth for scope, sequencing, and implementation details

    The user has planned every detail. Forge's agent team executes this plan — it defines
    **WHAT** to build and in what order. Agent instruction files define **HOW** the team
    operates (roles, workflows, quality gates).
    """)


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


def _phase3_tasks(config: ForgeConfig, agents: list[str]) -> str:
    """Build Phase 3 task list based on actual agent roster and project type."""
    agent_set = set(agents)
    has_frontend = config.has_frontend_involvement()
    is_cli = config.is_cli_project()
    has_web = config.has_web_backend()
    sections: list[str] = []

    if "research-strategist" in agent_set:
        sections.append(dedent("""\

        #### Research & Strategy (Research Strategist)
        - Research technology options based on requirements and tech stack preferences
        - Produce: technical strategy, iteration plan (3-7 iterations), risk assessment"""))

    if "architect" in agent_set:
        if is_cli:
            sections.append(dedent("""\

            #### Architecture (Architect)
            - Design CLI command structure, plugin architecture, and data flow patterns
            - Define module boundaries, configuration schema, error handling strategy
            - Establish coding patterns and conventions"""))
        elif has_frontend and not has_web:
            sections.append(dedent("""\

            #### Architecture (Architect)
            - Design component architecture, page layout system, content schemas
            - Define styling patterns, responsive breakpoints, and build configuration
            - Establish coding patterns and conventions"""))
        else:
            sections.append(dedent("""\

            #### Architecture (Architect)
            - Design system architecture based on strategy
            - Define API contracts, data models, project structure
            - Establish coding patterns and conventions"""))

    if "devops-specialist" in agent_set:
        if is_cli:
            infra_items = dedent("""\

            #### Infrastructure (DevOps Specialist)
            - Set up CI/CD pipeline configuration
            - Set up project scaffolding (build tools, linting, testing framework)
            - Configure package distribution (setuptools/pyproject.toml)""")
        elif has_frontend and not has_web:
            infra_items = dedent("""\

            #### Infrastructure (DevOps Specialist)
            - Set up build pipeline and deployment configuration
            - Configure CI/CD for build, test, and deploy
            - Set up project scaffolding (build tools, linting, testing framework)""")
        else:
            infra_items = dedent("""\

            #### Infrastructure (DevOps Specialist)
            - Set up Docker Compose for local development
            - Create CI/CD pipeline configuration
            - Set up project scaffolding (build tools, linting, testing framework)""")
        if config.llm_gateway.enabled:
            infra_items += "\n    - Install and configure llm-gateway"
        sections.append(infra_items)

    # Implementation section — adapt to project type
    impl_agents = [a for a in ("backend-developer", "frontend-engineer", "frontend-developer") if a in agent_set]
    if impl_agents:
        if is_cli:
            impl_text = dedent("""\

            #### Implementation (Backend Developer)
            - Implement CLI commands and data processing logic
            - Follow architecture patterns from Architect
            - Write input parsing, validation, and error handling""")
        elif has_frontend and not has_web:
            impl_text = dedent("""\

            #### Implementation (Frontend)
            - Implement pages, components, and content based on iteration 1 scope
            - Follow architecture patterns and component interfaces from Architect""")
        elif has_frontend:
            impl_text = dedent("""\

            #### Implementation (Backend + Frontend)
            - Implement core feature(s) based on iteration 1 scope
            - Follow architecture patterns from Architect
            - Use API contracts for frontend-backend integration""")
        else:
            impl_text = dedent("""\

            #### Implementation (Backend Developer)
            - Implement API endpoints and business logic based on iteration 1 scope
            - Follow architecture patterns from Architect
            - Implement data layer and service integrations""")
        if config.llm_gateway.enabled:
            impl_text += "\n    - All LLM calls MUST use llm-gateway (never import vendor SDKs directly)"
        sections.append(impl_text)

    if "qa-engineer" in agent_set:
        if is_cli:
            sections.append(dedent("""\

            #### Quality (QA Engineer)
            - Set up testing framework (pytest)
            - Write tests for CLI commands and data processing
            - Define quality gates (test coverage, command behavior verification)"""))
        elif has_frontend:
            sections.append(dedent("""\

            #### Quality (QA Engineer)
            - Set up testing framework
            - Set up Playwright for visual verification: `npx playwright install chromium`
            - Write tests for iteration 1 deliverables
            - Capture screenshot baselines for all key pages
            - Define quality gates (including visual regression)"""))
        else:
            sections.append(dedent("""\

            #### Quality (QA Engineer)
            - Set up testing framework
            - Write API integration tests for iteration 1 endpoints
            - Define quality gates (coverage targets, API contract compliance)"""))

    if "critic" in agent_set:
        sections.append(dedent("""\

        #### Review (Critic)
        - Review all iteration 1 deliverables
        - Check requirements compliance, architecture compliance, code quality"""))

    return "\n".join(sections) if sections else ""


def _phase4_checklist(config: ForgeConfig) -> str:
    """Build Phase 4 verification checklist based on project type."""
    has_frontend = config.has_frontend_involvement()
    is_cli = config.is_cli_project()
    has_web = config.has_web_backend()
    threshold = '70%' if config.mode.value == 'mvp' else '90%' if config.mode.value == 'production-ready' else '100%'

    items = [
        "1. All tasks have deliverables",
        "2. All tests pass",
    ]

    if is_cli:
        items.append("3. **Smoke test**: CLI installs, commands run, output is correct")
        items.append("4. **Output verification**: Help text and error messages reviewed")
    elif has_frontend and has_web:
        items.append("3. **Smoke test**: Application starts, endpoints respond, UI loads")
        items.append("4. **Visual verification**: Screenshots of all key pages captured and reviewed")
    elif has_frontend:
        items.append("3. **Smoke test**: Build succeeds, dev server starts, pages load")
        items.append("4. **Visual verification**: Screenshots of all key pages captured and reviewed")
    elif has_web:
        items.append("3. **Smoke test**: Server starts, all endpoints respond with correct status codes")
        items.append("4. **API documentation**: OpenAPI docs generated and accurate")
    else:
        items.append("3. **Smoke test**: Application starts and core features work")

    items.extend([
        f"{'5' if len(items) > 3 else '4'}. Code review completed",
        f"{'6' if len(items) > 4 else '5'}. Quality threshold met ({threshold})",
        f"{'7' if len(items) > 5 else '6'}. Tag: `iteration-1-verified`",
    ])

    return "\n    ".join(items)


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
        "auto-pilot": "Auto-Pilot — Full autonomy for all decisions, no permission prompts",
        "co-pilot": "Co-Pilot — Full autonomy for implementation, human input on architecture/scope/domain decisions only",
        "micro-manage": "Micro-Manage — Every significant decision presented to human for approval",
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

    git_auth_init = ""
    if config.has_ssh_auth():
        git_auth_init = dedent(f"""\

        ### Phase 0: Git Authentication Setup

        **Before spawning any agents**, configure git to use SSH authentication.
        This prevents macOS Keychain prompts that would block agent execution.

        1. Verify SSH key exists:
           ```bash
           test -f {config.git.ssh_key_path} && echo "SSH key found" || echo "ERROR: SSH key missing"
           ```
        2. Configure git to use the SSH key (persists in `.git/config`):
           ```bash
           git config core.sshCommand "ssh -i {config.git.ssh_key_path} -o IdentitiesOnly=yes"
           ```
        3. Convert remote URL to SSH (if currently HTTPS):
           ```bash
           git remote -v
           # If HTTPS → git remote set-url origin git@github.com:OWNER/REPO.git
           ```
        4. Verify SSH access:
           ```bash
           ssh -T git@github.com -i {config.git.ssh_key_path} -o IdentitiesOnly=yes
           ```
        5. Verify GitHub CLI auth:
           ```bash
           gh auth status
           ```

        **This must succeed before proceeding to Phase 1.**
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

    ws_type = config.workspace.type
    is_new = config.project.type == "new"

    if ws_type == WorkspaceType.WORKSPACE and is_new:
        workspace_note = dedent("""\

        ### Workspace Setup (workspace — new)

        This is a **new multi-repo workspace**. The directory may be empty or contain only forge-generated files.
        - Create individual git repositories per Architect design within the workspace directory
        - Each repo gets its own README, .gitignore, and CI config
        - Set up cross-repo documentation describing the overall system architecture
        - Each repository is a bounded context with its own release cycle
        """)
    elif ws_type == WorkspaceType.WORKSPACE and not is_new:
        workspace_note = dedent("""\

        ### Workspace Setup (workspace — existing)

        This is an **existing multi-repo workspace**. Multiple independent git repositories exist under this directory.
        - Scan workspace for existing `.git/` directories to discover all repositories
        - Read each repo's README and structure to understand the landscape
        - Map inter-repo dependencies and communication patterns
        - Respect each repo's independent conventions, branching strategy, and CI
        """)
    elif ws_type == WorkspaceType.MONOREPO and is_new:
        workspace_note = dedent("""\

        ### Workspace Setup (monorepo — new)

        This is a **new monorepo**. The directory may be empty or contain only forge-generated files.
        - Init a single git repo and create package directories per Architect design
        - Set up root-level tooling: linting, formatting, CI, shared configs
        - Each package gets its own manifest (`package.json`, `pyproject.toml`, etc.)
        - Establish shared library conventions for cross-package contracts
        """)
    elif ws_type == WorkspaceType.MONOREPO and not is_new:
        workspace_note = dedent("""\

        ### Workspace Setup (monorepo — existing)

        This is an **existing monorepo**. Respect existing conventions:
        - Scan for existing packages by looking for manifests (`package.json`, `pyproject.toml`, `go.mod`, etc.)
        - Understand inter-package dependencies and shared libraries
        - Follow existing monorepo conventions (build system, CI, linting)
        - Do not restructure existing packages unless explicitly required
        """)
    elif is_new:
        workspace_note = dedent("""\

        ### Workspace Setup

        This is a **new project**. The workspace directory may be empty or only contain forge-generated files.
        - Check if `.git/` exists — if not, initialize a git repository
        - Create README.md, .gitignore, and project configuration files as part of Iteration 1
        - Scaffold project structure appropriate for the tech stack
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

    pre_init_sections = [s for s in [
        _plan_file_section(config), _non_negotiables_init_section(config),
    ] if s.strip()]
    pre_init_content = "\n".join(pre_init_sections)

    post_spawn_sections = [s for s in [
        naming_init, atlassian_init, spawning_init, workflow_init, workspace_note,
    ] if s.strip()]
    post_spawn_content = "\n".join(post_spawn_sections)

    init_sequence_sections = [s for s in [git_auth_init] if s.strip()]
    init_sequence_content = "\n".join(init_sequence_sections)

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
    {pre_init_content}
    ## Initialization Sequence
    {init_sequence_content}
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
    {post_spawn_content}
    ### Phase 3: Iteration 1 — Bootstrap

    The first iteration should establish the project foundation:
    {_phase3_tasks(config, agents)}
    ### Phase 4: Verify and Proceed

    Before marking Iteration 1 complete:
    {_phase4_checklist(config)}

    ### Phase 5: Continue Until Done (MANDATORY)

    **Iteration 1 is the BEGINNING, not the end.** After verifying Iteration 1:

    1. **Assess remaining work**: Compare what was delivered against ALL project requirements
    2. **Plan the next iteration**: Decompose remaining requirements into Iteration 2 tasks
    3. **Execute the full lifecycle again**: PLAN → EXECUTE → TEST → INTEGRATE → REVIEW → CRITIQUE → DECISION
    4. **Repeat** until every single requirement is implemented, tested, and verified
    5. **Final verification**: Run a comprehensive end-to-end smoke test of the ENTIRE application
    6. **Commit everything**: `git status` must show a clean working tree — zero uncommitted files
    7. **Tag the final release**: `git tag v1.0.0` (or appropriate version)

    **You are NOT done until:**
    - Every requirement from the project context is fully implemented
    - All non-negotiable rules are met
    - All code is committed and pushed
    - All iterations are tagged (`iteration-N-verified`)
    - The complete application passes end-to-end smoke tests
    - The Critic has reviewed the final state and found no BLOCKERs

    **Do NOT stop, pause, or ask if you should continue** — the answer is always YES until the
    above conditions are met. If you hit the cost cap, report what remains unfinished.

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
    | Git Auth | {'SSH (' + config.git.ssh_key_path + ')' if config.has_ssh_auth() else 'Default (system)'} |
    | Non-Negotiables | {f'{len(config.non_negotiables)} rules' if config.non_negotiables else 'None'} |

    ---

    **Start now.** Read CLAUDE.md, then begin Phase 2: Spawn the Team.
    """)

    output_path = project_dir / "team-init-plan.md"
    output_path.write_text(content)
