"""Generate reusable skills for .claude/skills/ directory."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from forge_cli.config_schema import ForgeConfig


def generate_skills(config: ForgeConfig, skills_dir: Path) -> None:
    """Generate reusable skill files based on project configuration."""
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Always generate status skill
    _write_skill(skills_dir / "team-status.md", _status_skill(config))

    # Always generate iteration skill
    _write_skill(skills_dir / "iteration-review.md", _iteration_review_skill(config))

    # Spawn agent skill (if sub-agent spawning enabled)
    if config.agents.allow_sub_agent_spawning:
        _write_skill(skills_dir / "spawn-agent.md", _spawn_agent_skill(config))

    # Atlassian skills
    if config.atlassian.enabled:
        _write_skill(skills_dir / "jira-update.md", _jira_update_skill(config))
        _write_skill(skills_dir / "sprint-report.md", _sprint_report_skill(config))

    # Smoke test skill
    _write_skill(skills_dir / "smoke-test.md", _smoke_test_skill(config))

    # Screenshot review skill (visual verification)
    _write_skill(skills_dir / "screenshot-review.md", _screenshot_review_skill(config))

    # PR workflow skill
    _write_skill(skills_dir / "create-pr.md", _pr_workflow_skill(config))

    # Release management skill
    _write_skill(skills_dir / "release.md", _release_management_skill(config))

    # Architecture review skill
    _write_skill(skills_dir / "arch-review.md", _arch_review_skill(config))


def _write_skill(path: Path, content: str) -> None:
    # Strip the template indentation (from Python source nesting) while
    # preserving intentional indentation within the content.  We use the
    # first non-empty line's indent as the baseline to strip — this is
    # always the `---` frontmatter line at the template's indentation level.
    lines = content.split("\n")
    first_non_empty = next((l for l in lines if l.strip()), "")
    baseline = len(first_non_empty) - len(first_non_empty.lstrip())
    if baseline > 0:
        lines = [line[baseline:] if line[:baseline].isspace() else line for line in lines]
    path.write_text("\n".join(lines).strip() + "\n")


def _indent(spaces: int, text: str) -> str:
    """Add leading spaces to each line of text."""
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" for line in text.split("\n"))


def _tech_stack_summary(config: ForgeConfig) -> str:
    """Build a concise tech stack summary for skill templates."""
    parts = []
    if config.tech_stack.languages:
        parts.append(f"Languages: {', '.join(config.tech_stack.languages)}")
    if config.tech_stack.frameworks:
        parts.append(f"Frameworks: {', '.join(config.tech_stack.frameworks)}")
    if config.tech_stack.databases:
        parts.append(f"Databases: {', '.join(config.tech_stack.databases)}")
    if config.tech_stack.infrastructure:
        parts.append(f"Infrastructure: {', '.join(config.tech_stack.infrastructure)}")
    return " | ".join(parts) if parts else "Not specified"


def _agents_list(config: ForgeConfig) -> str:
    """Get comma-separated list of active agents."""
    return ", ".join(config.get_active_agents())


def _test_commands(config: ForgeConfig) -> str:
    """Generate test commands based on tech stack."""
    cmds: list[str] = []
    langs = [l.lower() for l in config.tech_stack.languages]
    frameworks = [f.lower() for f in config.tech_stack.frameworks]
    is_cli = config.is_cli_project()
    has_frontend = config.has_frontend_involvement()
    has_web = config.has_web_backend()

    # Python backend detection — distinguish CLI, Django, FastAPI, generic
    if "python" in langs or any(f in frameworks for f in ("fastapi", "django", "flask", "click", "typer")):
        if is_cli:
            cli_fw = "Click" if "click" in frameworks else "Typer" if "typer" in frameworks else "CLI"
            cmds.append(f"- CLI ({cli_fw}): `pytest` and verify `python -m <package> --help` runs")
        elif "django" in frameworks or "drf" in frameworks:
            cmds.append("- Backend (Django): `pytest` / `manage.py test` and verify `manage.py runserver` starts")
        elif "fastapi" in frameworks:
            cmds.append("- Backend (FastAPI): `pytest` and verify server starts with `uvicorn`")
        elif "flask" in frameworks:
            cmds.append("- Backend (Flask): `pytest` and verify `flask run` starts")
        else:
            cmds.append("- Python: `pytest`")

    # Go backend
    if "go" in langs or "golang" in langs:
        cmds.append("- Backend (Go): `go test ./...` and verify service starts")

    # Frontend / static site
    if has_frontend:
        if "astro" in frameworks:
            cmds.append("- Frontend (Astro): `npm run build` and `npm run dev` starts without errors")
        elif "nextjs" in frameworks or "next.js" in frameworks or "next" in frameworks:
            cmds.append("- Frontend (Next.js): `npm test` and `npm run build`")
        elif "react" in frameworks:
            cmds.append("- Frontend (React): `npm test` and `npm run build`")
        elif "typescript" in langs or "javascript" in langs:
            cmds.append("- Frontend: `npm test` and `npm run build`")

    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        cmds.append(f"- Database ({dbs}): verify migrations apply cleanly")
    return "\n".join(cmds) if cmds else "- Run project test suite"


def _quality_gate_checks(config: ForgeConfig) -> str:
    """Generate quality gate checks based on tech stack and mode."""
    checks: list[str] = []
    langs = [l.lower() for l in config.tech_stack.languages]
    frameworks = [f.lower() for f in config.tech_stack.frameworks]
    has_frontend = config.has_frontend_involvement()
    is_cli = config.is_cli_project()
    has_web = config.has_web_backend()

    # CLI-specific checks
    if is_cli:
        cli_fw = "Click" if "click" in frameworks else "Typer" if "typer" in frameworks else "CLI"
        checks.append(f"- {cli_fw} commands parse correctly and `--help` responds?")
        checks.append("- Python tests pass (`pytest`)?")
    else:
        # Frontend checks
        if has_frontend:
            if "astro" in frameworks:
                checks.append("- Astro build succeeds (`npm run build`)?")
                checks.append("- Dev server starts without errors (`npm run dev`)?")
            elif "nextjs" in frameworks or "next.js" in frameworks or "next" in frameworks:
                checks.append("- Next.js build succeeds and dev server starts?")
            elif "react" in frameworks and ("typescript" in langs or "javascript" in langs):
                checks.append("- TypeScript compilation successful with no errors?")
                checks.append("- React dev server starts and renders without console errors?")

        # Backend checks
        if "fastapi" in frameworks:
            checks.append("- FastAPI server starts and health endpoint responds?")
            checks.append("- Python tests pass (`pytest`)?")
        elif "django" in frameworks or "drf" in frameworks:
            checks.append("- Django server starts and health endpoint responds?")
            checks.append("- Python tests pass (`pytest` / `manage.py test`)?")
        elif "flask" in frameworks:
            checks.append("- Flask server starts and health endpoint responds?")
            checks.append("- Python tests pass (`pytest`)?")
        elif has_web and ("python" in langs):
            checks.append("- Server starts and health endpoint responds?")
            checks.append("- Python tests pass (`pytest`)?")
        elif "go" in langs or "golang" in langs:
            checks.append("- Go services build and start successfully?")
            checks.append("- Go tests pass (`go test ./...`)?")
        elif "python" in langs and not has_frontend:
            checks.append("- Python tests pass (`pytest`)?")

    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        checks.append(f"- Database ({dbs}) migrations applied successfully?")
    if has_web and not has_frontend:
        checks.append("- API endpoints respond with correct status codes and schemas?")
    checks.append(f"- Coverage meets {config.mode.value} threshold?")
    return "\n".join(f"   {c}" for c in checks) if checks else "   - All tests pass?"


def _functional_checks(config: ForgeConfig) -> str:
    """Generate functional verification checks from project requirements."""
    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    combined = f"{req} {desc}"
    has_frontend = config.has_frontend_involvement()
    is_cli = config.is_cli_project()
    checks: list[str] = []

    # CLI-specific checks
    if is_cli:
        if "pipeline" in combined or "etl" in combined:
            checks.append("- Pipeline definitions parse and validate correctly?")
            checks.append("- Sample pipeline executes end-to-end (extract → transform → load)?")
        if "extractor" in combined or "csv" in combined or "json" in combined:
            checks.append("- Built-in extractors read data correctly (CSV, JSON, API, DB)?")
        if "transformer" in combined or "filter" in combined or "aggregate" in combined:
            checks.append("- Transformers process data correctly (filter, map, aggregate)?")
        if "loader" in combined:
            checks.append("- Loaders write output correctly to target destinations?")
        if "plugin" in combined:
            checks.append("- Plugin loading and discovery works for custom extensions?")
        if "dry-run" in combined or "dry_run" in combined:
            checks.append("- Dry-run mode shows planned operations without side effects?")
        if "progress" in combined:
            checks.append("- Progress reporting shows accurate status during execution?")
        if "dead-letter" in combined or "dead_letter" in combined or "error" in combined:
            checks.append("- Error handling captures failures in dead-letter queue?")
        if "version" in combined and "migration" in combined:
            checks.append("- Pipeline versioning and migration between versions works?")
        if "concurrent" in combined or "parallel" in combined:
            checks.append("- Parallel execution runs correctly with configured concurrency?")

    # Web application checks
    if "auth" in combined:
        checks.append("- User authentication flows working (registration, login, logout)?")
    if "transaction" in combined or "debit" in combined or "credit" in combined or "ledger" in combined:
        checks.append("- Transaction processing works correctly (create, validate, record)?")
    if "audit" in combined or "compliance" in combined:
        checks.append("- Audit trail captures all operations with immutable records?")
    if ("product" in combined or "catalog" in combined) and has_frontend:
        checks.append("- Product catalog functionality complete (browse, search, filter)?")
    if "cart" in combined or "shopping" in combined:
        checks.append("- Shopping cart operations functional (add, remove, update quantities)?")
    if "checkout" in combined or "payment" in combined:
        checks.append("- Checkout/payment process works end-to-end?")
    if ("api" in combined or "rest" in combined) and not is_cli:
        checks.append("- API endpoints respond correctly with proper status codes?")
    if "kanban" in combined or "drag-and-drop" in combined or "drag and drop" in combined:
        checks.append("- Kanban board renders correctly with drag-and-drop between columns?")
    if "task" in combined and ("assignment" in combined or "due date" in combined or "priorit" in combined):
        checks.append("- Task creation, assignment, and priority/due-date setting works?")
    if "real-time" in combined or "websocket" in combined or "chat" in combined:
        checks.append("- Real-time features (WebSocket/chat) connect and deliver messages?")
    if "@mention" in combined or "mention" in combined:
        checks.append("- @mention notifications trigger and display correctly?")
    if "activity" in combined and "feed" in combined:
        checks.append("- Activity feed shows recent actions in chronological order?")
    if ("dashboard" in combined or "admin" in combined) and has_frontend:
        checks.append("- Dashboard/admin views render and display correct data?")
    if "search" in combined:
        checks.append("- Search functionality returns relevant results?")
    if "notification" in combined or "email" in combined or "webhook" in combined:
        checks.append("- Notification/webhook system delivers messages?")
    if ("upload" in combined or "file" in combined or "image" in combined) and not is_cli:
        checks.append("- File upload/media handling works correctly?")
    if "rate" in combined and "limit" in combined:
        checks.append("- Rate limiting enforced correctly on protected endpoints?")
    if "rbac" in combined or ("role" in combined and "access" in combined):
        checks.append("- Role-based access control enforces permissions correctly?")
    # Static site specific
    if "dark mode" in combined or "dark-mode" in combined:
        checks.append("- Dark mode toggle works and persists preference?")
    if "blog" in combined or "mdx" in combined:
        checks.append("- Blog posts render correctly from MDX/markdown?")
    if "portfolio" in combined or "showcase" in combined:
        checks.append("- Project showcase displays with screenshots and descriptions?")
    if "contact" in combined and "form" in combined:
        checks.append("- Contact form validates input and submits successfully?")
    if "responsive" in combined:
        checks.append("- Responsive design works across desktop and mobile viewports?")
    # Enterprise HR specific
    if "payroll" in combined:
        checks.append("- Payroll processing calculates correctly (taxes, deductions)?")
    if "leave" in combined and ("management" in combined or "tracking" in combined or "pto" in combined):
        checks.append("- Leave management workflow works (request, approve, reject)?")
    if "org" in combined and ("chart" in combined or "hierarchy" in combined):
        checks.append("- Org chart displays hierarchy correctly?")
    if "sso" in combined or "saml" in combined or "oidc" in combined:
        checks.append("- SSO integration authenticates via SAML/OIDC correctly?")
    if "performance review" in combined:
        checks.append("- Performance review workflow functions correctly?")
    if "document" in combined and ("management" in combined or "upload" in combined or "offer" in combined or "contract" in combined):
        checks.append("- Document management (upload, download, versioning) works correctly?")
    # E-commerce specific
    if "vendor" in combined and ("onboard" in combined or "storefront" in combined):
        checks.append("- Vendor onboarding and storefront creation works?")
    if "review" in combined and "rating" in combined:
        checks.append("- Customer reviews and ratings system works?")
    if "inventory" in combined:
        checks.append("- Inventory management tracks stock correctly?")
    if "order" in combined and ("status" in combined or "tracking" in combined or "management" in combined):
        checks.append("- Order management with status tracking works end-to-end?")

    if not checks:
        checks.append("- Core feature requirements from project spec are functional?")

    return "\n".join(checks)


def _domain_context(config: ForgeConfig) -> str:
    """Build a domain context block from project description and requirements."""
    return (
        f"**Project**: {config.project.description}\n"
        f"    **Requirements**: {config.project.requirements}\n"
        f"    **Mode**: {config.mode.value} | **Strategy**: {config.strategy.value}"
    )


def _agent_use_cases(config: ForgeConfig) -> str:
    """Generate 'When to Use Which Agent' section based on actual roster."""
    agents = set(config.get_active_agents())
    cases: list[str] = []
    if "backend-developer" in agents:
        if config.is_cli_project():
            cases.append("- **Implement CLI commands or data processing**: `backend-developer`")
        else:
            cases.append("- **Implement API endpoints or business logic**: `backend-developer`")
    if "frontend-engineer" in agents:
        cases.append("- **Build UI components or pages**: `frontend-engineer`")
    if "frontend-developer" in agents:
        cases.append("- **Build frontend logic and interactions**: `frontend-developer`")
    if "frontend-designer" in agents:
        cases.append("- **Design UI/UX and component specs**: `frontend-designer`")
    if "research-strategist" in agents:
        cases.append("- **Research a technology or approach**: `research-strategist`")
    if "architect" in agents:
        cases.append("- **Design system architecture or API contracts**: `architect`")
    if "devops-specialist" in agents:
        cases.append("- **Set up CI/CD, Docker, or infrastructure**: `devops-specialist`")
    if "qa-engineer" in agents:
        cases.append("- **Write or run tests, validate quality**: `qa-engineer`")
    if "security-tester" in agents:
        cases.append("- **Security audits or vulnerability scanning**: `security-tester`")
    if "performance-engineer" in agents:
        cases.append("- **Load testing or performance optimization**: `performance-engineer`")
    if "documentation-specialist" in agents:
        cases.append("- **Write API docs, guides, or architecture docs**: `documentation-specialist`")
    if "critic" in agents:
        cases.append("- **Independent quality review**: `critic`")
    if "scrum-master" in agents:
        cases.append("- **Sprint management and Jira updates**: `scrum-master`")
    return "\n".join(f"    {c}" for c in cases)


def _agent_routing(config: ForgeConfig) -> str:
    """Generate iteration review agent routing based on actual roster."""
    agents = set(config.get_active_agents())
    routes: list[str] = []
    is_cli = config.is_cli_project()
    if "backend-developer" in agents:
        if is_cli:
            routes.append("- CLI/processing issues -> backend-developer")
        else:
            routes.append("- Backend/API issues -> backend-developer")
    if "frontend-engineer" in agents:
        routes.append("- Frontend/UI issues -> frontend-engineer")
    if "frontend-developer" in agents:
        routes.append("- Frontend logic issues -> frontend-developer")
    if "qa-engineer" in agents:
        routes.append("- Test failures -> qa-engineer")
    if "devops-specialist" in agents:
        routes.append("- Infrastructure -> devops-specialist")
    if "architect" in agents:
        routes.append("- Architecture concerns -> architect")
    if "security-tester" in agents:
        routes.append("- Security issues -> security-tester")
    if "documentation-specialist" in agents:
        routes.append("- Documentation gaps -> documentation-specialist")
    return "\n".join(f"      {r}" for r in routes)


def _pr_reviewer_routing(config: ForgeConfig) -> str:
    """Generate PR reviewer routing based on actual agent roster."""
    agents = set(config.get_active_agents())
    routes: list[str] = []
    if "architect" in agents:
        routes.append("- Architecture/cross-cutting changes: architect + team-leader")
    if "backend-developer" in agents:
        label = "CLI/processing" if config.is_cli_project() else "Backend"
        routes.append(f"- {label} changes: backend-developer or team-leader")
    if "frontend-engineer" in agents:
        routes.append("- Frontend changes: frontend-engineer or team-leader")
    if "frontend-developer" in agents:
        routes.append("- Frontend changes: frontend-developer or team-leader")
    if "devops-specialist" in agents:
        routes.append("- Infrastructure: devops-specialist + team-leader")
    if "security-tester" in agents:
        routes.append("- Security-sensitive changes: security-tester")
    if "documentation-specialist" in agents:
        routes.append("- Documentation changes: documentation-specialist")
    return "\n".join(f"       {r}" for r in routes)


def _security_checks(config: ForgeConfig) -> str:
    """Generate domain-specific security checks."""
    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    combined = f"{req} {desc}"
    is_cli = config.is_cli_project()
    checks: list[str] = []

    if "auth" in combined:
        checks.append("- Authentication: JWT/session validation on protected endpoints")
        checks.append("- Password hashing uses bcrypt/argon2, never plaintext")
    if "payment" in combined or "checkout" in combined:
        checks.append("- Payment data: no card numbers stored in plain text")
        checks.append("- Checkout flow: CSRF protection on state-changing operations")
    if "pci" in combined:
        checks.append("- PCI-DSS: sensitive data masked in logs and responses")
    if "user" in combined and not is_cli:
        checks.append("- User data: input validation on all user-facing forms")
        checks.append("- Authorization: users can only access their own resources")
    if "sso" in combined or "saml" in combined or "oidc" in combined:
        checks.append("- SSO: SAML/OIDC token validation, secure session handling")
    if "audit" in combined:
        checks.append("- Audit logs: immutable, no sensitive data in plain text")
    checks.append("- No API keys, passwords, or tokens in source code")
    if config.tech_stack.databases:
        checks.append("- SQL injection prevention: parameterized queries only")
    if is_cli:
        checks.append("- File path traversal prevention on user-provided paths")
        checks.append("- Credentials/tokens not logged in verbose output")

    return "\n".join(f"   {c}" for c in checks)


def _status_skill(config: ForgeConfig) -> str:
    agents = _agents_list(config)
    stack = _tech_stack_summary(config)
    return dedent(f"""\
    ---
    name: team-status
    description: "Get a comprehensive status report of all active agents and current iteration"
    argument-hint: ""
    ---

    # Team Status Report

    > Project: {config.project.description} | Mode: {config.mode.value} | Stack: {stack}

    Collect and present a comprehensive status report:

    1. **Current Iteration**: Number, phase, progress percentage
    2. **Active Agents**: Status of each agent ({agents})
       - Current task and progress
       - Blockers or dependencies
       - Branch and last commit
    3. **Tech Stack Health**:
{_quality_gate_checks(config)}
    4. **Feature Progress**:
{_indent(3, _functional_checks(config))}
    5. **Completed Work**: Tasks finished in this iteration
    6. **Upcoming Work**: Next tasks in the pipeline
    7. **Integration Status**: Branch merge status, any conflicts
    8. **Cost Tracking**: Budget consumed vs. remaining (cap: ${config.cost.max_development_cost or 'N/A'})

    Present this in a clean, formatted summary for the human.
    """)


def _iteration_review_skill(config: ForgeConfig) -> str:
    agents = _agents_list(config)
    stack = _tech_stack_summary(config)
    return dedent(f"""\
    ---
    name: iteration-review
    description: "Review current iteration deliverables and decide: proceed, rework, rollback, or escalate"
    argument-hint: "[iteration-number]"
    ---

    # Iteration Review

    > {_domain_context(config)}
    > Stack: {stack}

    Review the current iteration and make a DECISION:

    1. **Collect all deliverables** from this iteration
    2. **Verify against acceptance criteria** for each task
    3. **Check quality gates**:
{_quality_gate_checks(config)}
    4. **Check functional deliverables**:
{_indent(3, _functional_checks(config))}
    5. **Run smoke test** (use /smoke-test skill)
    6. **Decision**: PROCEED | REWORK | ROLLBACK | ESCALATE

    If PROCEED: tag the iteration as verified, plan next iteration.
    If REWORK: route issues to specific agents:
{_agent_routing(config)}
    If ROLLBACK: restore last verified tag, ensure rollback scripts are safe.
    If ESCALATE: present situation to human with trade-off options and timeline impact.

    $ARGUMENTS
    """)


def _spawn_agent_skill(config: ForgeConfig) -> str:
    agents = config.get_active_agents()
    stack = _tech_stack_summary(config)

    # Build agent list with role descriptions
    role_descriptions = {
        "team-leader": "Orchestration, task decomposition, iteration management",
        "research-strategist": "Technical research, strategy documents, iteration planning",
        "architect": "System design, API contracts, architecture decisions, ADRs",
        "backend-developer": "Server-side implementation, APIs, database logic, business logic",
        "frontend-engineer": "Full frontend — UI components, state management, API integration",
        "frontend-designer": "UI/UX design, wireframes, design system, component specs",
        "frontend-developer": "Frontend logic, state management, complex interactions",
        "qa-engineer": "Test strategy, test implementation, quality gates, bug tracking",
        "devops-specialist": "CI/CD, Docker, infrastructure, deployment, monitoring",
        "security-tester": "Security audits, vulnerability scanning, auth review, OWASP",
        "performance-engineer": "Load testing, profiling, optimization, benchmarks",
        "documentation-specialist": "API docs, architecture docs, user guides, ADRs",
        "critic": "Independent quality review, governance oversight, deliverable evaluation",
        "scrum-master": "Sprint management, Jira/Confluence, ceremony facilitation",
    }
    agent_list_items = []
    for a in agents:
        role_desc = role_descriptions.get(a, "Custom agent role")
        agent_list_items.append(f"    - `{a}` — {role_desc}")
    agent_list = "\n".join(agent_list_items)

    return dedent(f"""\
    ---
    name: spawn-agent
    description: "Spawn a new agent with the correct instruction file"
    argument-hint: "<agent-type> <task-description>"
    ---

    # Spawn Agent

    > Project: {config.project.description} | Mode: {config.mode.value} | Stack: {stack}

    Spawn a new agent from the forge instruction files.

    **Agent type**: First word of $ARGUMENTS
    **Task**: Remaining words of $ARGUMENTS

    ## Available Agents

