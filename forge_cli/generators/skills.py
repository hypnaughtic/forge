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
    cmds = []
    langs = [l.lower() for l in config.tech_stack.languages]
    frameworks = [f.lower() for f in config.tech_stack.frameworks]

    if "python" in langs or "fastapi" in frameworks:
        cmds.append("- Backend (Python/FastAPI): `pytest` and verify server starts with `uvicorn`")
    if "typescript" in langs or "javascript" in langs or "react" in frameworks or "nextjs" in frameworks:
        cmds.append("- Frontend (TypeScript/React): `npm test` and `npm run build`")
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        cmds.append(f"- Database ({dbs}): verify migrations apply cleanly")
    return "\n".join(cmds) if cmds else "- Run project test suite"


def _quality_gate_checks(config: ForgeConfig) -> str:
    """Generate quality gate checks based on tech stack and mode."""
    checks = []
    langs = [l.lower() for l in config.tech_stack.languages]
    frameworks = [f.lower() for f in config.tech_stack.frameworks]

    if "react" in frameworks or "typescript" in langs:
        checks.append("- TypeScript compilation successful with no errors?")
        checks.append("- React dev server starts and renders without console errors?")
    if "fastapi" in frameworks or "python" in langs:
        checks.append("- FastAPI server starts and health endpoint responds?")
        checks.append("- Python tests pass (`pytest`)?")
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        checks.append(f"- Database ({dbs}) migrations applied successfully?")
    checks.append(f"- Coverage meets {config.mode.value} threshold?")
    return "\n".join(f"   {c}" for c in checks) if checks else "   - All tests pass?"


def _functional_checks(config: ForgeConfig) -> str:
    """Generate functional verification checks from project requirements."""
    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    combined = f"{req} {desc}"
    checks = []

    if "auth" in combined:
        checks.append("- User authentication flows working (registration, login, logout)?")
    if "product" in combined or "catalog" in combined:
        checks.append("- Product catalog functionality complete (browse, search, filter)?")
    if "cart" in combined or "shopping" in combined:
        checks.append("- Shopping cart operations functional (add, remove, update quantities)?")
    if "checkout" in combined or "payment" in combined:
        checks.append("- Checkout/payment process works end-to-end?")
    if "api" in combined or "rest" in combined:
        checks.append("- API endpoints respond correctly with proper status codes?")
    if "real-time" in combined or "websocket" in combined or "chat" in combined:
        checks.append("- Real-time features (WebSocket/chat) connect and deliver messages?")
    if "dashboard" in combined or "admin" in combined:
        checks.append("- Dashboard/admin views render and display correct data?")
    if "search" in combined:
        checks.append("- Search functionality returns relevant results?")
    if "notification" in combined or "email" in combined:
        checks.append("- Notification/email system delivers messages?")
    if "upload" in combined or "file" in combined or "image" in combined:
        checks.append("- File upload/media handling works correctly?")

    if not checks:
        checks.append("- Core feature requirements from project spec are functional?")

    return "\n".join(f"   {c}" for c in checks)


def _domain_context(config: ForgeConfig) -> str:
    """Build a domain context block from project description and requirements."""
    return (
        f"**Project**: {config.project.description}\n"
        f"    **Requirements**: {config.project.requirements}\n"
        f"    **Mode**: {config.mode.value} | **Strategy**: {config.strategy.value}"
    )