{agent_list}

    ## When to Use Which Agent

{_agent_use_cases(config)}

    ## Steps

    1. **Validate agent type**: Confirm the agent file exists at `.claude/agents/<agent-type>.md`
    2. **Read the instruction file**: Load `.claude/agents/<agent-type>.md` in full
    3. **Spawn with context**: Use the Agent tool with:
       - The full instruction file as system context
       - The task description as the initial prompt
       - Project context: {config.project.description} ({config.mode.value} mode, {config.strategy.value} strategy)
    4. **Verify spawn**: Confirm the sub-agent acknowledged its role and task
    5. **Track**: Log the spawned agent in the current iteration status

    ## Error Handling

    - If agent file not found: list available agents from `.claude/agents/` and report error
    - If spawn fails: retry once, then escalate to team-leader
    - If agent type is ambiguous: ask for clarification before spawning

    $ARGUMENTS
    """)


def _jira_update_skill(config: ForgeConfig) -> str:
    project_key = config.atlassian.jira_project_key or "PROJ"
    stack = _tech_stack_summary(config)
    strategy = config.strategy.value

    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    combined = f"{req} {desc}"

    # Domain-specific ticket examples and types
    examples: list[str] = []
    domain_ticket_types: list[str] = []
    if "hr" in combined or "payroll" in combined:
        examples.append(f"- `{project_key}-42` \"In Progress\" \"Implementing payroll calculation engine with tax tables\"")
        examples.append(f"- `{project_key}-55` \"In Review\" \"Employee onboarding flow complete — SSO integration verified\"")
        examples.append(f"- `{project_key}-70` \"Testing\" \"Leave approval workflow ready for QA — edge cases covered\"")
        domain_ticket_types.extend([
            "- **Payroll**: tax calculation, salary processing, pay stub generation",
            "- **Leave Management**: PTO requests, approval workflows, balance tracking",
            "- **Employee Profiles**: onboarding, org hierarchy, document management",
            "- **Compliance**: audit logging, SSO integration, data protection",
        ])
    elif "e-commerce" in combined or "marketplace" in combined:
        examples.append(f"- `{project_key}-42` \"In Progress\" \"Implementing Stripe checkout flow with webhook handling\"")
        examples.append(f"- `{project_key}-55` \"In Review\" \"Product catalog search with Elasticsearch — filters working\"")
        examples.append(f"- `{project_key}-70` \"Testing\" \"Vendor dashboard analytics ready for QA — revenue charts verified\"")
        domain_ticket_types.extend([
            "- **Vendor**: onboarding, storefront setup, dashboard, payout management",
            "- **Payments**: Stripe integration, checkout flow, refund handling",
            "- **Catalog**: product listing, search, filters, inventory management",
            "- **Orders**: status tracking, fulfillment, shipping notifications",
        ])
    elif "api" in combined or "transaction" in combined or "financial" in combined:
        examples.append(f"- `{project_key}-42` \"In Progress\" \"Implementing double-entry bookkeeping for debit/credit transactions\"")
        examples.append(f"- `{project_key}-55` \"In Review\" \"Audit trail logging complete — immutable log verified\"")
        domain_ticket_types.extend([
            "- **Transactions**: ingestion, bookkeeping, balance calculation",
            "- **Compliance**: audit trails, PCI-DSS data handling, access control",
            "- **Integration**: webhook notifications, rate limiting, API versioning",
        ])
    else:
        examples.append(f"- `{project_key}-42` \"In Progress\" \"Implementing core feature\"")
        examples.append(f"- `{project_key}-55` \"In Review\" \"Feature complete, pending QA\"")
    examples_text = "\n".join(f"    {e}" for e in examples)

    domain_types_section = ""
    if domain_ticket_types:
        types_text = "\n".join(f"    {t}" for t in domain_ticket_types)
        domain_types_section = f"\n\n    ## Domain Ticket Categories\n\n{types_text}"

    # Strategy-specific update requirements
    strategy_section = ""
    if strategy == "micro-manage":
        strategy_section = dedent("""\

        ## Micro-Manage Progress Tracking

        When updating tickets under micro-manage strategy, include:
        - **Time spent**: estimated hours on this update
        - **% complete**: current completion estimate
        - **Blockers**: list any blocking issues with ticket references
        - **Dependencies**: link related tickets that this work affects
        - **Next steps**: what will be done in the next work session
        """)
    elif strategy == "co-pilot":
        strategy_section = dedent("""\

        ## Co-Pilot Update Guidelines

        When updating tickets, include enough context for human review:
        - Summarize what was done and key decisions made
        - Flag any design choices that may need human input
        - Note if the work affects other tickets or team members
        """)

    # Quality fields for production-ready/no-compromise modes
    quality_section = ""
    mode = config.mode.value
    if mode in ("production-ready", "no-compromise"):
        quality_section = dedent(f"""\

        ## Quality Fields ({mode})

        Before transitioning to "Done", verify these ticket fields are set:
        - **Acceptance criteria**: all criteria checked and met
        - **Test coverage**: unit and integration tests written
        - **Security review**: security-relevant changes reviewed{" by security-tester" if "security-tester" in set(config.get_active_agents()) else ""}
        - **Documentation**: API docs and architecture docs updated if applicable
        """)

    return dedent(f"""\
    ---
    name: jira-update
    description: "Update a Jira ticket with current progress"
    argument-hint: "<ticket-key> <status> <comment>"
    ---

    # Jira Ticket Update

    > {_domain_context(config)}
    > Stack: {stack}

    Update a Jira ticket using the Atlassian MCP tool.

    **Ticket key**: e.g., {project_key}-123
    **Status transitions**: To Do -> In Progress -> In Review -> Testing -> Done

    ## Examples

{examples_text}

    ## Steps

    1. Parse $ARGUMENTS for ticket key, new status, and comment
    2. Use the Atlassian MCP tool to transition the ticket status
    3. Add a comment with the provided text, signed with your agent name
    4. If the ticket doesn't exist, report back — don't create it without Team Leader approval
    5. Link related tickets if this work creates or resolves dependencies
{domain_types_section}{strategy_section}{quality_section}
    ## Agent Usage

    All agents ({_agents_list(config)}) should update their assigned tickets when:
    - Starting work on a task (-> In Progress)
    - Completing implementation (-> In Review)
    - After QA approval (-> Testing / Done)

    $ARGUMENTS
    """)


def _sprint_report_skill(config: ForgeConfig) -> str:
    project_key = config.atlassian.jira_project_key or "[project key]"
    stack = _tech_stack_summary(config)
    strategy = config.strategy.value
    mode = config.mode.value

    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    combined = f"{req} {desc}"

    # Domain-specific metrics
    domain_metrics: list[str] = []
    if "hr" in combined or "payroll" in combined:
        domain_metrics.extend([
            "- **HR Modules**: payroll processing status, leave management, org chart, performance reviews",
            "- **Compliance**: audit logging coverage, SSO integration progress, data protection measures",
            "- **Employee Features**: profile completeness, document management, onboarding flow status",
        ])
    elif "e-commerce" in combined or "marketplace" in combined:
        domain_metrics.extend([
            "- **Commerce Features**: checkout flow, Stripe payment integration, order management status",
            "- **Vendor Pipeline**: vendor onboarding count, storefront status, dashboard features",
            "- **Catalog & Inventory**: product listing, search/filter, inventory tracking progress",
        ])
    elif "api" in combined or "transaction" in combined or "financial" in combined:
        domain_metrics.extend([
            "- **API Endpoints**: implemented vs. planned, integration test coverage",
            "- **Transaction Processing**: bookkeeping accuracy, audit trail completeness",
            "- **Compliance**: PCI-DSS checklist items completed, security review status",
        ])
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        domain_metrics.append(f"- **Database ({dbs})**: migration status, schema changes, query performance")

    domain_section = ""
    if domain_metrics:
        dm_text = "\n".join(f"       {m}" for m in domain_metrics)
        domain_section = f"\n       **Domain Progress**:\n{dm_text}"

    # Strategy-specific reporting sections
    strategy_section = ""
    if strategy == "micro-manage":
        strategy_section = dedent("""\

        ## Detailed Progress Tracking (Micro-Manage)

        For each in-progress ticket, include:
        - Agent assigned and estimated hours spent
        - % completion with expected delivery date
        - Detailed blocker analysis with impact assessment
        - Dependency chain: upstream/downstream tickets affected
        - Risk assessment: high/medium/low with mitigation plan

        Include velocity trend: compare this sprint with previous sprints.
        Flag any tickets that are behind schedule with recommended actions.
        """)
    elif strategy == "co-pilot":
        strategy_section = dedent("""\

        ## Decision Points for Human Review

        Highlight items needing human input:
        - Architecture decisions that were deferred
        - Scope changes discovered during implementation
        - Quality trade-offs that need confirmation
        """)

    # Mode-specific quality section
    quality_section = ""
    if mode in ("production-ready", "no-compromise"):
        quality_items = [
            "- Test coverage: current % and target",
            "- Security review: pending items count",
        ]
        if "security-tester" in set(config.get_active_agents()):
            quality_items.append("- Security audit: findings open vs. resolved")
        if "performance-engineer" in set(config.get_active_agents()):
            quality_items.append("- Performance: benchmark results vs. targets")
        qi_text = "\n".join(f"       {q}" for q in quality_items)
        quality_section = f"\n       **Quality Gates ({mode})**:\n{qi_text}"

    # Tech stack component status
    tech_components: list[str] = []
    frameworks = [f.lower() for f in config.tech_stack.frameworks]
    languages = [l.lower() for l in config.tech_stack.languages]
    for fw in frameworks:
        if fw in ("next.js", "react"):
            tech_components.append(f"- {fw}: build succeeds, dev server starts, no console errors")
        elif fw in ("django", "drf", "django rest framework"):
            tech_components.append("- Django: server starts, health endpoint responds, tests pass")
        elif fw in ("fastapi",):
            tech_components.append("- FastAPI: server starts, /docs accessible, tests pass")
    for db in config.tech_stack.databases:
        tech_components.append(f"- {db}: migrations applied, connection verified")
    if "go" in languages:
        tech_components.append("- Go services: build succeeds, tests pass, health endpoints respond")
    tech_text = ""
    if tech_components:
        tc_text = "\n".join(f"       {t}" for t in tech_components)
        tech_text = f"\n       **Tech Stack Health**:\n{tc_text}"

    # Agent attribution
    agents = config.get_active_agents()
    agent_text = ", ".join(agents)

    return dedent(f"""\
    ---
    name: sprint-report
    description: "Generate a sprint report from Jira and present it"
    argument-hint: ""
    ---

    # Sprint Report

    > {_domain_context(config)}
    > Stack: {stack}

    Generate a sprint status report using Jira data.

    ## Steps

    1. Fetch current sprint from Jira project {project_key}
    2. Collect all tickets in the sprint
    3. Summarize:
       - **Completed**: tickets done this sprint (with agent attribution: {agent_text})
       - **In Progress**: tickets being worked on (agent, % complete, blockers)
       - **Blocked**: tickets that are blocked (blocker description, impact, assigned agent)
       - **To Do**: tickets not yet started (priority order)
       - **Velocity**: story points completed vs committed, trend vs. previous sprint{domain_section}{quality_section}{tech_text}
    4. **Quality Gate Checks**:
{_quality_gate_checks(config)}
    5. Present a clean formatted report with:
       - Executive summary (3-5 bullet points)
       - Detailed breakdown by category
       - Risks and blockers requiring attention
       - Recommendations for next sprint
{strategy_section}
    $ARGUMENTS
    """)


def _smoke_test_skill(config: ForgeConfig) -> str:
    stack = _tech_stack_summary(config)
    has_frontend = config.has_frontend_involvement()
    has_web = config.has_web_backend()
    is_cli = config.is_cli_project()
    frameworks = [f.lower() for f in config.tech_stack.frameworks]
    functional = _functional_checks(config)

    # Build sections as plain strings (no dedent — _write_skill handles stripping)
    sections: list[str] = []

    # --- Section 1: Start / Build ---
    if is_cli:
        sections.append(
            "## 1. Build & Verify Installation\n\n"
            "- Package installs cleanly (`pip install -e .` or equivalent)\n"
            "- CLI entry point responds: `<command> --help` shows usage\n"
            "- `<command> --version` shows correct version string"
        )
    elif has_frontend and not has_web:
        sections.append(
            "## 1. Build & Start\n\n"
            "- Build succeeds: `npm run build` completes without errors\n"
            "- Dev server starts: `npm run dev` and serves without errors\n"
            "- Build output contains expected pages (check `dist/` or `build/` directory)"
        )
    else:
        sections.append(
            "## 1. Start the Application\n\n"
            "Start all services and verify no startup errors:\n"
            f"{_test_commands(config)}"
        )

    # --- Section 2: Core verification ---
    if is_cli:
        sections.append(
            "## 2. CLI Command Verification\n\n"
            "Test all core commands with representative inputs:\n"
            f"{functional}\n"
            "- Error cases return non-zero exit codes and helpful messages\n"
            "- Invalid arguments produce clear usage hints\n"
            "- Dry-run mode (if applicable) executes without side effects"
        )
    elif has_web:
        sections.append(
            "## 2. Backend API Verification\n\n"
            "For every API endpoint, make a real HTTP request:\n"
            "- Health check endpoint responds 200\n"
            "- Core CRUD endpoints return correct data\n"
            "- Authentication endpoints work (login/register if applicable)\n"
            "- Error responses return structured JSON, not stack traces\n"
            f"{functional}"
        )
    elif has_frontend and not has_web:
        sections.append(
            "## 2. Page & Feature Verification\n\n"
            "Navigate to each page and verify:\n"
            "- All pages load without console errors or broken assets\n"
            "- Navigation between pages works correctly\n"
            "- Interactive elements respond (buttons, toggles, forms)\n"
            f"{functional}"
        )
    else:
        sections.append(f"## 2. Core Verification\n\n{functional}")

    # --- Section 3: Frontend (only for full-stack projects) ---
    section_num = 3
    if has_frontend and has_web:
        sections.append(
            f"## {section_num}. Frontend Verification\n\n"
            "- Pages load without console errors\n"
            "- Assets serve correctly (CSS, JS, images)\n"
            "- Responsive design works on desktop and mobile viewports\n"
            "- Key user flows work end-to-end through the UI"
        )
        section_num += 1

    # --- Visual verification (only for projects with UI) ---
    if has_frontend:
        sections.append(
            f"## {section_num}. Visual Verification\n\n"
            "Capture full-page screenshots of key pages using Playwright:\n"
            "- `npx playwright screenshot --full-page http://localhost:{port}/path page.png`\n"
            "- Save to `docs/screenshots/smoke-test/`\n"
            "- Use the Read tool to verify visual correctness"
        )
        section_num += 1

    # --- Integration verification ---
    if is_cli:
        sections.append(
            f"## {section_num}. Integration Verification\n\n"
            "- External dependencies reachable (databases, APIs, storage)\n"
            "- End-to-end pipeline: input → processing → output produces correct results\n"
            "- Configuration files parse and validate correctly"
        )
    elif has_frontend and has_web:
        sections.append(
            f"## {section_num}. Integration Verification\n\n"
            "- Database connects and queries return data\n"
            "- Full-stack operations work (frontend → API → database → response)\n"
            "- External service integrations respond (if applicable)"
        )
    elif has_web:
        sections.append(
            f"## {section_num}. Integration Verification\n\n"
            "- Database connects and queries return data\n"
            "- API → service → database round-trips return correct data\n"
            "- External service integrations respond (if applicable)"
        )
    elif has_frontend:
        sections.append(
            f"## {section_num}. Build Output Verification\n\n"
            "- All pages present in build output directory\n"
            "- No broken links between pages\n"
            "- Static assets (images, fonts) included in build\n"
            "- Serverless functions (if any) deploy and respond"
        )

    verify_text = "the CLI tool works correctly with real inputs" if is_cli else \
        "the application actually works from a user perspective" if has_frontend else \
        "the application works end-to-end"

    body = "\n\n".join(sections)

    return dedent(f"""\
    ---
    name: smoke-test
    description: "Run smoke tests to verify the application works end-to-end"
    argument-hint: ""
    ---

    # Smoke Test Protocol

    > {_domain_context(config)}
    > Stack: {stack}

    Verify {verify_text}.

    {body}

    ## Verdict

    Any failure is a **BLOCKER**. Do not mark the iteration complete until all smoke tests pass.
    Report: each test -> PASS/FAIL with evidence.

    $ARGUMENTS
    """)


def _screenshot_review_skill(config: ForgeConfig) -> str:
    stack = _tech_stack_summary(config)
    has_frontend = config.has_frontend_involvement()
    has_web = config.has_web_backend()
    is_cli = config.is_cli_project()
    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    combined = f"{req} {desc}"
    frameworks = [f.lower() for f in config.tech_stack.frameworks]

    # --- CLI projects: generate CLI output review skill ---
    if is_cli:
        # Build domain-specific CLI outputs to capture
        cli_outputs = ["- `<command> --help` — main help text and available subcommands"]
        if "pipeline" in combined or "etl" in combined:
            cli_outputs.append("- `<command> run <sample>` — pipeline execution output with progress")
            cli_outputs.append("- `<command> validate <config>` — configuration validation output")
            cli_outputs.append("- `<command> run --dry-run <sample>` — dry-run output showing planned operations")
        if "plugin" in combined:
            cli_outputs.append("- `<command> plugins list` — installed plugins listing")
        cli_outputs.append("- Error output — invalid arguments, missing files, connection failures")
        cli_outputs.append("- Verbose/debug output — `--verbose` or `--debug` flag output")
        cli_outputs_text = "\n".join(f"   {o}" for o in cli_outputs)

        return dedent(f"""\
        ---
        name: screenshot-review
        description: "Capture and review CLI output for iteration review"
        argument-hint: "[command-or-feature]"
        ---

        # CLI Output Review

        > {_domain_context(config)}
        > Stack: {stack}

        Capture representative CLI outputs for iteration review.

        ## Steps

        1. **Run key commands** and capture output:
    {cli_outputs_text}
        2. **Save outputs** to `docs/cli-outputs/{{{{iteration}}}}/` as `.txt` files
        3. **Review each output** for:
           - Help text is clear and complete (all subcommands, options documented)
           - Output formatting is consistent and readable
           - Error messages are helpful (explain what went wrong and how to fix)
           - Progress indicators work correctly (if applicable)
           - Exit codes are correct (0 for success, non-zero for errors)
        4. **Check README** matches actual CLI behavior: examples run correctly, options are accurate

        ## Output

        Present to Team Leader:
        - Command -> output status (CORRECT / ISSUE) with sample output
        - Any discrepancies between help text and actual behavior
        - Overall CLI usability assessment

        $ARGUMENTS
        """)

    # --- Backend-only API projects: generate API documentation review skill ---
    if not has_frontend:
        # Detect specific API framework for accurate docs reference
        if "fastapi" in frameworks:
            docs_step = "1. **Verify OpenAPI/Swagger docs** are accessible at `/docs` (Swagger UI) and `/redoc` (ReDoc)"
            screenshot_cmd = "npx playwright screenshot --full-page http://localhost:{port}/docs api-docs.png"
        elif "django" in frameworks or "drf" in frameworks:
            docs_step = "1. **Verify API docs** are accessible (DRF browsable API or configured Swagger/drf-spectacular)"
            screenshot_cmd = "npx playwright screenshot --full-page http://localhost:{port}/api/docs api-docs.png"
        else:
            docs_step = "1. **Verify API documentation** is generated and accessible (OpenAPI/Swagger if configured)"
            screenshot_cmd = "npx playwright screenshot --full-page http://localhost:{port}/docs api-docs.png"

        # Domain-specific documentation areas
        doc_areas = []
        if "auth" in combined:
            doc_areas.append("- Authentication: login/register flows, token refresh, permission levels")
        if "transaction" in combined or "payment" in combined:
            doc_areas.append("- Transaction/payment: request schemas, idempotency keys, error codes")
        if "audit" in combined or "compliance" in combined:
            doc_areas.append("- Audit/compliance: logging endpoints, data retention policies")
        if "webhook" in combined:
            doc_areas.append("- Webhooks: event types, payload schemas, retry policies")
        doc_areas_text = "\n".join(f"   {d}" for d in doc_areas)
        domain_section = f"\n\n    ## Domain-Specific Documentation\n\n{doc_areas_text}" if doc_areas else ""

        return dedent(f"""\
        ---
        name: screenshot-review
        description: "Review API documentation and developer-facing interfaces"
        argument-hint: "[endpoint-or-feature]"
        ---

        # API Documentation Review

        > {_domain_context(config)}
        > Stack: {stack}

        Review API documentation and developer-facing interfaces for completeness and accuracy.

        ## Steps

        {docs_step}
        2. **Review endpoint documentation**: all endpoints listed, request/response schemas accurate, error codes documented
        3. **Test example requests** from docs: copy a curl command, verify it works against the running API
        4. **Check README**: setup instructions complete, environment variables documented, API usage examples provided
        5. **Capture screenshots** of API docs UI if available:
           - `{screenshot_cmd}`
           - Save to `docs/screenshots/{{{{iteration}}}}/`
        6. **Compile summary**: List each endpoint group with documentation status (complete / missing / outdated)
        {domain_section}
        ## API Documentation Criteria

        - Every endpoint has a description and example request/response
        - Authentication requirements clearly documented per endpoint
        - Error response schemas documented with status codes and messages
        - Rate limiting documented (if applicable)
        - Webhook payloads documented (if applicable)

        ## Output

        Present to Team Leader:
        - Endpoint group -> documentation status (COMPLETE / PARTIAL / MISSING)
        - Any discrepancies between docs and actual API behavior
        - Overall API documentation quality assessment

        $ARGUMENTS
        """)

    # Build domain-specific pages to capture
    pages = []
    pages.append("- Home / Landing page")
    if "auth" in combined or "login" in combined:
        pages.append("- Login page")
        pages.append("- Registration page")
        pages.append("- User profile / account settings")
    if "product" in combined or "catalog" in combined:
        pages.append("- Product listing / catalog page")
        pages.append("- Product detail page")
    if "cart" in combined or "shopping" in combined:
        pages.append("- Shopping cart (empty and populated states)")
    if "checkout" in combined or "payment" in combined:
        pages.append("- Checkout flow (each step)")
    if "dashboard" in combined or "admin" in combined:
        pages.append("- Dashboard / admin panel")
    if "search" in combined:
        pages.append("- Search results page")
    if "chat" in combined or "message" in combined:
        pages.append("- Chat / messaging interface (with messages and @mentions)")
    if "kanban" in combined or "board" in combined or "task" in combined:
        pages.append("- Kanban / task board (empty board, board with cards across columns)")
        pages.append("- Task detail / edit view (with assignments, due dates, priority)")
    if "notification" in combined:
        pages.append("- Notification dropdown / notification settings")
    if "activity" in combined or "feed" in combined:
        pages.append("- Activity feed / timeline view")
    if "upload" in combined or "file" in combined or "attachment" in combined:
        pages.append("- File attachment views (upload interface, attachment preview)")
    if "team" in combined and ("member" in combined or "roster" in combined or "manage" in combined):
        pages.append("- Team management / member list page")
    # HR-specific pages
    if "employee" in combined or "hr" in combined:
        pages.append("- Employee directory / profile page")
    if "payroll" in combined:
        pages.append("- Payroll dashboard (salary, deductions, tax breakdown)")
    if "leave" in combined and ("management" in combined or "tracking" in combined or "pto" in combined):
        pages.append("- Leave management (request form, approval queue, balance view)")
    if "org" in combined and ("chart" in combined or "hierarchy" in combined):
        pages.append("- Org chart visualization (hierarchy, reporting structure)")
    if "performance review" in combined:
        pages.append("- Performance review interface (form, rating, feedback)")
    if "document" in combined and ("management" in combined or "upload" in combined):
        pages.append("- Document management (upload, listing, preview)")
    if "sso" in combined or "saml" in combined:
        pages.append("- SSO login page / IdP selection")
    # E-commerce vendor pages
    if "vendor" in combined and ("onboard" in combined or "storefront" in combined or "dashboard" in combined):
        pages.append("- Vendor dashboard (sales analytics, orders, payouts)")
        pages.append("- Vendor storefront / onboarding flow")
    if "order" in combined and ("management" in combined or "tracking" in combined):
        pages.append("- Order management / order detail page")
    if "inventory" in combined:
        pages.append("- Inventory management view")
    if "review" in combined and "rating" in combined:
        pages.append("- Product reviews / ratings display")
    if "reporting" in combined or ("report" in combined and "chart" in combined):
        pages.append("- Reporting dashboard with charts and metrics")
    if not any(k in combined for k in ("auth", "product", "cart", "dashboard", "chat", "kanban", "task", "board", "employee", "payroll", "vendor", "order")):
        pages.append("- All user-facing pages identified from the project")

    pages_text = "\n".join(f"   {p}" for p in pages)

    # Domain-specific state variants
    states = ["- Default/loaded state (with representative data)", "- Empty state (no data)"]
    if "auth" in combined:
        states.append("- Authenticated vs. anonymous user views")
    if "cart" in combined:
        states.append("- Empty cart vs. populated cart")
    if "error" in combined or "payment" in combined:
        states.append("- Error state (validation errors, failed operations)")
    if "real-time" in combined or "websocket" in combined or "chat" in combined:
        states.append("- Real-time update in progress (live data arriving, typing indicators)")
    if "kanban" in combined or "board" in combined or "drag" in combined:
        states.append("- Drag-and-drop in progress (card being moved between columns)")
    if "notification" in combined:
        states.append("- Notification states (unread badge, notification list, empty notifications)")
    if "payroll" in combined or "financial" in combined:
        states.append("- Currency/number formatting (salary figures, tax calculations, decimal precision)")
    if "employee" in combined or "hr" in combined:
        states.append("- Different role views (admin vs. manager vs. employee)")
    if "leave" in combined and ("approval" in combined or "workflow" in combined):
        states.append("- Approval workflow states (pending, approved, rejected)")
    if "vendor" in combined:
        states.append("- Vendor vs. customer vs. admin views")
    if "inventory" in combined:
        states.append("- Low stock / out of stock states")
    states.append("- Loading state (if capturable)")

    states_text = "\n".join(f"       {s}" for s in states)

    return dedent(f"""\
    ---
    name: screenshot-review
    description: "Capture and review screenshots of all key UI pages for iteration review"
    argument-hint: "[url-or-feature]"
    ---

    # Screenshot Review

    > {_domain_context(config)}
    > Stack: {stack}

    Capture a visual summary of the application's current state for iteration review.

    ## Steps

    1. **Start the application** if not already running
    2. **Key pages to capture** ({config.project.description}):
{pages_text}
    3. **Capture screenshots** using Playwright:
       - Desktop viewport (1280x720): `npx playwright screenshot --full-page http://localhost:{{port}}/path page-desktop.png`
       - Mobile viewport (375x812): `npx playwright screenshot --full-page --viewport-size=375,812 http://localhost:{{port}}/path page-mobile.png`
    4. **Capture state variants** for key pages:
{states_text}
    5. **Save all screenshots** to `docs/screenshots/{{iteration}}/`
    6. **View each screenshot** using the Read tool — verify visual correctness
    7. **Compile summary**: List each page with its screenshot path and visual assessment

    ## Visual Correctness Criteria

    - Layout renders correctly (no overlapping elements, proper spacing)
    - Text is readable and not truncated
    - Interactive elements are visually distinct (buttons, links, inputs)
    - Responsive design works on both desktop and mobile viewports
    - Data displays correctly (numbers, dates, currency formatted properly)
    - Images and media load without broken references

    ## Output

    Present to Team Leader:
    - Page name -> screenshot path -> visual status (OK / ISSUE)
    - Any visual issues found with description
    - Overall visual quality assessment

    This helps the human understand what was built without starting the app themselves.

    $ARGUMENTS
    """)


def _pr_workflow_skill(config: ForgeConfig) -> str:
    agents = _agents_list(config)
    stack = _tech_stack_summary(config)

    if config.atlassian.enabled:
        project_key = config.atlassian.jira_project_key or "PROJ"
        ref_step = f"""
    4. **Reference Jira ticket** in the PR description: `Closes {project_key}-<number>`
    5. **Verify branch name** follows convention: `<type>-{project_key}-<N>-<description>`"""
    else:
        ref_step = """
    4. **Reference task ID** in the PR description
    5. **Verify branch name** follows convention: `<type>/<agent-name>/<task-id>-<description>`"""

    # Domain-specific PR testing guidance
    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    pr_combined = f"{req} {desc}"
    domain_test_lines = []
    if "auth" in pr_combined:
        domain_test_lines.append("- Auth changes: verify login/logout and user sessions work")
    if "cart" in pr_combined or "checkout" in pr_combined:
        domain_test_lines.append("- Cart/checkout changes: test full purchase flow end-to-end")
    if "product" in pr_combined or "catalog" in pr_combined:
        domain_test_lines.append("- Product changes: verify product display and search")
    if "real-time" in pr_combined or "websocket" in pr_combined or "chat" in pr_combined:
        domain_test_lines.append("- Real-time changes: verify WebSocket connectivity and live updates")
    if "kanban" in pr_combined or "board" in pr_combined or "task" in pr_combined:
        domain_test_lines.append("- Board/task changes: verify drag-and-drop, task state transitions")
    if "notification" in pr_combined or "email" in pr_combined:
        domain_test_lines.append("- Notification changes: verify delivery and rendering")
    if "upload" in pr_combined or "file" in pr_combined or "attachment" in pr_combined:
        domain_test_lines.append("- File changes: verify upload, validation, and retrieval")
    domain_test_text = "\n".join(f"   {l}" for l in domain_test_lines)
    domain_section = f"\n\n    **Domain-specific testing** (run if your changes touch these areas):\n{domain_test_text}" if domain_test_lines else ""

    gh_auth_note = ""
    if config.has_ssh_auth():
        gh_auth_note = dedent("""\

        ## Authentication Note

        Git push uses SSH (`core.sshCommand` in `.git/config`). Ensure `GH_TOKEN` is
        exported before running `gh pr create`.

        """)

    return dedent(f"""\
    ---
    name: create-pr
    description: "Create a Pull Request following the team's workflow conventions"
    argument-hint: "<target-branch> [title]"
    ---

    # Create Pull Request

    > {_domain_context(config)}
    > Stack: {stack}

    Create a PR following the team's workflow conventions.
    {gh_auth_note}
    ## Pre-PR Checklist

    Run before creating the PR:
{_test_commands(config)}{domain_section}

    ## Steps

    1. **Verify all changes are committed** and pushed to the remote branch
    2. **Run tests** locally — ensure they pass before creating the PR
    3. **Create the PR** using `gh pr create` with:
       - Clear, descriptive title referencing the feature/fix
       - Summary of changes in the description
       - Target branch (parent feature branch or default branch){ref_step}
    6. **Request review** from appropriate agents:
{_pr_reviewer_routing(config)}
    7. **Wait for approval** — at least one approval required before merge

    ## PR Size Guidelines ({config.mode.value} mode)

    - **Big PRs** (new features, cross-cutting changes): reviewer should test the feature end-to-end
    - **Small PRs** (docs, config, bug fixes): code review is sufficient

    ## Team Agents

    Available reviewers: {agents}

    $ARGUMENTS
    """)


def _release_management_skill(config: ForgeConfig) -> str:
    stack = _tech_stack_summary(config)
    is_cli = config.is_cli_project()
    has_frontend = config.has_frontend_involvement()
    has_web = config.has_web_backend()
    frameworks = [f.lower() for f in config.tech_stack.frameworks]

    release_auth_note = ""
    if config.has_ssh_auth():
        release_auth_note = dedent("""\

        ## Authentication

        Ensure `GH_TOKEN` is set before `gh release create`. Git push uses SSH.

        """)

    confluence_step = ""
    if config.atlassian.enabled:
        confluence_step = """
    5. **Update Confluence** release notes page with the release summary
    6. **Update Jira** — mark the release version as released, move remaining tickets to next version"""

    # Domain-specific pre-release checks
    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    combined = f"{req} {desc}"
    domain_checks: list[str] = []
    if "auth" in combined:
        domain_checks.append("- Authentication flows verified (login, register, logout, token refresh)")
    if "payment" in combined or "checkout" in combined:
        domain_checks.append("- Payment/checkout flow tested end-to-end")
    if "cart" in combined or "shopping" in combined:
        domain_checks.append("- Cart operations verified (add, remove, update, persist)")
    if "transaction" in combined or "ledger" in combined:
        domain_checks.append("- Transaction processing verified (create, validate, reconcile)")
    if "audit" in combined or "compliance" in combined:
        domain_checks.append("- Audit trail integrity verified (immutable records, no data leakage)")
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        domain_checks.append(f"- Database ({dbs}) migrations verified (up and down)")

    # Project-type-specific checks
    if is_cli:
        domain_checks.append("- CLI installs cleanly and `--help` / `--version` work")
        domain_checks.append("- All subcommands execute successfully with sample inputs")
        if "plugin" in combined:
            domain_checks.append("- Plugin loading and discovery works correctly")
    elif has_frontend and not has_web:
        # Static site
        domain_checks.append("- Build output is complete and deployable")
        if "astro" in frameworks:
            domain_checks.append("- `npm run build` succeeds with no warnings")
        if "vercel" in combined:
            domain_checks.append("- Vercel deployment preview is healthy and all pages load")
    elif has_web:
        domain_checks.append("- API health endpoint responds after deployment")
        if "go" in [l.lower() for l in config.tech_stack.languages]:
            domain_checks.append("- Go services build and start successfully")

    domain_checks_text = "\n".join(f"    {c}" for c in domain_checks) if domain_checks else ""
    domain_section = f"\n{domain_checks_text}" if domain_checks_text else ""

    # Post-release section varies by project type
    if is_cli:
        post_release = dedent("""\
        ## Post-Release

        - Verify package installs from release artifacts
        - Test CLI commands work with the released version
        - If critical issues found: yank release and publish patch""")
    elif has_frontend and not has_web:
        post_release = dedent("""\
        ## Post-Release

        - Verify deployment is live and all pages load correctly
        - Check for broken links, missing assets, or rendering issues
        - Monitor error tracking for any client-side errors
        - If critical issues found: rollback deployment to previous version""")
    else:
        post_release = dedent("""\
        ## Post-Release

        - Verify deployment is healthy (check application responds, no error spikes)
        - Monitor for 15 minutes after deploy for regressions
        - If critical issues found: rollback with `git revert` or deploy previous tag""")

    return dedent(f"""\
    ---
    name: release
    description: "Create a GitHub release with tag and release notes"
    argument-hint: "<version-tag> [title]"
    ---

    # Release Management

    > {_domain_context(config)}
    > Stack: {stack}

    Create a GitHub release after a major milestone.
    {release_auth_note}
    ## Pre-Release Verification

    Before releasing, verify:
{_test_commands(config)}
    - All smoke tests pass (use /smoke-test skill)
    - Current iteration is verified and tagged{domain_section}

    ## Steps

    1. **Verify readiness**: All tests pass, smoke tests pass, iteration is verified
    2. **Create git tag**: `git tag v<version>` (e.g., `v1.0.0`, `v0.1.0-alpha`)
    3. **Push tag**: `git push origin v<version>`
    4. **Create GitHub release**: `gh release create v<version> --generate-notes --title "<title>"`{confluence_step}

    {post_release}

    ## Version Numbering

    - Major releases: `v1.0.0`, `v2.0.0` — breaking changes or major milestones
    - Minor releases: `v1.1.0`, `v1.2.0` — new features
    - Patch releases: `v1.0.1`, `v1.0.2` — bug fixes

    $ARGUMENTS
    """)


def _arch_review_skill(config: ForgeConfig) -> str:
    stack = _tech_stack_summary(config)
    langs = [l.lower() for l in config.tech_stack.languages]
    frameworks = [f.lower() for f in config.tech_stack.frameworks]
    is_cli = config.is_cli_project()
    has_frontend = config.has_frontend_involvement()
    has_web = config.has_web_backend()
    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    combined = f"{req} {desc}"

    # Build tech-specific review points
    review_points: list[str] = []
    point_num = 1

    # 1. Abstractions (always relevant)
    if is_cli:
        review_points.append(dedent(f"""\
    {point_num}. **Plugin/extension architecture**: External deps behind abstractions?
       - I/O operations (file, network, database) behind Protocol/ABC interfaces
       - Plugin contracts well-defined with clear extension points
       - Core processing logic imports only abstractions, never concrete SDKs"""))
    elif has_frontend and not has_web:
        review_points.append(dedent(f"""\
    {point_num}. **Component architecture**: Clean boundaries between components?
       - Components are self-contained with clear props/interfaces
       - External services (APIs, storage) behind abstractions
       - Shared state managed centrally, not passed through deep prop chains"""))
    else:
        review_points.append(dedent(f"""\
    {point_num}. **Vendor-agnostic interfaces**: External deps behind abstractions?
       - Database repositories behind Protocol/ABC interfaces
       - HTTP clients behind service interfaces
       - Core business logic imports only abstractions, never concrete SDKs"""))
    point_num += 1

    # 2. Layer separation (framework-specific)
    if is_cli:
        cli_fw = "Click" if "click" in frameworks else "Typer" if "typer" in frameworks else "CLI"
        review_points.append(dedent(f"""\
    {point_num}. **Layer separation** ({cli_fw}):
       - CLI commands only handle argument parsing, delegate to services
       - Processing logic separate from I/O (file reading, network calls)
       - Configuration loading separate from business logic
       - Domain models free of CLI framework dependencies"""))
    elif "fastapi" in frameworks and has_frontend:
        fe_fw = "Next.js" if any(f in frameworks for f in ("nextjs", "next.js", "next")) else "React"
        review_points.append(dedent(f"""\
    {point_num}. **Layer separation** (Full-stack: FastAPI + {fe_fw}):
       - FastAPI: routes only handle request/response, delegate to services
       - {fe_fw}: components focus on UI, business logic in custom hooks/services
       - Domain models free of framework dependencies
       - Dependency injection used for services"""))
    elif "django" in frameworks or "drf" in frameworks:
        review_points.append(dedent(f"""\
    {point_num}. **Layer separation** (Django):
       - Views only handle request/response, delegate to services
       - Models contain data logic, not business orchestration
       - Serializers validate input, don't contain business logic
       - Dependency injection used for external services"""))
    elif "go" in langs:
        review_points.append(dedent(f"""\
    {point_num}. **Layer separation** (Go microservices):
       - Handlers only handle request/response, delegate to services
       - Domain models separate from transport layer
       - Repository pattern for data access
       - Interface-based dependency injection"""))
    elif "fastapi" in frameworks or ("python" in langs and has_web):
        review_points.append(dedent(f"""\
    {point_num}. **Layer separation** (Python API):
       - Routes only handle request/response, delegate to services
       - Domain models free of framework dependencies
       - Dependency injection used for services"""))
    elif has_frontend and "astro" in frameworks:
        review_points.append(dedent(f"""\
    {point_num}. **Layer separation** (Astro + React islands):
       - Astro pages handle layout and static content
       - React islands encapsulate interactive components
       - Shared utilities and types in dedicated modules
       - Content (MDX/markdown) separate from presentation"""))
    elif has_frontend:
        review_points.append(dedent(f"""\
    {point_num}. **Layer separation**:
       - Components focus on UI, business logic in custom hooks/services
       - Proper separation of concerns between components and state management"""))
    else:
        review_points.append(dedent(f"""\
    {point_num}. **Layer separation**: Business logic separate from transport/persistence?"""))
    point_num += 1

    # 3. API/interface contracts (skip for pure static sites)
    if has_web or is_cli:
        if is_cli:
            review_points.append(dedent(f"""\
    {point_num}. **CLI contract compliance**: Commands match defined specifications?
       - All documented subcommands and options implemented
       - Exit codes follow conventions (0 success, 1 error, 2 usage error)
       - Output formats consistent (JSON, table, plain text as documented)"""))
        else:
            review_points.append(dedent(f"""\
    {point_num}. **API contract compliance**: Endpoints match the defined contracts?
       - Request/response schemas match API specs
       - Proper HTTP status codes and error responses"""))
        point_num += 1

    # 4. Error handling
    if is_cli:
        review_points.append(dedent(f"""\
    {point_num}. **Error handling**: Consistent error reporting?
       - Errors print to stderr, not stdout
       - Error messages include actionable guidance
       - No stack traces in normal error output (only with --debug)"""))
    else:
        review_points.append(dedent(f"""\
    {point_num}. **Error handling**: Consistent error format, no leaked internals?
       - No database errors, stack traces, or internal service names exposed to clients
       - Structured error responses with user-friendly messages"""))
    point_num += 1

    # 5. Security (domain-specific, skip for pure static sites with no forms)
    if has_web or is_cli or "form" in combined or "auth" in combined:
        security_checks = _security_checks(config)
        review_points.append(f"""\
    {point_num}. **Security** (domain-specific):
{security_checks}""")
        point_num += 1

    # 6. Database (only if databases configured)
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        review_points.append(dedent(f"""\
    {point_num}. **Database** ({dbs}):
       - Query efficiency (avoid N+1, proper indexing)
       - Migrations are reversible
       - Schema constraints enforced at database level
       - Connection pooling configured"""))
        point_num += 1

    # 7. Code organization (always relevant)
    review_points.append(dedent(f"""\
    {point_num}. **Code organization**: Follows project structure conventions?
       - Proper module/package separation
       - Consistent import patterns
       - No circular dependencies"""))
    point_num += 1

    # 8. Domain-specific architecture
    domain_checks: list[str] = []
    if "cart" in combined or "checkout" in combined or "e-commerce" in combined or "ecommerce" in combined:
        domain_checks.append("- Cart state management (persistence across sessions)")
        domain_checks.append("- Order processing workflow (state machine pattern)")
        domain_checks.append("- Inventory management (race condition prevention)")
    if "real-time" in combined or "websocket" in combined:
        domain_checks.append("- WebSocket connection lifecycle management")
        domain_checks.append("- Real-time state synchronization strategy")
    if "auth" in combined:
        domain_checks.append("- Authentication flow architecture (token refresh, session management)")
    if "pipeline" in combined or "etl" in combined:
        domain_checks.append("- Pipeline execution model (streaming vs batch, error recovery)")
        domain_checks.append("- Plugin loading and discovery mechanism")
        domain_checks.append("- Data validation between pipeline stages")
    if "microservice" in combined:
        domain_checks.append("- Service communication patterns (sync vs async, retries)")
        domain_checks.append("- Data consistency across services (saga, eventual consistency)")
    if "payroll" in combined or "hr" in combined:
        domain_checks.append("- Sensitive data handling (PII encryption, audit trails)")
        domain_checks.append("- Calculation engine architecture (payroll, tax)")
    if "sso" in combined or "saml" in combined or "oidc" in combined:
        domain_checks.append("- SSO integration architecture (SAML/OIDC flow)")
    if "static" in combined and "site" in combined:
        domain_checks.append("- Build-time vs runtime content strategy")
        domain_checks.append("- Asset optimization pipeline (images, fonts, CSS)")
    if "blog" in combined or "mdx" in combined or "markdown" in combined:
        domain_checks.append("- Content management architecture (MDX/markdown processing)")
    if domain_checks:
        domain_text = "\n".join(f"   {c}" for c in domain_checks)
        review_points.append(f"""\
    {point_num}. **Domain architecture** ({config.project.description}):
{domain_text}""")

    points_text = "\n".join(review_points)

    return dedent(f"""\
    ---
    name: arch-review
    description: "Review code for architecture compliance"
    argument-hint: "<file-or-directory>"
    ---

    # Architecture Review

    > {_domain_context(config)}
    > Stack: {stack}

    Review the specified code for architecture compliance.

    ## Checklist

{points_text}

    ## Priority by Mode ({config.mode.value})

    - **P0 (BLOCKER)**: Security vulnerabilities, broken abstractions, data loss risks
    - **P1 (WARNING)**: Missing validations, poor error handling, performance concerns
    - **P2 (NOTE)**: Code style, better patterns, documentation gaps

    Include specific file and line references for each finding.

    $ARGUMENTS
    """)