def _security_checks(config: ForgeConfig) -> str:
    """Generate domain-specific security checks."""
    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    combined = f"{req} {desc}"
    checks = []

    if "auth" in combined:
        checks.append("- Authentication: JWT/session validation on protected endpoints")
        checks.append("- Password hashing uses bcrypt/argon2, never plaintext")
    if "payment" in combined or "checkout" in combined:
        checks.append("- Payment data: no card numbers stored in plain text")
        checks.append("- Checkout flow: CSRF protection on state-changing operations")
    if "user" in combined:
        checks.append("- User data: input validation on all user-facing forms")
        checks.append("- Authorization: users can only access their own resources")
    checks.append("- No API keys, passwords, or tokens in source code")
    checks.append("- SQL injection prevention: parameterized queries only")

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
{_functional_checks(config)}
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
{_functional_checks(config)}
    5. **Run smoke test** (use /smoke-test skill)
    6. **Decision**: PROCEED | REWORK | ROLLBACK | ESCALATE

    If PROCEED: tag the iteration as verified, plan next iteration.
    If REWORK: route issues to specific agents:
      - Backend/API issues -> backend-developer
      - Frontend/UI issues -> frontend-engineer
      - Test failures -> qa-engineer
      - Infrastructure -> devops-specialist
      - Architecture concerns -> architect
    If ROLLBACK: restore last verified tag, ensure database rollback scripts are safe.
    If ESCALATE: present situation to human with trade-off options and timeline impact.

    $ARGUMENTS
    """)


def _spawn_agent_skill(config: ForgeConfig) -> str:
    agents = config.get_active_agents()
    agent_list = "\n".join(f"    - `{a}`" for a in agents)
    stack = _tech_stack_summary(config)
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
    return dedent(f"""\
    ---
    name: jira-update
    description: "Update a Jira ticket with current progress"
    argument-hint: "<ticket-key> <status> <comment>"
    ---

    # Jira Ticket Update

    Update a Jira ticket using the Atlassian MCP tool.

    **Ticket key**: e.g., {config.atlassian.jira_project_key or 'PROJ'}-123
    **Status transitions**: To Do -> In Progress -> In Review -> Testing -> Done

    Steps:
    1. Parse $ARGUMENTS for ticket key, new status, and comment
    2. Use the Atlassian MCP tool to transition the ticket status
    3. Add a comment with the provided text, signed with your agent name
    4. If the ticket doesn't exist, report back — don't create it without Team Leader approval

    $ARGUMENTS
    """)


def _sprint_report_skill(config: ForgeConfig) -> str:
    return dedent(f"""\
    ---
    name: sprint-report
    description: "Generate a sprint report from Jira and present it"
    argument-hint: ""
    ---

    # Sprint Report

    Generate a sprint status report using Jira data.

    1. Fetch current sprint from Jira project {config.atlassian.jira_project_key or '[project key]'}
    2. Collect all tickets in the sprint
    3. Summarize:
       - **Completed**: tickets done this sprint
       - **In Progress**: tickets being worked on (and by which agent)
       - **Blocked**: tickets that are blocked
       - **To Do**: tickets not yet started
       - **Velocity**: story points completed vs committed
    4. Present a clean formatted report

    $ARGUMENTS
    """)


def _smoke_test_skill(config: ForgeConfig) -> str:
    stack = _tech_stack_summary(config)
    return dedent(f"""\
    ---
    name: smoke-test
    description: "Run smoke tests to verify the application works end-to-end"
    argument-hint: ""
    ---

    # Smoke Test Protocol

    > {_domain_context(config)}
    > Stack: {stack}

    Verify the application actually works from a user's perspective.

    ## 1. Start the Application

    Start all services and verify no startup errors:
{_test_commands(config)}

    ## 2. Backend Verification

    For every API endpoint, make a real HTTP request:
    - Health check endpoint responds 200
    - Core CRUD endpoints return correct data
    - Authentication endpoints work (login/register if applicable)
    - Error responses return structured JSON, not stack traces

    ## 3. Frontend Verification

    - Pages load without console errors
    - Assets serve correctly (CSS, JS, images)
    - Key user flows work end-to-end:
{_functional_checks(config)}

    ## 4. Visual Verification

    Capture full-page screenshots of all UI pages using Playwright:
    - `npx playwright screenshot --full-page http://localhost:{{port}}/path page.png`
    - Save to `docs/screenshots/smoke-test/`
    - Use the Read tool to verify visual correctness

    ## 5. Integration Verification

    - Database connects and queries return data
    - Full-stack operations work (frontend -> API -> database -> response)
    - External service integrations respond (if applicable)

    ## Verdict

    Any failure is a **BLOCKER**. Do not mark the iteration complete until all smoke tests pass.
    Report: each test -> PASS/FAIL with evidence.

    $ARGUMENTS
    """)


def _screenshot_review_skill(config: ForgeConfig) -> str:
    stack = _tech_stack_summary(config)
    req = config.project.requirements.lower()
    desc = config.project.description.lower()
    combined = f"{req} {desc}"

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
        pages.append("- Chat / messaging interface")
    if not any(k in combined for k in ("auth", "product", "cart", "dashboard", "chat")):
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
    domain_test_lines = []
    if "auth" in req:
        domain_test_lines.append("- Auth changes: verify login/logout and user sessions work")
    if "cart" in req or "checkout" in req:
        domain_test_lines.append("- Cart/checkout changes: test full purchase flow end-to-end")
    if "product" in req or "catalog" in req:
        domain_test_lines.append("- Product changes: verify product display and search")
    domain_test_text = "\n".join(f"   {l}" for l in domain_test_lines)
    domain_section = f"\n    3. **Test domain-specific flows** relevant to your changes:\n{domain_test_text}" if domain_test_lines else ""

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
       - Architecture/cross-cutting changes: architect + team-leader
       - Backend changes: backend-developer or team-leader
       - Frontend changes: frontend-engineer or team-leader
       - Infrastructure: devops-specialist + team-leader
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

    confluence_step = ""
    if config.atlassian.enabled:
        confluence_step = """
    5. **Update Confluence** release notes page with the release summary
    6. **Update Jira** — mark the release version as released, move remaining tickets to next version"""

    # Domain-specific pre-release checks
    req = config.project.requirements.lower()
    domain_checks = []
    if "auth" in req:
        domain_checks.append("- Authentication flows verified (login, register, logout, token refresh)")
    if "payment" in req or "checkout" in req:
        domain_checks.append("- Payment/checkout flow tested end-to-end")
    if "cart" in req or "shopping" in req:
        domain_checks.append("- Cart operations verified (add, remove, update, persist)")
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        domain_checks.append(f"- Database ({dbs}) migrations verified (up and down)")
    domain_checks_text = "\n".join(f"    {c}" for c in domain_checks) if domain_checks else ""
    domain_section = f"\n{domain_checks_text}" if domain_checks_text else ""

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

    ## Post-Release

    - Verify deployment is healthy (check application responds, no error spikes)
    - Monitor for 15 minutes after deploy for regressions
    - If critical issues found: rollback with `git revert` or deploy previous tag

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

    # Build tech-specific review points
    review_points = []

    review_points.append(dedent("""\
    1. **Vendor-agnostic interfaces**: External deps behind abstractions?
       - Database repositories behind Protocol/ABC interfaces
       - HTTP clients behind service interfaces
       - Core business logic imports only abstractions, never concrete SDKs"""))

    if "fastapi" in frameworks and "react" in frameworks:
        review_points.append(dedent("""\
    2. **Layer separation** (Full-stack):
       - FastAPI: routes only handle request/response, delegate to services
       - React: components focus on UI, business logic in custom hooks/services
       - Domain models free of framework dependencies
       - Dependency injection used for services"""))
    elif "fastapi" in frameworks or "python" in langs:
        review_points.append(dedent("""\
    2. **Layer separation** (FastAPI/Python):
       - Routes only handle request/response, delegate to services
       - Domain models free of framework dependencies
       - Dependency injection used for services"""))
    elif "react" in frameworks or "typescript" in langs:
        review_points.append(dedent("""\
    2. **Layer separation** (React/TypeScript):
       - Components focus on UI, business logic in custom hooks/services
       - Proper separation of concerns between components and state management"""))
    else:
        review_points.append(dedent("""\
    2. **Layer separation**: Business logic separate from transport/persistence?"""))

    review_points.append(dedent("""\
    3. **API contract compliance**: Endpoints match the defined contracts?
       - Request/response schemas match API specs
       - Proper HTTP status codes and error responses"""))

    review_points.append(dedent("""\
    4. **Error handling**: Consistent error format, no leaked internals?
       - No database errors, stack traces, or internal service names exposed to clients
       - Structured error responses with user-friendly messages"""))

    # Security with domain-specific checks
    security_checks = _security_checks(config)
    review_points.append(f"""\
    5. **Security** (domain-specific):
{security_checks}""")

    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        review_points.append(dedent(f"""\
    6. **Database** ({dbs}):
       - Query efficiency (avoid N+1, proper indexing)
       - Migrations are reversible
       - Schema constraints enforced at database level
       - Connection pooling configured"""))

    review_points.append(dedent("""\
    7. **Code organization**: Follows project structure conventions?
       - Proper module/package separation
       - Consistent import patterns
       - No circular dependencies"""))

    # Domain-specific architecture
    req = config.project.requirements.lower()
    domain_checks = []
    if "cart" in req or "checkout" in req or "e-commerce" in req or "ecommerce" in req:
        domain_checks.append("- Cart state management (persistence across sessions)")
        domain_checks.append("- Order processing workflow (state machine pattern)")
        domain_checks.append("- Inventory management (race condition prevention)")
    if "real-time" in req or "websocket" in req:
        domain_checks.append("- WebSocket connection lifecycle management")
        domain_checks.append("- Real-time state synchronization strategy")
    if "auth" in req:
        domain_checks.append("- Authentication flow architecture (token refresh, session management)")
    if domain_checks:
        domain_text = "\n".join(f"   {c}" for c in domain_checks)
        review_points.append(f"""\
    8. **Domain architecture** ({config.project.description}):
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
