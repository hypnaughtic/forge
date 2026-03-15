"""Generate reusable skills for .claude/skills/ directory."""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

from forge_cli.config_schema import ForgeConfig


def generate_skills(
    config: ForgeConfig,
    skills_dir: Path,
    on_progress: object | None = None,
) -> None:
    """Generate reusable skill files based on project configuration.

    Args:
        config: Forge configuration.
        skills_dir: Directory to write skill files to.
        on_progress: Optional callback(detail=str, files_done=int) for progress updates.
    """
    skills_dir.mkdir(parents=True, exist_ok=True)
    files_done = 0

    def _emit(name: str) -> None:
        nonlocal files_done
        files_done += 1
        if on_progress and callable(on_progress):
            on_progress(detail=name, files_done=files_done)

    # Always generate status skill
    _write_skill(skills_dir / "team-status.md", _status_skill(config))
    _emit("team-status.md")

    # Always generate iteration skill
    _write_skill(skills_dir / "iteration-review.md", _iteration_review_skill(config))
    _emit("iteration-review.md")

    # Spawn agent skill (if sub-agent spawning enabled)
    if config.agents.allow_sub_agent_spawning:
        _write_skill(skills_dir / "spawn-agent.md", _spawn_agent_skill(config))
        _emit("spawn-agent.md")

    # Atlassian skills
    if config.atlassian.enabled:
        _write_skill(skills_dir / "jira-update.md", _jira_update_skill(config))
        _emit("jira-update.md")
        _write_skill(skills_dir / "sprint-report.md", _sprint_report_skill(config))
        _emit("sprint-report.md")

    # Smoke test skill
    _write_skill(skills_dir / "smoke-test.md", _smoke_test_skill(config))
    _emit("smoke-test.md")

    # Screenshot review skill (visual verification)
    _write_skill(skills_dir / "screenshot-review.md", _screenshot_review_skill(config))
    _emit("screenshot-review.md")

    # PR workflow skill
    _write_skill(skills_dir / "create-pr.md", _pr_workflow_skill(config))
    _emit("create-pr.md")

    # Release management skill
    _write_skill(skills_dir / "release.md", _release_management_skill(config))
    _emit("release.md")

    # Architecture review skill
    _write_skill(skills_dir / "arch-review.md", _arch_review_skill(config))
    _emit("arch-review.md")

    # Playwright testing skill (for frontend projects)
    if config.has_frontend_involvement():
        _write_skill(skills_dir / "playwright-test.md", _playwright_test_skill(config))
        _emit("playwright-test.md")

    # Excalidraw diagramming skill
    _write_skill(skills_dir / "excalidraw-diagram.md", _excalidraw_diagram_skill(config))
    _emit("excalidraw-diagram.md")

    # Code review skill
    _write_skill(skills_dir / "code-review.md", _code_review_skill(config))
    _emit("code-review.md")

    # Dependency audit skill
    _write_skill(skills_dir / "dependency-audit.md", _dependency_audit_skill(config))
    _emit("dependency-audit.md")

    # Performance benchmark skill
    _write_skill(skills_dir / "benchmark.md", _benchmark_skill(config))
    _emit("benchmark.md")

    # Checkpoint skill (always generated — session persistence)
    _write_skill(skills_dir / "checkpoint.md", _checkpoint_skill(config))
    _emit("checkpoint.md")

    # Agent init skill (always generated — startup ceremony)
    _write_skill(skills_dir / "agent-init.md", _agent_init_skill(config))
    _emit("agent-init.md")

    # Respawn skill (always generated — cooperative compaction)
    _write_skill(skills_dir / "respawn.md", _respawn_skill(config))
    _emit("respawn.md")

    # Handoff skill (always generated — structured handoffs)
    _write_skill(skills_dir / "handoff.md", _handoff_skill(config))
    _emit("handoff.md")

    # Context reload skill (always generated — context recovery)
    _write_skill(skills_dir / "context-reload.md", _context_reload_skill(config))
    _emit("context-reload.md")


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


def _truncate_at_sentence(text: str, max_len: int) -> str:
    """Truncate text at the last sentence boundary before max_len.

    Avoids mid-sentence truncation that produces incomplete fragments.
    Falls back to max_len truncation with '...' if no sentence boundary found.
    """
    if len(text) <= max_len:
        return text
    # Find last sentence-ending punctuation within max_len
    truncated = text[:max_len]
    last_period = truncated.rfind(". ")
    if last_period > max_len // 3:
        return truncated[: last_period + 1]
    # Fallback: truncate at last space to avoid mid-word cut
    last_space = truncated.rfind(" ")
    if last_space > max_len // 3:
        return truncated[:last_space] + "..."
    return truncated + "..."


def _detect_project_domains(config: ForgeConfig) -> set[str]:
    """Detect project domain(s) from description (primary) and requirements (secondary).

    Uses the short project DESCRIPTION as the primary signal to avoid
    false positives from substring matching on large requirements text.
    Returns a set of domain tags used to gate domain-specific content.
    """
    desc = config.project.description.lower()
    # Only use first ~500 chars of requirements for secondary signal
    req = (config.project.requirements[:500].lower()
           if config.project.requirements else "")
    domains: set[str] = set()

    # --- E-commerce / Marketplace ---
    ecom_keywords = ("e-commerce", "ecommerce", "marketplace", "online store",
                     "storefront", "shopping cart", "shopping platform")
    if any(k in desc for k in ecom_keywords):
        domains.add("ecommerce")
    elif re.search(r"\bproduct\s+catalog\b", desc):
        domains.add("ecommerce")

    # --- HR / Payroll ---
    hr_keywords = ("human resources", "hrms", "hris", "payroll",
                   "employee management", "employee portal", "hr platform",
                   "hr system", "workforce management")
    if any(k in desc for k in hr_keywords):
        domains.add("hr")

    # --- Financial / Fintech ---
    fin_keywords = ("fintech", "banking", "ledger", "accounting",
                    "bookkeeping", "financial platform", "payment gateway",
                    "payment processing")
    if any(k in desc for k in fin_keywords):
        domains.add("financial")
    elif "payment" in desc and any(k in desc for k in ("process", "gateway", "platform")):
        domains.add("financial")

    # --- Project / Task Management ---
    pm_keywords = ("project management", "task management", "issue tracker",
                   "kanban", "task board", "sprint planning")
    if any(k in desc for k in pm_keywords):
        domains.add("project_management")

    # --- Data Pipeline / ETL ---
    if any(k in desc for k in ("data pipeline", "etl", "data processing",
                                "data ingestion", "data orchestration")):
        domains.add("pipeline")
    elif config.is_cli_project() and "pipeline" in desc:
        domains.add("pipeline")

    # --- Real-time / Chat / Collaboration ---
    if any(k in desc for k in ("real-time chat", "messaging platform",
                                "chat application", "collaboration tool")):
        domains.add("realtime")

    # --- Content / Blog / CMS ---
    if any(k in desc for k in ("blog", "cms", "content management",
                                "publishing platform")):
        domains.add("content")

    # --- Auth as primary domain (not incidental auth) ---
    if any(k in desc for k in ("auth service", "identity provider",
                                "sso platform", "single sign-on",
                                "oauth provider", "authentication service")):
        domains.add("auth")

    # --- Vendor / Multi-vendor (sub-domain of ecommerce) ---
    if "ecommerce" in domains and any(
        k in desc for k in ("vendor", "multi-vendor", "marketplace")
    ):
        domains.add("vendor")

    # --- PCI / Compliance (only when payments are primary domain) ---
    if "financial" in domains or "ecommerce" in domains:
        if any(k in f"{desc} {req}" for k in ("pci", "pci-dss")):
            domains.add("pci")

    return domains


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
    """Generate functional verification checks from project config.

    Uses domain detection (description-primary) to avoid false positives
    from substring matching on large requirements text.
    """
    domains = _detect_project_domains(config)
    desc = config.project.description.lower()
    has_frontend = config.has_frontend_involvement()
    is_cli = config.is_cli_project()
    has_web = config.has_web_backend()
    checks: list[str] = []

    # CLI-specific checks — use description for feature detection
    if is_cli:
        if "pipeline" in domains or "pipeline" in desc or "etl" in desc:
            checks.append("- Pipeline definitions parse and validate correctly?")
            checks.append("- Sample pipeline executes end-to-end (extract → transform → load)?")
        if "plugin" in desc:
            checks.append("- Plugin loading and discovery works for custom extensions?")
        if "dry-run" in desc or "dry_run" in desc:
            checks.append("- Dry-run mode shows planned operations without side effects?")

    # Domain-gated checks: only include when domain is confidently detected
    if "ecommerce" in domains:
        checks.append("- Product catalog functionality complete (browse, search, filter)?")
        checks.append("- Shopping cart operations functional (add, remove, update quantities)?")
        checks.append("- Checkout/payment process works end-to-end?")
        if "vendor" in domains:
            checks.append("- Vendor onboarding and storefront creation works?")
            checks.append("- Inventory management tracks stock correctly?")
            checks.append("- Order management with status tracking works end-to-end?")

    if "hr" in domains:
        checks.append("- Payroll processing calculates correctly (taxes, deductions)?")
        checks.append("- Leave management workflow works (request, approve, reject)?")
        checks.append("- Org chart displays hierarchy correctly?")
        checks.append("- SSO integration authenticates via SAML/OIDC correctly?")

    if "financial" in domains:
        checks.append("- Transaction processing works correctly (create, validate, record)?")
        checks.append("- Audit trail captures all operations with immutable records?")

    if "project_management" in domains:
        checks.append("- Kanban board renders correctly with drag-and-drop between columns?")
        checks.append("- Task creation, assignment, and priority/due-date setting works?")

    if "content" in domains:
        checks.append("- Blog posts render correctly from MDX/markdown?")

    if "auth" in domains:
        checks.append("- Authentication flows working (registration, login, logout)?")

    # Generic checks based on description keywords (description is short/focused)
    if has_web and not is_cli:
        checks.append("- API endpoints respond correctly with proper status codes?")
    if "real-time" in desc or "websocket" in desc:
        checks.append("- Real-time features (WebSocket) connect and deliver messages?")
    if "dashboard" in desc and has_frontend:
        checks.append("- Dashboard views render and display correct data?")
    if "search" in desc and not is_cli:
        checks.append("- Search functionality returns relevant results?")
    if ("dark mode" in desc or "dark-mode" in desc) and has_frontend:
        checks.append("- Dark mode toggle works and persists preference?")
    if "responsive" in desc and has_frontend:
        checks.append("- Responsive design works across desktop and mobile viewports?")

    if not checks:
        checks.append("- Core feature requirements from project spec are functional?")

    return "\n".join(checks)


def _domain_context(config: ForgeConfig) -> str:
    """Build a concise domain context block for skill headers.

    Uses only the project description and a short requirements excerpt
    to avoid embedding thousands of words of raw requirements text.
    """
    parts = [f"**Project**: {config.project.description}"]
    if config.project.requirements:
        # Truncate at word boundary to keep skill files focused
        req = config.project.requirements
        if len(req) > 300:
            # Find last space before limit for clean truncation
            cut = req[:300].rfind(" ")
            if cut < 100:
                cut = 300
            excerpt = req[:cut].rstrip(".,;:-") + "..."
        else:
            excerpt = req
        parts.append(f"**Requirements**: {excerpt}")
    parts.append(
        f"**Mode**: {config.mode.value} | **Strategy**: {config.strategy.value}"
    )
    return "\n    ".join(parts)


def _non_negotiables_section(config: ForgeConfig, context: str = "") -> str:
    """Build non-negotiables verification section for skill templates.

    Args:
        config: Project configuration.
        context: Optional context hint for filtering relevant non-negotiables
                 (e.g., 'performance', 'security', 'release').
    """
    if not config.non_negotiables:
        return ""
    rules = config.non_negotiables
    items = "\n".join(f"    - {rule}" for rule in rules)
    return f"\n    ## Non-Negotiables Verification\n\n    Verify these project-level requirements are met:\n{items}\n"


def _infra_section(config: ForgeConfig) -> str:
    """Build infrastructure context from tech stack for skill templates."""
    parts: list[str] = []
    if config.tech_stack.infrastructure:
        parts.append(f"Infrastructure: {', '.join(config.tech_stack.infrastructure)}")
    if config.tech_stack.databases:
        parts.append(f"Databases: {', '.join(config.tech_stack.databases)}")
    return " | ".join(parts) if parts else ""


def _domain_specific_scenarios(config: ForgeConfig) -> list[str]:
    """Extract domain-specific test/verification scenarios from project config.

    Uses domain detection to avoid false positives from keyword matching.
    """
    domains = _detect_project_domains(config)
    scenarios: list[str] = []

    if "ecommerce" in domains:
        scenarios.extend([
            "Product catalog browsing and search",
            "Shopping cart operations (add, remove, update quantities)",
            "Checkout flow with payment processing",
            "Order status tracking and management",
        ])
        if "vendor" in domains:
            scenarios.extend([
                "Vendor registration and onboarding",
                "Vendor storefront management",
                "Commission calculation and payouts",
            ])

    if "financial" in domains:
        scenarios.append("Transaction processing and audit trail verification")

    if "hr" in domains:
        scenarios.extend([
            "Payroll processing verification",
            "Leave management workflow testing",
        ])

    if "auth" in domains:
        scenarios.append("Authentication flows (login, register, token refresh, logout)")

    if "pci" in domains:
        scenarios.append("PCI-DSS compliance (no card data in logs, encrypted storage)")

    # Infrastructure checks use tech stack (not keyword matching)
    desc = config.project.description.lower()
    if any(nn.lower().find("wcag") >= 0 or nn.lower().find("a11y") >= 0
           for nn in (config.non_negotiables or [])):
        scenarios.append("WCAG 2.1 AA accessibility compliance checks")
    if "redis" in [d.lower() for d in config.tech_stack.databases]:
        scenarios.append("Redis caching behavior (hit/miss ratios, invalidation)")
    if "aws" in [i.lower() for i in config.tech_stack.infrastructure]:
        scenarios.append("AWS deployment verification (ECS/EKS health, RDS connectivity)")
    if "docker" in [i.lower() for i in config.tech_stack.infrastructure]:
        scenarios.append("Container health checks and resource limits")

    return scenarios


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
    """Generate domain-specific security checks.

    Uses domain detection for domain-specific checks, tech stack for infra checks.
    """
    domains = _detect_project_domains(config)
    is_cli = config.is_cli_project()
    has_web = config.has_web_backend()
    checks: list[str] = []

    if "auth" in domains or "hr" in domains:
        checks.append("- Authentication: JWT/session validation on protected endpoints")
        checks.append("- Password hashing uses bcrypt/argon2, never plaintext")
    elif has_web:
        # Generic API security for any web backend
        checks.append("- API authentication verified on protected endpoints")

    if "ecommerce" in domains or "financial" in domains:
        checks.append("- Payment data: no card numbers stored in plain text")
        checks.append("- CSRF protection on state-changing operations")
    if "pci" in domains:
        checks.append("- PCI-DSS: sensitive data masked in logs and responses")
    if has_web and not is_cli:
        checks.append("- Input validation on all user-facing endpoints")
        checks.append("- Authorization: users can only access their own resources")
    if "hr" in domains:
        checks.append("- SSO: SAML/OIDC token validation, secure session handling")
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
    # Build domain-specific verification criteria
    domains = _detect_project_domains(config)
    domain_criteria: list[str] = []
    if "financial" in domains:
        domain_criteria.extend([
            "- [ ] Transaction processing: debit/credit operations create balanced ledger entries",
            "- [ ] Audit trail: all operations logged immutably (no UPDATE/DELETE on audit table)",
            "- [ ] Financial calculations: use decimal precision, no floating-point currency math",
        ])
    if "pci" in domains:
        domain_criteria.append("- [ ] PCI-DSS: no raw card data in logs, responses, or unencrypted storage")
    if "ecommerce" in domains:
        domain_criteria.extend([
            "- [ ] Checkout flow: end-to-end purchase completes with payment integration",
            "- [ ] Inventory: stock levels update correctly on purchase",
        ])
    if "hr" in domains:
        domain_criteria.extend([
            "- [ ] Payroll: tax/deduction calculations produce correct results",
            "- [ ] PII: employee data access is role-gated and access is audited",
        ])
    if "auth" in domains:
        domain_criteria.append("- [ ] Auth: register → login → protected access → token refresh → logout works")
    desc_lower = config.project.description.lower()
    req_lower = (config.project.requirements or "").lower()
    if "webhook" in desc_lower or "webhook" in req_lower:
        domain_criteria.append("- [ ] Webhooks: events trigger delivery to registered endpoints with retry")
    if "rate limit" in desc_lower or "rate limit" in req_lower or "rate-limit" in req_lower:
        domain_criteria.append("- [ ] Rate limiting: excessive requests return 429 with appropriate headers")
    if config.is_cli_project():
        if "pipeline" in desc_lower or "etl" in desc_lower:
            domain_criteria.extend([
                "- [ ] Pipeline execution: sample YAML pipeline runs end-to-end correctly",
                "- [ ] Dry-run mode: shows planned operations without side effects",
            ])
        if "plugin" in desc_lower:
            domain_criteria.append("- [ ] Plugin system: custom plugins discovered, loaded, and execute correctly")

    domain_verify_section = ""
    if domain_criteria:
        dc_text = "\n".join(f"    {c}" for c in domain_criteria)
        domain_verify_section = f"""
    ## Domain-Specific Verification (MANDATORY)

{dc_text}
"""
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
    6. **Quality & UX verification** (see below)
    7. **Performance verification** (see below)
    8. **Send to Critic** for independent review — Critic findings are HARD REQUIREMENTS
    9. **Decision**: PROCEED | REWORK | ROLLBACK | ESCALATE
    {domain_verify_section}

    ## Quality & User Experience Verification (MANDATORY)

    {"**Launch the application** and test as a real user:" if not config.is_cli_project() else "**Run the CLI** with real inputs as a real user:"}
    {"- Capture screenshots of all key pages/flows using Playwright" if config.has_frontend_involvement() else "- Capture CLI output for all key commands" if config.is_cli_project() else "- Hit every API endpoint with real HTTP requests"}
    {"- Use `/screenshot-review` skill to verify visual quality" if config.has_frontend_involvement() else ""}
    - Complete the primary user journey end-to-end
    - Test error paths: what happens with invalid input? Empty data? Network errors?
    - Verify error messages are helpful and actionable (not stack traces)
    {"- Check responsive design: desktop and mobile viewports" if config.has_frontend_involvement() else ""}
    {"- Run accessibility audit: `npx @axe-core/cli <url>`" if config.has_frontend_involvement() else ""}

    ## Performance Verification (MANDATORY)

    {"- **API benchmarks**: `hey -n 200 -c 20 <critical-endpoint>` — record p50/p95/p99 latency" if config.has_web_backend() else "- **CLI timing**: `time <command> <typical-args>` for all primary operations" if config.is_cli_project() else "- **Lighthouse**: `npx lighthouse <url> --output json` — Performance, Accessibility, Best Practices scores" if config.has_frontend_involvement() else "- **Benchmark key operations**: measure and record execution time"}
    {"- **Load test**: `hey -n 1000 -c 50 <url>` — verify error rate < 1% under load" if config.has_web_backend() else ""}
    {"- **Lighthouse audit**: Run on all key pages — scores must be > 80" if config.has_frontend_involvement() else ""}
    {"- **Bundle analysis**: Check build output size — flag bloated bundles" if config.has_frontend_involvement() else ""}
    - **Database queries**: Check for N+1 queries, slow queries, missing indexes
    - Record ALL measurements with actual numbers — include in iteration summary

    ## Critic Review (MANDATORY)

    After collecting all evidence above:
    - **Send everything to the Critic**: deliverables, screenshots/outputs, performance numbers, test results
    - **Critic's BLOCKERs are non-negotiable** — they must be resolved before PROCEED
    - **Critic's Improvement Tasks become tasks in the next iteration** — they are not optional
    - The Critic must be satisfied across ALL quality dimensions before the project can be complete

    ## Decision Outcomes

    If PROCEED: tag the iteration as verified, plan next iteration.
    If REWORK: route issues to specific agents:
{_agent_routing(config)}
    If ROLLBACK: restore last verified tag, ensure rollback scripts are safe.
    If ESCALATE: present situation to human with trade-off options and timeline impact.

    ## Pre-Decision Checklist (MANDATORY)

    Before ANY decision, verify:
    - [ ] `git status` shows clean working tree (no uncommitted/untracked files)
    - [ ] All branches merged via PR
    - [ ] Iteration tag applied (`iteration-N-verified`)
    - [ ] Compare delivered features against FULL project requirements list
    - [ ] List any requirements NOT yet implemented
    - [ ] Performance benchmarks recorded with actual numbers
    {"- [ ] Screenshots captured and reviewed" if config.has_frontend_involvement() else "- [ ] CLI outputs captured and reviewed" if config.is_cli_project() else "- [ ] API endpoints tested with real HTTP requests"}
    - [ ] Critic review complete with no unresolved BLOCKERs
    - [ ] Critic's quality scores meet threshold

    ## After PROCEED: Are We Done?

    After tagging the iteration, ask: **"Are ALL project requirements fully implemented?"**
    AND: **"Has the Critic approved the overall product quality?"**
    - If BOTH YES: Run a final comprehensive end-to-end smoke test, verify git is clean, then report project complete
    - If EITHER NO: Immediately plan the next iteration targeting remaining requirements AND Critic improvement tasks. **Do NOT stop.**

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
    3. **Register the spawn event**: Write a JSON event to `.forge/events/`:
       ```
       {{
         "event_type": "agent_started",
         "agent_type": "<agent-type>",
         "agent_name": "<to-be-assigned>",
         "parent_agent_type": "<your-type>",
         "parent_agent_name": "<your-name>",
         "task": "<task-description>",
         "timestamp": "<ISO-timestamp>"
       }}
       ```
    4. **Spawn with context**: Use the Agent tool with:
       - The full instruction file as system context
       - The task description as the initial prompt
       - Project context: {config.project.description} ({config.mode.value} mode, {config.strategy.value} strategy)
       - Naming protocol: instruct the child to choose a name and run `/agent-init detect` as first action
       - Parent identity: include your agent_type and agent_name so the child knows its parent
    5. **Verify spawn**: Confirm the sub-agent acknowledged its role, chose a name, and ran `/agent-init detect`
    6. **Track in checkpoint**: Update your checkpoint's `sub_agents` list with the new agent
    7. **Update session.json**: Add the new agent to the agent_tree (Team Leader only)

    ## Domain Context for Spawning

    When spawning agents for this project, include this domain context:
    - **Project**: {config.project.description}
    - **Requirements**: {_truncate_at_sentence(config.project.requirements, 500) if config.project.requirements else config.project.description}
    - **Strategy**: {config.strategy.value} — {"agents have full autonomy" if config.strategy.value == "auto-pilot" else "agents ask human only for architecture/scope/domain decisions" if config.strategy.value == "co-pilot" else "agents present significant decisions to human for approval"}

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

    domains = _detect_project_domains(config)

    # Domain-specific ticket examples and types
    examples: list[str] = []
    domain_ticket_types: list[str] = []
    if "hr" in domains:
        examples.append(f"- `{project_key}-42` \"In Progress\" \"Implementing payroll calculation engine with tax tables\"")
        examples.append(f"- `{project_key}-55` \"In Review\" \"Employee onboarding flow complete — SSO integration verified\"")
        examples.append(f"- `{project_key}-70` \"Testing\" \"Leave approval workflow ready for QA — edge cases covered\"")
        domain_ticket_types.extend([
            "- **Payroll**: tax calculation, salary processing, pay stub generation",
            "- **Leave Management**: PTO requests, approval workflows, balance tracking",
            "- **Employee Profiles**: onboarding, org hierarchy, document management",
            "- **Compliance**: audit logging, SSO integration, data protection",
        ])
    elif "ecommerce" in domains:
        examples.append(f"- `{project_key}-42` \"In Progress\" \"Implementing Stripe checkout flow with webhook handling\"")
        examples.append(f"- `{project_key}-55` \"In Review\" \"Product catalog search with Elasticsearch — filters working\"")
        examples.append(f"- `{project_key}-70` \"Testing\" \"Vendor dashboard analytics ready for QA — revenue charts verified\"")
        domain_ticket_types.extend([
            "- **Vendor**: onboarding, storefront setup, dashboard, payout management",
            "- **Payments**: Stripe integration, checkout flow, refund handling",
            "- **Catalog**: product listing, search, filters, inventory management",
            "- **Orders**: status tracking, fulfillment, shipping notifications",
        ])
    elif "financial" in domains:
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

    domains = _detect_project_domains(config)

    # Domain-specific metrics
    domain_metrics: list[str] = []
    if "hr" in domains:
        domain_metrics.extend([
            "- **HR Modules**: payroll processing status, leave management, org chart, performance reviews",
            "- **Compliance**: audit logging coverage, SSO integration progress, data protection measures",
            "- **Employee Features**: profile completeness, document management, onboarding flow status",
        ])
    elif "ecommerce" in domains:
        domain_metrics.extend([
            "- **Commerce Features**: checkout flow, Stripe payment integration, order management status",
            "- **Vendor Pipeline**: vendor onboarding count, storefront status, dashboard features",
            "- **Catalog & Inventory**: product listing, search/filter, inventory tracking progress",
        ])
    elif "financial" in domains:
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

    # Non-negotiables verification section
    non_neg_checks: list[str] = []
    if config.non_negotiables:
        for rule in config.non_negotiables:
            rule_lower = rule.lower()
            if "p95" in rule_lower or "latency" in rule_lower or "response time" in rule_lower:
                non_neg_checks.append(f"- **Performance**: {rule} — measure with `wrk` or `hey` against key endpoints")
            elif "pci" in rule_lower or "payment" in rule_lower:
                non_neg_checks.append(f"- **PCI-DSS**: {rule} — verify no card data in logs, encrypted storage")
            elif "wcag" in rule_lower or "accessibility" in rule_lower or "a11y" in rule_lower:
                non_neg_checks.append(f"- **Accessibility**: {rule} — run `npx @axe-core/cli` on key pages")
            elif "openapi" in rule_lower or "api doc" in rule_lower or "swagger" in rule_lower:
                non_neg_checks.append(f"- **API Docs**: {rule} — verify /docs endpoint is live and complete")
            elif "secret" in rule_lower or "leak" in rule_lower:
                non_neg_checks.append(f"- **Secrets**: {rule} — run `gitleaks detect` on the repo")
            else:
                non_neg_checks.append(f"- **Compliance**: {rule}")

    non_neg_section = ""
    if non_neg_checks:
        section_num_nn = len(sections) + 1
        nn_text = "\n".join(f"    {c}" for c in non_neg_checks)
        non_neg_section = f"\n\n    ## {section_num_nn}. Non-Negotiables Verification\n\n{nn_text}"

    # Domain-specific smoke test additions
    domains = _detect_project_domains(config)
    desc_lower = config.project.description.lower()
    domain_checks: list[str] = []
    if "financial" in domains:
        domain_checks.extend([
            "- Transaction processing: create debit/credit and verify ledger entries balance",
            "- Audit trail: verify all operations create immutable, append-only log records",
            "- Audit immutability: confirm UPDATE/DELETE on audit table is rejected",
        ])
        if "pci" in domains:
            domain_checks.append("- PCI-DSS: verify no raw card/account numbers appear in logs or API responses")
    if "ecommerce" in domains:
        domain_checks.extend([
            "- Product catalog: browse, search, filter return correct results",
            "- Cart operations: add, remove, update quantities work correctly",
            "- Checkout flow: complete purchase end-to-end (use test payment credentials)",
        ])
        if "vendor" in domains:
            domain_checks.extend([
                "- Vendor registration and storefront creation works end-to-end",
                "- Multi-vendor product aggregation returns correct results",
            ])
    if "hr" in domains:
        domain_checks.extend([
            "- Payroll calculation: verify tax/deduction computation correctness",
            "- Leave management: request → approval → balance update works",
        ])
    if "auth" in domains:
        domain_checks.append("- Auth flows: register → login → access protected resource → logout")
    if is_cli:
        if "pipeline" in desc_lower or "etl" in desc_lower:
            domain_checks.extend([
                "- Pipeline execution: sample pipeline runs end-to-end (extract → transform → load)",
                "- Dry-run mode: shows planned operations without side effects",
            ])
        if "plugin" in desc_lower:
            domain_checks.append("- Plugin loading: built-in and custom plugins discovered and loaded correctly")
    # Webhook verification if mentioned in requirements
    req_lower = (config.project.requirements or "").lower()
    if "webhook" in desc_lower or "webhook" in req_lower:
        domain_checks.append("- Webhook delivery: events trigger notifications to registered endpoints")
    # Rate limiting if mentioned
    if "rate limit" in desc_lower or "rate limit" in req_lower or "rate-limit" in req_lower:
        domain_checks.append("- Rate limiting: excessive requests are properly throttled (verify 429 response)")
    # Infrastructure checks
    if "redis" in [d.lower() for d in config.tech_stack.databases]:
        domain_checks.append("- Redis: connection verified, caching/rate-limiting operational")
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        domain_checks.append(f"- Database ({dbs}): migrations applied and seeded data accessible")

    domain_section = ""
    if domain_checks:
        section_num_d = len(sections) + (2 if non_neg_checks else 1)
        dc_text = "\n".join(f"    {c}" for c in domain_checks)
        domain_section = f"\n\n    ## {section_num_d}. Domain-Specific Checks ({config.project.description})\n\n{dc_text}"

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

    {body}{non_neg_section}{domain_section}

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
    desc = config.project.description.lower()
    domains = _detect_project_domains(config)
    frameworks = [f.lower() for f in config.tech_stack.frameworks]

    # --- CLI projects: generate CLI output review skill ---
    if is_cli:
        # Build domain-specific CLI outputs to capture
        cli_outputs = ["- `<command> --help` — main help text and available subcommands"]
        if "pipeline" in domains or "etl" in desc:
            cli_outputs.append("- `<command> run <sample>` — pipeline execution output with progress")
            cli_outputs.append("- `<command> validate <config>` — configuration validation output")
            cli_outputs.append("- `<command> run --dry-run <sample>` — dry-run output showing planned operations")
        if "plugin" in desc:
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

        # Domain-specific documentation areas — use domain detection
        domains = _detect_project_domains(config)
        doc_areas = []
        if "auth" in domains:
            doc_areas.append("- Authentication: login/register flows, token refresh, permission levels")
        if "financial" in domains or "ecommerce" in domains:
            doc_areas.append("- Transaction/payment: request schemas, idempotency keys, error codes")
        if "webhook" in desc:
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

    # Build domain-specific pages to capture — use domain detection
    domains = _detect_project_domains(config)
    desc = config.project.description.lower()
    pages = []
    pages.append("- Home / Landing page")

    if "auth" in domains:
        pages.append("- Login page")
        pages.append("- Registration page")
        pages.append("- User profile / account settings")
    if "ecommerce" in domains:
        pages.append("- Product listing / catalog page")
        pages.append("- Product detail page")
        pages.append("- Shopping cart (empty and populated states)")
        pages.append("- Checkout flow (each step)")
        if "vendor" in domains:
            pages.append("- Vendor dashboard (sales analytics, orders, payouts)")
            pages.append("- Vendor storefront / onboarding flow")
            pages.append("- Order management / order detail page")
            pages.append("- Inventory management view")
    if "dashboard" in desc:
        pages.append("- Dashboard / admin panel")
    if "search" in desc:
        pages.append("- Search results page")
    if "realtime" in domains:
        pages.append("- Chat / messaging interface")
    if "project_management" in domains:
        pages.append("- Kanban / task board (empty board, board with cards across columns)")
        pages.append("- Task detail / edit view (with assignments, due dates, priority)")
    if "hr" in domains:
        pages.append("- Employee directory / profile page")
        pages.append("- Payroll dashboard (salary, deductions, tax breakdown)")
        pages.append("- Leave management (request form, approval queue, balance view)")
        pages.append("- Org chart visualization (hierarchy, reporting structure)")
        pages.append("- SSO login page / IdP selection")
    if "content" in domains:
        pages.append("- Blog post / content pages")
    if not domains:
        pages.append("- All user-facing pages identified from the project")

    pages_text = "\n".join(f"   {p}" for p in pages)

    # Domain-specific state variants — use domain detection
    states = ["- Default/loaded state (with representative data)", "- Empty state (no data)"]
    if "auth" in domains:
        states.append("- Authenticated vs. anonymous user views")
    if "ecommerce" in domains:
        states.append("- Empty cart vs. populated cart")
        states.append("- Error state (validation errors, failed operations)")
        if "vendor" in domains:
            states.append("- Vendor vs. customer vs. admin views")
    if "real-time" in desc or "websocket" in desc:
        states.append("- Real-time update in progress (live data arriving)")
    if "project_management" in domains:
        states.append("- Drag-and-drop in progress (card being moved between columns)")
    if "hr" in domains:
        states.append("- Currency/number formatting (salary figures, tax calculations)")
        states.append("- Different role views (admin vs. manager vs. employee)")
        states.append("- Approval workflow states (pending, approved, rejected)")
    if "financial" in domains:
        states.append("- Currency/number formatting (transaction amounts, decimal precision)")
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

    # Domain-specific PR testing guidance — use domain detection
    domains = _detect_project_domains(config)
    desc = config.project.description.lower()
    is_cli = config.is_cli_project()
    domain_test_lines: list[str] = []

    if "auth" in domains:
        domain_test_lines.append("- Auth changes: verify login/logout and user sessions work")
    if "ecommerce" in domains:
        domain_test_lines.append("- Cart/checkout changes: test full purchase flow end-to-end")
        domain_test_lines.append("- Product changes: verify product display and search")
        if "vendor" in domains:
            domain_test_lines.append("- Vendor changes: verify onboarding and storefront creation")
            domain_test_lines.append("- Inventory changes: verify stock tracking and alerts")
    if "real-time" in desc or "websocket" in desc:
        domain_test_lines.append("- Real-time changes: verify WebSocket connectivity and live updates")
    if "project_management" in domains:
        domain_test_lines.append("- Board/task changes: verify drag-and-drop, task state transitions")
    if "financial" in domains:
        domain_test_lines.append("- Transaction changes: verify bookkeeping accuracy and audit trail")
    if "pci" in domains:
        domain_test_lines.append("- Security: verify no raw card numbers in logs or responses")
    if "hr" in domains:
        domain_test_lines.append("- Payroll changes: verify tax calculations and deduction accuracy")
        domain_test_lines.append("- Leave changes: verify approval workflow state transitions")
        domain_test_lines.append("- SSO changes: verify SAML/OIDC login flow end-to-end")
    if "pipeline" in domains:
        domain_test_lines.append("- Pipeline changes: verify end-to-end extract → transform → load")
        if is_cli and "plugin" in desc:
            domain_test_lines.append("- Plugin changes: verify plugin loading and execution")
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

    # Domain-specific pre-release checks — use domain detection
    domains = _detect_project_domains(config)
    desc = config.project.description.lower()
    domain_checks: list[str] = []
    if "auth" in domains:
        domain_checks.append("- Authentication flows verified (login, register, logout, token refresh)")
    if "ecommerce" in domains:
        domain_checks.append("- Payment/checkout flow tested end-to-end")
        domain_checks.append("- Cart operations verified (add, remove, update, persist)")
    if "financial" in domains:
        domain_checks.append("- Transaction processing verified (create, validate, reconcile)")
        domain_checks.append("- Audit trail integrity verified (immutable records, no data leakage)")
        domain_checks.append("- Financial calculations use decimal precision (no floating-point errors)")
    if "hr" in domains:
        domain_checks.append("- Payroll calculations verified (salary, taxes, deductions produce correct totals)")
        domain_checks.append("- Leave management workflows tested (request, approve, reject, balance updates)")
        domain_checks.append("- SSO/SAML authentication flow verified end-to-end")
        domain_checks.append("- Audit logs capture all sensitive operations (payroll runs, permission changes)")
        domain_checks.append("- Employee data privacy: PII masking and access controls verified")
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        domain_checks.append(f"- Database ({dbs}) migrations verified (up and down)")

    # Webhook/rate-limiting checks from requirements
    req_lower = (config.project.requirements or "").lower()
    if "webhook" in desc or "webhook" in req_lower:
        domain_checks.append("- Webhook delivery verified (events trigger, retry on failure)")
    if "rate limit" in desc or "rate limit" in req_lower or "rate-limit" in req_lower:
        domain_checks.append("- Rate limiting verified (excessive requests return 429)")

    # Project-type-specific checks
    if is_cli:
        domain_checks.append("- CLI installs cleanly and `--help` / `--version` work")
        domain_checks.append("- All subcommands execute successfully with sample inputs")
        if "plugin" in desc:
            domain_checks.append("- Plugin loading and discovery works correctly")
        if "pipeline" in desc or "etl" in desc:
            domain_checks.append("- Pipeline definitions backward-compatible with previous version")
            domain_checks.append("- Sample pipeline executes end-to-end correctly")
    elif has_frontend and not has_web:
        # Static site
        domain_checks.append("- Build output is complete and deployable")
        if "astro" in frameworks:
            domain_checks.append("- `npm run build` succeeds with no warnings")
        if "vercel" in desc:
            domain_checks.append("- Vercel deployment preview is healthy and all pages load")
    elif has_web:
        domain_checks.append("- API health endpoint responds after deployment")
        if "go" in [l.lower() for l in config.tech_stack.languages]:
            domain_checks.append("- Go services build and start successfully")

    # Add non-negotiables to pre-release checks
    if config.non_negotiables:
        for rule in config.non_negotiables:
            rule_lower = rule.lower()
            if "pci" in rule_lower:
                domain_checks.append(f"- PCI-DSS compliance verified: {rule}")
            elif "wcag" in rule_lower or "accessibility" in rule_lower or "a11y" in rule_lower:
                domain_checks.append(f"- Accessibility verified: {rule}")
            elif "p95" in rule_lower or "latency" in rule_lower or "response time" in rule_lower:
                domain_checks.append(f"- Performance target met: {rule}")
            elif "openapi" in rule_lower or "api doc" in rule_lower:
                domain_checks.append(f"- API documentation verified: {rule}")
            elif "secret" in rule_lower or "leak" in rule_lower:
                domain_checks.append(f"- Secrets scan passed: {rule}")

    # Infrastructure-specific pre-release checks
    infra_items = [i.lower() for i in config.tech_stack.infrastructure]
    if "aws" in infra_items or "ecs" in infra_items or "eks" in infra_items:
        domain_checks.append("- AWS deployment verified (ECS/EKS service stable, health checks passing)")
    if "docker" in infra_items:
        domain_checks.append("- Docker images built and scanned (no Critical vulnerabilities)")

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
    desc = config.project.description.lower()

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
    if has_web or is_cli or "form" in desc or "auth" in desc:
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

    # 8. Domain-specific architecture — use domain detection
    domains = _detect_project_domains(config)
    desc = config.project.description.lower()
    domain_checks: list[str] = []
    if "ecommerce" in domains:
        domain_checks.append("- Cart state management (persistence across sessions)")
        domain_checks.append("- Order processing workflow (state machine pattern)")
        domain_checks.append("- Inventory management (race condition prevention)")
    if "real-time" in desc or "websocket" in desc:
        domain_checks.append("- WebSocket connection lifecycle management")
        domain_checks.append("- Real-time state synchronization strategy")
    if "auth" in domains:
        domain_checks.append("- Authentication flow architecture (token refresh, session management)")
    if "pipeline" in domains:
        domain_checks.append("- Pipeline execution model (streaming vs batch, error recovery)")
        domain_checks.append("- Plugin loading and discovery mechanism")
        domain_checks.append("- Data validation between pipeline stages")
    if "microservice" in desc:
        domain_checks.append("- Service communication patterns (sync vs async, retries)")
        domain_checks.append("- Data consistency across services (saga, eventual consistency)")
    if "hr" in domains:
        domain_checks.append("- Sensitive data handling (PII encryption, audit trails)")
        domain_checks.append("- Calculation engine architecture (payroll, tax)")
        domain_checks.append("- SSO integration architecture (SAML/OIDC flow)")
    if not has_web and has_frontend:
        domain_checks.append("- Build-time vs runtime content strategy")
        domain_checks.append("- Asset optimization pipeline (images, fonts, CSS)")
    if "content" in domains:
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


def _playwright_test_skill(config: ForgeConfig) -> str:
    """Generate Playwright testing skill for frontend verification."""
    tech = _tech_stack_summary(config)
    frameworks = [f.lower() for f in config.tech_stack.frameworks]
    agents = set(config.get_active_agents())
    desc = config.project.description.lower()

    # Detect frontend framework for specific guidance
    if any(f in frameworks for f in ("react", "next", "nextjs", "next.js")):
        framework_note = "React/Next.js — test components, pages, and client-side routing"
    elif any(f in frameworks for f in ("vue", "nuxt", "nuxtjs")):
        framework_note = "Vue/Nuxt — test components, pages, and Vue Router navigation"
    elif any(f in frameworks for f in ("angular",)):
        framework_note = "Angular — test components, services, and Angular Router"
    elif any(f in frameworks for f in ("svelte",)):
        framework_note = "Svelte — test components and SvelteKit routing"
    else:
        framework_note = "Test all UI components, pages, and user workflows"

    # Domain-specific test scenarios — use domain detection
    domains = _detect_project_domains(config)
    domain_tests: list[str] = []
    if "ecommerce" in domains:
        domain_tests.extend([
            "### E-Commerce Test Scenarios",
            "- **Product catalog**: Browse, search, filter products, verify product detail pages",
            "- **Shopping cart**: Add/remove items, update quantities, verify cart persistence across pages",
            "- **Checkout flow**: Complete checkout end-to-end (address → shipping → payment → confirmation)",
            "- **Stripe payment**: Use Stripe test cards (`4242424242424242`), verify payment success/failure states",
        ])
        if "vendor" in domains:
            domain_tests.extend([
                "- **Vendor flows**: Vendor registration, storefront setup, product listing, order management",
                "- **Multi-vendor**: Product aggregation from multiple vendors, vendor-specific filtering",
            ])
    if "auth" in domains:
        domain_tests.extend([
            "### Authentication Test Scenarios",
            "- **Login**: Valid credentials, invalid credentials, locked account, remember me",
            "- **Registration**: Valid registration, duplicate email, password validation rules",
            "- **Session**: Token refresh, session expiry, logout, concurrent sessions",
        ])
    if "dashboard" in config.project.description.lower():
        domain_tests.append("- **Dashboard**: Data loading, chart rendering, filter interactions, export functions")

    domain_section = ""
    if domain_tests:
        dt_text = "\n".join(f"    {t}" for t in domain_tests)
        domain_section = f"\n{dt_text}\n"

    # Accessibility section — enhanced if WCAG in non-negotiables
    a11y_section = """
    ## Accessibility Testing (WCAG 2.1 AA)

    ```typescript
    import {{ test, expect }} from '@playwright/test';
    import AxeBuilder from '@axe-core/playwright';

    test('should have no accessibility violations', async ({{ page }}) => {{
      await page.goto('/');
      const results = await new AxeBuilder({{ page }}).analyze();
      expect(results.violations).toEqual([]);
    }});
    ```

    Key accessibility checks:
    - Color contrast ratios meet AA standards (4.5:1 for text, 3:1 for large text)
    - All interactive elements are keyboard navigable
    - Form inputs have associated labels
    - Images have alt text
    - ARIA roles and properties are correct"""

    wcag_in_non_neg = config.non_negotiables and any("wcag" in nn.lower() or "accessibility" in nn.lower() or "a11y" in nn.lower() for nn in config.non_negotiables)
    if wcag_in_non_neg:
        a11y_section += """
    - **Non-negotiable**: Every page MUST pass axe-core with zero violations before merge
    - Run `npx playwright test --grep @a11y` as part of pre-merge checks"""

    # Agent coordination
    agent_roles: list[str] = []
    if "frontend-developer" in agents or "frontend-engineer" in agents:
        fe_agent = "frontend-developer" if "frontend-developer" in agents else "frontend-engineer"
        agent_roles.append(f"- **{fe_agent}**: Write and maintain Playwright tests alongside UI code")
    if "qa-engineer" in agents:
        agent_roles.append("- **qa-engineer**: Run full E2E suite during iteration review, report failures")
    if "frontend-designer" in agents:
        agent_roles.append("- **frontend-designer**: Verify visual accuracy against design specs using screenshots")
    if "critic" in agents:
        agent_roles.append("- **critic**: Review screenshot evidence for visual quality and UX consistency")
    agent_section = ""
    if agent_roles:
        ar_text = "\n".join(f"    {r}" for r in agent_roles)
        agent_section = f"\n    ## Agent Responsibilities\n\n{ar_text}\n"

    non_neg = _non_negotiables_section(config)

    return f"""\
    ---
    name: playwright-test
    description: "Run Playwright tests for visual verification and E2E testing"
    argument-hint: "<test-file-or-pattern>"
    ---

    # Playwright Testing

    > {_domain_context(config)}
    > Stack: {tech}
    > Framework: {framework_note}

    ## When to Use

    - After implementing or modifying any UI component or page
    - Before marking frontend tasks as complete
    - During iteration review for visual regression checks
    - When verifying responsive design across viewports

    ## Playwright CLI Commands

    ### Run all tests
    ```bash
    npx playwright test
    ```

    ### Run specific test file
    ```bash
    npx playwright test tests/e2e/specific-test.spec.ts
    ```

    ### Run with UI mode (debugging)
    ```bash
    npx playwright test --ui
    ```

    ### Generate test from user actions
    ```bash
    npx playwright codegen http://localhost:3000
    ```

    ### Screenshot comparison
    ```bash
    npx playwright test --update-snapshots  # Update baseline
    npx playwright test                     # Compare against baseline
    ```
    {domain_section}
    ## Test Structure

    ```typescript
    import {{ test, expect }} from '@playwright/test';

    test.describe('Feature Name', () => {{
      test('should render correctly', async ({{ page }}) => {{
        await page.goto('/feature');
        await expect(page.getByRole('heading')).toHaveText('Feature');
        await expect(page).toHaveScreenshot('feature-default.png');
      }});

      test('should handle user interaction', async ({{ page }}) => {{
        await page.goto('/feature');
        await page.getByRole('button', {{ name: 'Submit' }}).click();
        await expect(page.getByText('Success')).toBeVisible();
      }});
    }});
    ```

    ## Visual Regression Workflow

    1. Capture baseline screenshots: `npx playwright test --update-snapshots`
    2. Make UI changes
    3. Run tests: `npx playwright test`
    4. Review diffs in `test-results/` directory
    5. If changes are intentional, update baselines

    ## Viewport Testing

    Test across standard viewports:
    - Mobile: 375x667 (iPhone SE)
    - Tablet: 768x1024 (iPad)
    - Desktop: 1280x720 (standard)
    - Wide: 1920x1080 (full HD)
    {a11y_section}
    {non_neg}{agent_section}
    ## Forge Workflow Integration

    - Save screenshots to `docs/screenshots/` for human review
    - Include screenshot evidence in PR descriptions
    - Run Playwright tests in CI before merge

    $ARGUMENTS
    """


def _excalidraw_diagram_skill(config: ForgeConfig) -> str:
    """Generate Excalidraw diagramming skill."""
    tech = _tech_stack_summary(config)
    agents_set = set(config.get_active_agents())
    agents = _agents_list(config)
    desc = config.project.description.lower()

    # Domain-specific diagram types — use domain detection
    domains = _detect_project_domains(config)
    domain_diagrams: list[str] = []
    if "ecommerce" in domains:
        domain_diagrams.extend([
            "### Checkout / Payment Flow",
            "- Sequence diagram: Browse → Cart → Checkout → Stripe Payment → Order Confirmation",
            "- Include: Stripe webhook handling, payment failure retry, inventory reservation",
            "- Save as: `docs/diagrams/sequences/checkout-flow.excalidraw`",
            "",
        ])
        if "vendor" in domains:
            domain_diagrams.extend([
                "### Multi-Vendor Marketplace Topology",
                "- Vendor onboarding flow (registration → approval → storefront creation)",
                "- Commission calculation and payout pipeline",
                "- Save as: `docs/diagrams/marketplace-topology.excalidraw`",
                "",
            ])
    if "financial" in domains:
        domain_diagrams.extend([
            "### Transaction Processing Flow",
            "- Sequence: Request → Validation → Ledger Entry (debit+credit) → Audit Log → Response",
            "- Include: transaction rollback paths, webhook notification triggers",
            "- Save as: `docs/diagrams/sequences/transaction-flow.excalidraw`",
            "",
            "### Audit Trail Architecture",
            "- Immutable append-only audit log data flow",
            "- Audit query paths for compliance reporting",
            "- Save as: `docs/diagrams/audit-trail-architecture.excalidraw`",
            "",
        ])
    if "pci" in domains:
        domain_diagrams.extend([
            "### PCI-DSS Compliance Zones",
            "- Network boundaries between PCI scope and non-PCI services",
            "- Data flow showing where card data is handled/tokenized",
            "- Trust boundaries with data classification zones",
            "- Save as: `docs/diagrams/pci-compliance-zones.excalidraw`",
            "",
        ])
    if "hr" in domains:
        domain_diagrams.extend([
            "### Payroll Processing Pipeline",
            "- Sequence: Time tracking → Tax calculation → Deductions → Disbursement",
            "- Include: compliance checkpoints, audit trail",
            "- Save as: `docs/diagrams/sequences/payroll-flow.excalidraw`",
            "",
        ])
    if "auth" in domains:
        domain_diagrams.extend([
            "### Authentication Flow",
            "- Login/register sequence with token lifecycle",
            "- Token refresh and session management",
            "- Save as: `docs/diagrams/sequences/auth-flow.excalidraw`",
            "",
        ])
    if "pipeline" in domains:
        domain_diagrams.extend([
            "### Data Pipeline Architecture",
            "- Extract → Transform → Load stages with data flow",
            "- Error handling and dead-letter queue paths",
            "- Plugin/extension points",
            "- Save as: `docs/diagrams/pipeline-architecture.excalidraw`",
            "",
        ])
    if "microservice" in desc:
        domain_diagrams.extend([
            "### Service Mesh / Communication",
            "- Inter-service communication patterns (sync/async)",
            "- Event bus / message queue topology",
            "- Service discovery and load balancing",
            "- Save as: `docs/diagrams/service-mesh.excalidraw`",
            "",
        ])

    domain_section = ""
    if domain_diagrams:
        dd_text = "\n".join(f"    {d}" for d in domain_diagrams)
        domain_section = f"\n    ## Domain-Specific Diagrams ({config.project.description})\n\n{dd_text}"

    # Infrastructure diagrams based on tech stack
    infra_diagrams: list[str] = []
    infra_items = [i.lower() for i in config.tech_stack.infrastructure]
    if "aws" in infra_items or "ecs" in infra_items or "eks" in infra_items:
        infra_diagrams.extend([
            "### AWS Infrastructure",
            "- ECS/EKS cluster layout with service placement",
            "- RDS/ElastiCache connectivity and VPC subnets",
            "- Load balancer → service → database data flow",
            "- Save as: `docs/diagrams/aws-infrastructure.excalidraw`",
        ])
    elif "docker" in infra_items or "kubernetes" in infra_items:
        infra_diagrams.extend([
            "### Container Infrastructure",
            "- Container orchestration layout",
            "- Service networking and port mapping",
            "- Save as: `docs/diagrams/container-infrastructure.excalidraw`",
        ])
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        infra_diagrams.extend([
            f"### Database Topology ({dbs})",
            "- Primary/replica configuration",
            "- Connection pooling and caching layers",
            f"- Save as: `docs/diagrams/database-topology.excalidraw`",
        ])

    infra_section = ""
    if infra_diagrams:
        it_text = "\n".join(f"    {d}" for d in infra_diagrams)
        infra_section = f"\n\n{it_text}\n"

    # Agent-specific roles
    agent_roles: list[str] = []
    if "architect" in agents_set:
        agent_roles.append("- **architect**: Create and own system architecture, data model, and deployment diagrams")
    if "documentation-specialist" in agents_set:
        agent_roles.append("- **documentation-specialist**: Maintain diagrams, ensure they stay current with code")
    if "devops-specialist" in agents_set:
        agent_roles.append("- **devops-specialist**: Create and maintain deployment topology and infrastructure diagrams")
    if "security-tester" in agents_set:
        agent_roles.append("- **security-tester**: Diagram security zones, trust boundaries, and data flow for threat modeling")
    if "team-leader" in agents_set:
        agent_roles.append("- **team-leader**: Reference diagrams in sprint planning, use in architecture decision records")
    agent_roles_text = "\n".join(f"    {r}" for r in agent_roles) if agent_roles else "    - All agents: Reference diagrams when discussing architecture decisions"

    return f"""\
    ---
    name: excalidraw-diagram
    description: "Create and maintain architecture diagrams using Excalidraw"
    argument-hint: "<diagram-type>"
    ---

    # Excalidraw Architecture Diagrams

    > {_domain_context(config)}
    > Stack: {tech}

    ## When to Use

    - During architecture design and review
    - When documenting system topology or data flows
    - Before major refactoring to visualize current vs target state
    - Sprint planning to illustrate feature scope
    - Onboarding documentation for new team members

    ## Excalidraw CLI Usage

    ### Install
    ```bash
    npm install -g @excalidraw/cli
    ```

    ### Convert Excalidraw JSON to PNG/SVG
    ```bash
    npx @excalidraw/cli export --format png docs/diagrams/architecture.excalidraw
    npx @excalidraw/cli export --format svg docs/diagrams/architecture.excalidraw
    ```

    ## Core Diagram Types

    ### 1. System Architecture
    - High-level component diagram showing services, databases, external APIs
    - Data flow arrows with protocol labels (HTTP, gRPC, WebSocket, etc.)
    - Save as: `docs/diagrams/system-architecture.excalidraw`

    ### 2. Data Model / ER Diagram
    - Entity relationships with cardinality
    - Key fields and indexes
    - Save as: `docs/diagrams/data-model.excalidraw`

    ### 3. Sequence Diagrams
    - Critical user flows for this project
    - Error handling and retry flows
    - Save as: `docs/diagrams/sequences/<flow-name>.excalidraw`

    ### 4. Deployment Topology
    - Infrastructure layout ({', '.join(config.tech_stack.infrastructure) if config.tech_stack.infrastructure else 'containers, servers, CDN'})
    - Network boundaries and security zones
    - Save as: `docs/diagrams/deployment.excalidraw`
    {domain_section}{infra_section}
    ## Excalidraw File Format

    `.excalidraw` files are JSON with this structure:
    ```json
    {{
      "type": "excalidraw",
      "version": 2,
      "elements": [
        {{
          "type": "rectangle",           // rectangle, ellipse, diamond, text, arrow, line
          "x": 100, "y": 200,           // position
          "width": 200, "height": 80,   // dimensions
          "strokeColor": "#1e1e1e",
          "backgroundColor": "#a5d8ff", // fill color
          "fillStyle": "solid",
          "strokeWidth": 2,
          "roundness": {{ "type": 3 }},  // rounded corners
          "boundElements": [{{ "type": "text", "id": "..." }}]  // linked text
        }},
        {{
          "type": "text",
          "text": "API Server",          // label content
          "fontSize": 16,
          "textAlign": "center",
          "containerId": "..."           // parent shape ID
        }},
        {{
          "type": "arrow",
          "startBinding": {{ "elementId": "...", "focus": 0, "gap": 1 }},
          "endBinding": {{ "elementId": "...", "focus": 0, "gap": 1 }},
          "points": [[0,0], [200,100]]   // arrow path
        }}
      ]
    }}
    ```

    **Tips**: Use `backgroundColor` to color-code components (blue=services, green=databases, orange=external APIs). Arrows with `startBinding`/`endBinding` auto-attach to shapes.

    ## Workflow

    1. Create/update `.excalidraw` files in `docs/diagrams/`
    2. Export to PNG for embedding in docs: `npx @excalidraw/cli export --format png <file>`
    3. Reference exported images in README, Confluence, or PR descriptions
    4. Keep diagrams in git — they are JSON files and diff cleanly
    5. Update diagrams when architecture changes

    ## Agent Responsibilities

{agent_roles_text}

    $ARGUMENTS
    """


def _code_review_skill(config: ForgeConfig) -> str:
    """Generate structured code review skill."""
    tech = _tech_stack_summary(config)
    mode = config.mode.value
    quality_bar = "70%" if mode == "mvp" else "90%" if mode == "production-ready" else "100%"

    non_neg_checks = ""
    if config.non_negotiables:
        rules = "\n".join(f"    - [ ] {rule}" for rule in config.non_negotiables)
        non_neg_checks = f"""
    ### Non-Negotiable Compliance
    {rules}
    """

    # Domain-specific code review sections
    domains = _detect_project_domains(config)
    is_cli = config.is_cli_project()
    domain_review: list[str] = []
    if "financial" in domains:
        domain_review.extend([
            "- [ ] Double-entry bookkeeping: every transaction creates balanced debit/credit entries",
            "- [ ] Audit trail: all financial operations create immutable, append-only log records",
            "- [ ] Transaction atomicity: financial operations use DB transactions with proper rollback",
            "- [ ] No raw card/account numbers in logs, error messages, or API responses",
        ])
    if "pci" in domains:
        domain_review.extend([
            "- [ ] PCI-DSS: sensitive data encrypted at rest and in transit",
            "- [ ] PCI-DSS: no cardholder data stored beyond what's necessary",
        ])
    if "ecommerce" in domains:
        domain_review.extend([
            "- [ ] Cart/checkout: race conditions handled for concurrent cart updates",
            "- [ ] Payment flow: idempotency keys prevent duplicate charges",
            "- [ ] Price calculations: use decimal types, not floating point",
        ])
    if "hr" in domains:
        domain_review.extend([
            "- [ ] Payroll calculations: tax and deduction logic uses precise arithmetic",
            "- [ ] PII handling: employee data access is role-gated and audited",
        ])
    if is_cli:
        desc = config.project.description.lower()
        domain_review.extend([
            "- [ ] CLI interface: command help text is clear and complete",
            "- [ ] Error messages: user-facing (no stack traces), suggest fixes",
            "- [ ] Exit codes: correct non-zero codes for different failure modes",
        ])
        if "pipeline" in desc or "etl" in desc:
            domain_review.extend([
                "- [ ] Pipeline definitions: YAML/config schema validated before execution",
                "- [ ] Data flow: transformers properly handle edge cases (empty, malformed)",
                "- [ ] Plugin interfaces: contracts enforced, isolation maintained",
            ])
    if "pipeline" in domains and not is_cli:
        domain_review.append("- [ ] Data pipeline: stage boundaries handle backpressure and errors")
    if "auth" in domains:
        domain_review.append("- [ ] Auth flows: tokens properly validated, expired tokens rejected")

    domain_section = ""
    if domain_review:
        items = "\n".join(f"    {item}" for item in domain_review)
        domain_section = f"""
    ### Domain-Specific
{items}
    """

    return f"""\
    ---
    name: code-review
    description: "Structured code review checklist with project-specific quality gates"
    argument-hint: "<pr-number-or-branch>"
    ---

    # Code Review

    **Tech Stack**: {tech}
    **Quality Bar**: {quality_bar} ({mode} mode)

    ## Review Checklist

    ### Correctness
    - [ ] Code does what the ticket/task describes
    - [ ] Edge cases handled (null, empty, boundary values)
    - [ ] Error handling is appropriate (not swallowed, not over-caught)
    - [ ] No regressions in existing functionality

    ### Security (OWASP Top 10)
    - [ ] No SQL injection (parameterized queries)
    - [ ] No XSS (output encoding, CSP headers)
    - [ ] No hardcoded secrets (env vars, SecretStr)
    - [ ] Input validation at system boundaries
    - [ ] Authentication/authorization checks present
    - [ ] No sensitive data in logs or error messages

    ### Architecture
    - [ ] Follows existing patterns and conventions
    - [ ] External dependencies behind abstractions
    - [ ] No circular dependencies introduced
    - [ ] Single responsibility — functions/classes do one thing
    - [ ] No function body > 50 lines, no file > 300 lines

    ### Testing
    - [ ] New code has tests (unit at minimum)
    - [ ] Tests cover happy path AND error cases
    - [ ] No flaky tests introduced
    - [ ] Mocks are realistic (named mocks, not bare MagicMock)

    ### Performance
    - [ ] No N+1 queries
    - [ ] No unbounded loops or memory allocations
    - [ ] Async I/O used for network calls (no sync in async)
    - [ ] Database indexes for new query patterns
    {domain_section}{non_neg_checks}
    ## Review Verdicts

    - **BLOCKER**: Must fix before merge. Re-review required.
    - **WARNING**: Should fix. Team Leader decides if it blocks.
    - **NOTE**: Optional improvement. Can merge without fixing.

    ## Process

    1. Read the PR description and linked ticket
    2. Review diff file-by-file using the checklist
    3. Run the tests locally if changes are non-trivial
    4. For big PRs: exercise the feature manually
    5. Leave review with verdict, specific feedback, and confidence level
    """


def _dependency_audit_skill(config: ForgeConfig) -> str:
    """Generate dependency audit skill."""
    tech = _tech_stack_summary(config)
    langs = [l.lower() for l in config.tech_stack.languages]
    agents = set(config.get_active_agents())

    python_section = ""
    if "python" in langs or any(
        f.lower() in ("fastapi", "django", "flask", "click", "typer")
        for f in config.tech_stack.frameworks
    ):
        python_section = """
    ### Python
    ```bash
    # Vulnerability scan
    pip-audit

    # License check
    pip-licenses --format=table --with-urls

    # Outdated packages
    pip list --outdated

    # Dependency tree
    pipdeptree
    ```
    """

    node_section = ""
    if "javascript" in langs or "typescript" in langs or any(
        f.lower() in ("react", "vue", "angular", "next", "nextjs", "express")
        for f in config.tech_stack.frameworks
    ):
        node_section = """
    ### Node.js
    ```bash
    # Vulnerability scan
    npm audit

    # Fix auto-fixable vulnerabilities
    npm audit fix

    # License check
    npx license-checker --summary

    # Outdated packages
    npm outdated
    ```
    """

    # Container image scanning
    container_section = ""
    infra_items = [i.lower() for i in config.tech_stack.infrastructure]
    if "docker" in infra_items or "aws" in infra_items or "ecs" in infra_items or "eks" in infra_items:
        container_section = """
    ### Container Images
    ```bash
    # Scan container images for vulnerabilities
    docker scout cves <image-name>

    # Alternative: Trivy scanner
    trivy image <image-name>

    # Check base image freshness
    docker scout recommendations <image-name>
    ```
    """

    # Domain-specific dependency priorities — use domain detection
    domains = _detect_project_domains(config)
    domain_deps: list[str] = []
    if "pci" in domains or "financial" in domains:
        domain_deps.extend([
            "- **Payment/PCI-DSS dependencies**: Prioritize payment SDK, cryptography libraries, and TLS libraries. Any vulnerability in these is automatically Critical severity.",
            "- **Crypto libraries**: Verify no deprecated algorithms (MD5, SHA1 for signing, RSA < 2048-bit).",
        ])
    if "auth" in domains:
        domain_deps.append("- **Auth dependencies**: JWT libraries, OAuth/OIDC clients, bcrypt/argon2 — vulnerabilities here are Critical.")
    if "ecommerce" in domains:
        domain_deps.append("- **E-commerce deps**: Payment SDKs, session management, CSRF protection libraries — audit with extra scrutiny.")
    if "redis" in [d.lower() for d in config.tech_stack.databases]:
        domain_deps.append("- **Redis client**: Check for connection security (TLS), command injection vulnerabilities.")
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        domain_deps.append(f"- **Database drivers ({dbs})**: SQL injection vectors, connection handling, TLS support.")

    domain_section = ""
    if domain_deps:
        dd_text = "\n".join(f"    {d}" for d in domain_deps)
        domain_section = f"\n    ## Domain-Specific Dependency Priorities\n\n{dd_text}\n"

    # Agent coordination
    agent_section = ""
    coord_agents: list[str] = []
    if "security-tester" in agents:
        coord_agents.append("- **security-tester**: Review Critical/High findings, validate fixes, check for transitive vulnerabilities")
    if "performance-engineer" in agents:
        coord_agents.append("- **performance-engineer**: Evaluate performance impact of dependency updates (bundle size, startup time)")
    if "devops-specialist" in agents:
        coord_agents.append("- **devops-specialist**: Update container base images, CI pipeline dependencies")
    if "backend-developer" in agents:
        coord_agents.append("- **backend-developer**: Apply dependency patches, test for regressions")
    if coord_agents:
        coord_text = "\n".join(f"    {a}" for a in coord_agents)
        agent_section = f"\n    ## Agent Coordination\n\n{coord_text}\n"

    non_neg = _non_negotiables_section(config)

    return f"""\
    ---
    name: dependency-audit
    description: "Audit project dependencies for vulnerabilities, licenses, and updates"
    argument-hint: ""
    ---

    # Dependency Audit

    > {_domain_context(config)}
    > Stack: {tech}

    ## When to Run

    - Before every release
    - Weekly during active development
    - When adding new dependencies
    - After Dependabot/Renovate PRs

    ## Audit Commands
    {python_section}{node_section}{container_section}
    ## Vulnerability Triage

    | Severity | Action | SLA |
    |----------|--------|-----|
    | Critical | Fix immediately, block release | Same day |
    | High | Fix before next release | 3 days |
    | Medium | Schedule fix | Next sprint |
    | Low | Track, fix when convenient | Backlog |
    {domain_section}
    ## License Compliance

    **Allowed**: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0
    **Review Required**: LGPL, AGPL, GPL (check compatibility with project license)
    **Blocked**: Proprietary, unlicensed, unknown
    {non_neg}{agent_section}
    ## Process

    1. Run vulnerability scan for all package ecosystems
    2. Triage findings by severity
    3. Update/patch critical and high vulnerabilities
    4. Review licenses of new dependencies
    5. Document exceptions in `SECURITY.md` if any vulnerabilities are accepted
    6. Report findings to Team Leader

    $ARGUMENTS
    """


def _benchmark_skill(config: ForgeConfig) -> str:
    """Generate performance benchmark skill."""
    tech = _tech_stack_summary(config)
    is_cli = config.is_cli_project()
    has_web = config.has_web_backend()
    has_frontend = config.has_frontend_involvement()
    agents = set(config.get_active_agents())

    # Extract p95 target from non-negotiables if present
    p95_target = "< 500ms"
    p50_target = "< 100ms"
    p99_target = "< 1000ms"
    if config.non_negotiables:
        for rule in config.non_negotiables:
            rule_lower = rule.lower()
            if "p95" in rule_lower:
                # Extract the target value from rules like "p95 API response time < 200ms"
                import re
                match = re.search(r"<\s*(\d+)\s*ms", rule_lower)
                if match:
                    p95_val = int(match.group(1))
                    p95_target = f"< {p95_val}ms"
                    p50_target = f"< {p95_val // 2}ms"
                    p99_target = f"< {p95_val * 2}ms"

    if is_cli:
        kpi_section = """
    ## Key Performance Indicators

    | Metric | Target | How to Measure |
    |--------|--------|----------------|
    | Command startup time | < 500ms | `time <command> --help` |
    | Throughput (items/sec) | Baseline + 10% | Custom benchmark script |
    | Memory usage (peak) | < 256MB | `mprof run <command>` |
    | File I/O throughput | > 100MB/s | `pv` or custom benchmark |
    """
    elif has_web:
        kpi_section = f"""
    ## Key Performance Indicators

    | Metric | Target | How to Measure |
    |--------|--------|----------------|
    | API response time (p50) | {p50_target} | `wrk` / `hey` / `k6` |
    | API response time (p95) | {p95_target} | `wrk` / `hey` / `k6` |
    | API response time (p99) | {p99_target} | `wrk` / `hey` / `k6` |
    | Throughput (req/sec) | > 1000 | `wrk -t4 -c100 -d30s` |
    | Error rate under load | < 0.1% | `k6` with checks |
    | DB query time (p95) | < 50ms | Query logging / APM |
    | Memory usage (steady) | < 512MB | Container metrics |
    """
    elif has_frontend:
        kpi_section = """
    ## Key Performance Indicators

    | Metric | Target | How to Measure |
    |--------|--------|----------------|
    | First Contentful Paint | < 1.5s | Lighthouse |
    | Largest Contentful Paint | < 2.5s | Lighthouse |
    | Cumulative Layout Shift | < 0.1 | Lighthouse |
    | Time to Interactive | < 3.5s | Lighthouse |
    | Bundle size (gzipped) | < 200KB | `next build` / `vite build` |
    | Lighthouse Performance | > 90 | `npx lighthouse` |
    """
    else:
        kpi_section = f"""
    ## Key Performance Indicators

    | Metric | Target | How to Measure |
    |--------|--------|----------------|
    | Operation latency (p50) | {p50_target} | Custom profiling |
    | Operation latency (p95) | {p95_target} | Custom profiling |
    | Memory usage (peak) | < 512MB | Memory profiler |
    | Throughput | Baseline + 10% | Benchmark suite |
    """

    # Domain-specific benchmark scenarios — use domain detection
    domains = _detect_project_domains(config)
    domain_benchmarks: list[str] = []
    if "ecommerce" in domains:
        domain_benchmarks.extend([
            "- **Checkout flow**: End-to-end checkout latency (browse → cart → payment → confirmation)",
            "- **Product search**: Search response time with 10k+ products, filtered queries",
            "- **Shopping cart**: Concurrent cart operations (add/remove/update) under load",
        ])
        if "vendor" in domains:
            domain_benchmarks.extend([
                "- **Multi-vendor load**: Aggregated product listing with 100+ vendors",
                "- **Commission calculation**: Batch payout processing throughput",
            ])
    if "financial" in domains:
        domain_benchmarks.append("- **Payment processing**: Payment API round-trip time, webhook processing latency")
    if "auth" in domains:
        domain_benchmarks.append("- **Auth endpoints**: Login/register throughput under concurrent load")
    if config.tech_stack.databases:
        dbs = ", ".join(config.tech_stack.databases)
        domain_benchmarks.append(f"- **Database ({dbs})**: Query performance for critical paths, connection pool saturation")
    if "redis" in [d.lower() for d in config.tech_stack.databases]:
        domain_benchmarks.append("- **Redis caching**: Cache hit/miss ratio impact on response times")
    if "docker" in [i.lower() for i in config.tech_stack.infrastructure] or "aws" in [i.lower() for i in config.tech_stack.infrastructure]:
        infra = ", ".join(config.tech_stack.infrastructure) if config.tech_stack.infrastructure else "cloud"
        domain_benchmarks.append(f"- **Infrastructure ({infra})**: Container resource utilization, auto-scaling triggers")

    domain_section = ""
    if domain_benchmarks:
        dm_text = "\n".join(f"    {b}" for b in domain_benchmarks)
        domain_section = f"\n    ## Domain-Specific Benchmarks\n\n{dm_text}\n"

    # Agent coordination
    agent_section = ""
    coord_agents: list[str] = []
    if "qa-engineer" in agents:
        coord_agents.append("- **qa-engineer**: Validate benchmark tests cover acceptance criteria")
    if "devops-specialist" in agents:
        coord_agents.append("- **devops-specialist**: Infrastructure provisioning for load tests")
    if "backend-developer" in agents:
        coord_agents.append("- **backend-developer**: Implement performance fixes identified by benchmarks")
    if "architect" in agents:
        coord_agents.append("- **architect**: Review architecture implications of performance findings")
    if coord_agents:
        coord_text = "\n".join(f"    {a}" for a in coord_agents)
        agent_section = f"\n    ## Agent Coordination\n\n{coord_text}\n"

    non_neg = _non_negotiables_section(config)

    # Build benchmark commands section based on project type
    bench_commands: list[str] = []
    if has_web and not is_cli:
        bench_commands.append(
            "### Load Testing (API)\n"
            "    ```bash\n"
            "    # Quick benchmark with hey\n"
            "    hey -n 1000 -c 50 http://localhost:8000/api/endpoint\n"
            "\n"
            "    # Extended benchmark with wrk\n"
            "    wrk -t4 -c100 -d30s http://localhost:8000/api/endpoint\n"
            "\n"
            "    # Scripted scenarios with k6\n"
            "    k6 run benchmarks/load-test.js\n"
            "    ```"
        )
    lang_label = "Python" if "python" in [l.lower() for l in config.tech_stack.languages] else "Application"
    bench_commands.append(
        f"### Profiling ({lang_label})\n"
        "    ```bash\n"
        "    # CPU profiling\n"
        "    python -m cProfile -o profile.out -m <module>\n"
        "    snakeviz profile.out\n"
        "\n"
        "    # Memory profiling\n"
        "    mprof run python -m <module>\n"
        "    mprof plot\n"
        "    ```"
    )
    if has_frontend:
        bench_commands.append(
            "### Frontend Performance\n"
            "    ```bash\n"
            "    # Lighthouse CI\n"
            "    npx lighthouse http://localhost:3000 --output=json --output-path=./benchmark-results.json\n"
            "\n"
            "    # Bundle analysis\n"
            "    npx webpack-bundle-analyzer stats.json\n"
            "    ```"
        )
    bench_cmd_text = "\n\n    ".join(bench_commands)

    return f"""\
    ---
    name: benchmark
    description: "Run performance benchmarks and track KPIs against targets"
    argument-hint: "[benchmark-suite]"
    ---

    # Performance Benchmark

    > {_domain_context(config)}
    > Stack: {tech}
    {kpi_section}{domain_section}
    ## Benchmark Workflow

    1. **Establish baseline**: Run benchmarks on current main branch
    2. **Implement changes**: Make performance improvements
    3. **Re-measure**: Run the same benchmarks on the feature branch
    4. **Compare**: Calculate percentage change for each KPI
    5. **Report**: Include before/after numbers in PR description

    ## Benchmark Commands

    {bench_cmd_text}
    {non_neg}{agent_section}
    ## Reporting

    Include in PR description:
    | Metric | Before | After | Change |
    |--------|--------|-------|--------|
    | p50 latency | 45ms | 32ms | -29% |
    | p95 latency | 120ms | 85ms | -29% |
    | Memory | 256MB | 248MB | -3% |

    $ARGUMENTS
    """


def _agent_init_skill(config: ForgeConfig) -> str:
    """Generate the agent-init skill for startup ceremony."""
    anchor_interval = config.compaction.anchor_interval_minutes

    return f"""\
    ---
    name: agent-init
    description: "Agent startup ceremony — fresh start, resume from checkpoint, or auto-detect"
    argument-hint: "[fresh|resume|detect]"
    ---

    # Agent Initialization

    > Lifecycle ceremony — applies to all agents regardless of project type.

    Full startup ceremony for agent lifecycle management.

    ## Modes

    Parse first word of `$ARGUMENTS` to determine mode. Default: `detect`.

    ### `detect` — Auto-Detect Mode (DEFAULT)

    1. Determine your agent type from your instruction file name
    2. Check if `.forge/checkpoints/{{your-agent-type}}/` directory exists
    3. Look for any `.json` checkpoint file in that directory
    4. If checkpoint found → run **resume** flow below
    5. If no checkpoint → run **fresh** flow below

    ### `fresh` — Fresh Start

    1. **Confirm identity**: Note your agent type from your instruction file
    2. **Read instruction file**: Load `.claude/agents/{{your-agent-type}}.md` in full
    3. **Read CLAUDE.md**: Load the project root `CLAUDE.md` for team context
    4. **Choose a name**: Follow the Agent Naming Protocol from your instruction file
    5. **Create checkpoint directory**: `mkdir -p .forge/checkpoints/{{your-agent-type}}/`
    6. **Save first checkpoint**: Run `/checkpoint save` with your chosen name, initial context_summary, and handoff_notes describing your plan
    7. **Write context anchor**: Create `.forge/checkpoints/{{your-agent-type}}/{{your-name}}.context-anchor.md` with:
       - Current task (initial assignment)
       - Key decisions (none yet)
       - Active files (instruction file, CLAUDE.md)
       - Next actions (your plan)
       - Mental model (initial understanding)
    8. **Team Leader only**: Also read `team-init-plan.md` and `.forge/session.json`

    ### `resume` — Resume from Checkpoint

    1. **Confirm identity**: Note your agent type from your instruction file
    2. **Read instruction file**: Load `.claude/agents/{{your-agent-type}}.md` (may have been updated)
    3. **Read CLAUDE.md**: Load project root `CLAUDE.md`
    4. **Load checkpoint**: Run `/checkpoint load`
    5. **Read context anchor**: Load `.forge/checkpoints/{{your-agent-type}}/{{your-name}}.context-anchor.md`
    6. **Re-read essential files**: From checkpoint's `essential_files` list (max 10 files). If `essential_files` is empty, fall back to the last 5 entries in `files_modified`
    7. **Check git status**: Verify your branches and files still exist
    8. **Review handoff_notes**: Your past self left you instructions — follow them
    9. **Team Leader only**: Also read `team-init-plan.md` and `.forge/session.json`, reconstruct agent tree

    ## Context Anchor Format

    Write to `.forge/checkpoints/{{your-agent-type}}/{{your-name}}.context-anchor.md`:

    ```markdown
    # Context Anchor — {{your-name}} ({{your-agent-type}})
    Updated: {{ISO-timestamp}}

    ## Current Task
    {{what you are working on right now}}

    ## Key Decisions
    {{decisions made this session with brief reasoning}}

    ## Active Files
    {{files you are actively working with — max 10}}

    ## Blockers
    {{anything blocking progress}}

    ## Next Actions
    {{ordered list of what to do next}}

    ## Mental Model
    {{2-5 sentences summarizing your understanding of the project state}}

    ## Essential Files
    {{list of files critical to reload on resume — max 10}}
    ```

    Update this anchor every {anchor_interval} minutes during work.

    $ARGUMENTS
    """


def _respawn_skill(config: ForgeConfig) -> str:
    """Generate the respawn skill for parent agents."""
    return f"""\
    ---
    name: respawn
    description: "Respawn a child agent after compaction with preserved context"
    argument-hint: "<agent-type> <agent-name>"
    ---

    # Respawn Agent

    > Lifecycle ceremony — parent runs this when a child returns after compaction.

    Parent runs this when a child agent returns with a compaction handoff.

    ## Arguments

    - **agent-type**: First word of `$ARGUMENTS` (e.g., `backend-developer`)
    - **agent-name**: Second word of `$ARGUMENTS` (e.g., `Nova`)

    ## Steps

    1. **Validate child checkpoint exists**: Check `.forge/checkpoints/{{agent-type}}/{{agent-name}}.json`
       - If not found, report error and abort
       - If found, verify it was updated recently (within last 30 minutes)

    2. **Reset token tracking**: Delete `.forge/checkpoints/{{agent-type}}/{{agent-name}}.token-estimate` to reset the token counter to zero. Also delete `.forge/checkpoints/{{agent-type}}/{{agent-name}}.compaction-marker` if it exists.

    3. **Read child's context anchor**: Load `.forge/checkpoints/{{agent-type}}/{{agent-name}}.context-anchor.md`

    4. **Identify child's sub-agents (recursive hierarchy)**: Check `.forge/session.json` for any agents that list this child as parent
       - Note their status — they may need re-spawning too

    5. **Build respawn prompt**: Construct a comprehensive prompt including:
       - The child's instruction file from `.claude/agents/{{agent-type}}.md`
       - The checkpoint's `context_summary` and `handoff_notes`
       - The context anchor content
       - The checkpoint's `current_task`, `pending_tasks`, and `decisions_made`
       - List of `files_modified` and `branches` from the checkpoint
       - `compaction_count` from checkpoint (incremented)

    6. **Preserve the exact same name**: The respawned agent MUST use the exact same name as before. Include in spawn prompt: "You are being respawned after context compaction. Run `/agent-init resume` as your first action. Your name is {{agent-name}} — do NOT choose a new name. Preserve this exact name."

    7. **Spawn the agent**: Use the Agent tool with the respawn prompt

    8. **Verify respawn**: Confirm the child:
       - Preserved the same name (exact name match)
       - Ran `/agent-init resume`
       - Acknowledged its prior context

    9. **Log in checkpoint**: Update your own checkpoint's `sub_agents` list with the respawned agent

    10. **Register event**: Write agent_started event to `.forge/events/`

    ## Error Handling

    - If checkpoint is too old (>30 min), warn but proceed — stale context is better than no context
    - If context anchor is missing, proceed with checkpoint data only
    - If respawn fails, retry once, then escalate to Team Leader

    $ARGUMENTS
    """


def _handoff_skill(config: ForgeConfig) -> str:
    """Generate the handoff skill for structured agent handoffs."""
    return f"""\
    ---
    name: handoff
    description: "Structured handoff — complete, compaction, or blocked"
    argument-hint: "[complete|compaction|blocked] [description]"
    ---

    # Agent Handoff

    > Lifecycle ceremony — structured handoff for all agent lifecycle transitions.

    ## Modes

    Parse first word of `$ARGUMENTS` to determine mode.

    ### `complete` — Task Finished

    1. **Verify all tasks done**: Check your `pending_tasks` list is empty and all `completed_tasks` are verified
    2. **Verify sub-agents complete**: If you spawned sub-agents, confirm all have status `complete`
    3. **Final checkpoint save**: Run `/checkpoint save` with `status: "complete"`
       - Include comprehensive `handoff_notes` summarizing all work done
       - Include complete `context_summary` of final project state
    4. **Write context anchor**: Final `.forge/checkpoints/{{your-agent-type}}/{{your-name}}.context-anchor.md`
    5. **Produce handoff report**: Output a structured report:
       ```
       ## Handoff Report — {{your-name}} ({{your-agent-type}})

       **Status**: COMPLETE
       **Tasks Completed**: {{count}}
       **Files Modified**: {{list}}
       **Branches**: {{list}}
       **Key Decisions**: {{summary}}
       **Notes for Parent**: {{anything the parent agent needs to know}}
       ```

    ### `compaction` — Context Compaction Needed

    1. **Increment compaction_count** in your checkpoint data
    2. **Checkpoint save**: Run `/checkpoint save` — status stays `active` (NOT complete)
       - Include extra-detailed `handoff_notes` — your respawned self needs maximum context
       - Include `context_summary` capturing your complete mental model
       - Include `essential_files` list (max 10 most important files to reload)
    3. **Write context anchor**: Full `.forge/checkpoints/{{your-agent-type}}/{{your-name}}.context-anchor.md`
    4. **Produce handoff report**: Output a structured report:
       ```
       ## Handoff Report — {{your-name}} ({{your-agent-type}})

       **Status**: REQUESTING RESPAWN (compaction #{{}})
       **Current Task**: {{what you were working on}}
       **Progress**: {{percentage and description}}
       **Next Steps**: {{ordered list of what respawned self should do}}
       **Critical Context**: {{anything that would be lost without this handoff}}
       **Essential Files**: {{files to reload}}
       ```
    5. **Return to parent**: The parent will run `/respawn` to restart you with context

    ### `blocked` — Cannot Proceed

    1. **Checkpoint save**: Run `/checkpoint save` with `status: "stopped"`
       - Include detailed blocker description in `handoff_notes`
       - Include what you tried and why it failed
    2. **Write context anchor**: `.forge/checkpoints/{{your-agent-type}}/{{your-name}}.context-anchor.md`
    3. **Produce handoff report**:
       ```
       ## Handoff Report — {{your-name}} ({{your-agent-type}})

       **Status**: BLOCKED
       **Blocker**: {{description of what is blocking progress}}
       **Tried**: {{what you attempted to resolve it}}
       **Needs**: {{what would unblock you}}
       **Can Resume When**: {{conditions for resumption}}
       ```

    $ARGUMENTS
    """


def _context_reload_skill(config: ForgeConfig) -> str:
    """Generate the context-reload skill for context recovery."""
    anchor_interval = config.compaction.anchor_interval_minutes
    compaction_threshold = config.compaction.compaction_threshold_tokens

    return f"""\
    ---
    name: context-reload
    description: "Context recovery — reload files, write anchors, check staleness"
    argument-hint: "[reload|anchor|status]"
    ---

    # Context Reload

    > Lifecycle ceremony — context recovery and anchor management for all agents.

    Context management for long-running agent sessions.

    ## Sub-Commands

    Parse first word of `$ARGUMENTS` to determine action.

    ### `reload` — Full Context Recovery

    Use after context compaction or when context feels stale.

    1. **Read instruction file**: Load `.claude/agents/{{your-agent-type}}.md`
    2. **Read CLAUDE.md**: Load project root `CLAUDE.md`
    3. **Load checkpoint**: Run `/checkpoint load` to restore state
    4. **Read context anchor**: Load `.forge/checkpoints/{{your-agent-type}}/{{your-name}}.context-anchor.md`
    5. **Re-read essential files**: From checkpoint's `essential_files` list (max 10).
       If `essential_files` is empty, fall back to the last 5 entries from `files_modified`
    6. **Check git status**: Verify branches and working tree state
    7. **Resume from handoff_notes**: Follow the instructions your past self left
    8. **Save fresh checkpoint**: Run `/checkpoint save` to mark successful reload
    9. **Delete compaction marker**: Remove `.forge/checkpoints/{{your-agent-type}}/{{your-name}}.compaction-marker` if present

    ### `anchor` — Write Context Anchor

    Write/update your context anchor file. Do this every {anchor_interval} minutes.

    1. **Write context-anchor.md** to `.forge/checkpoints/{{your-agent-type}}/{{your-name}}.context-anchor.md`:
       - Current task and progress
       - Key decisions made this session
       - Active files (max 10 most relevant)
       - Current blockers
       - Next actions (ordered)
       - Mental model (2-5 sentences)
       - Essential files for reload (max 10)
    2. **Update essential_files** in your next checkpoint save

    ### `status` — Check Context Health

    Diagnose context freshness and recommend actions.

    1. **Check checkpoint staleness**: How old is your last checkpoint?
       - < 10 min: OK
       - 10-15 min: STALE — save soon
       - > 15 min: CRITICAL — save immediately
    2. **Check anchor staleness**: How old is your context anchor?
       - < {anchor_interval} min: OK
       - > {anchor_interval} min: STALE — run `/context-reload anchor`
    3. **Token estimate**: Check activity log size as a proxy
       - Log size * 4 = estimated tokens consumed
       - Threshold: {compaction_threshold:,} tokens
    4. **Recommendations**: Based on staleness and token usage:
       - If tokens near threshold: "Run `/handoff compaction` soon"
       - If checkpoint stale: "Run `/checkpoint save` now"
       - If anchor stale: "Run `/context-reload anchor` now"
       - If all fresh: "Context health is good"

    $ARGUMENTS
    """


def _checkpoint_skill(config: ForgeConfig) -> str:
    """Generate the checkpoint skill for session persistence."""
    non_neg = _non_negotiables_section(config, context="checkpoint")

    # Project-type-specific checkpoint frequency guidance
    if config.is_cli_project():
        checkpoint_freq = dedent("""\
        ### Checkpoint Frequency (CLI Project)

        - After each command/subcommand implementation is verified working
        - After each subcommand group is complete
        - After test suite passes for a command group
        - After CLI help text and error messages are finalized
        - After plugin/extension system milestone (if applicable)
        """)
    elif config.has_frontend_involvement() and config.has_web_backend():
        checkpoint_freq = dedent("""\
        ### Checkpoint Frequency (Full-Stack Project)

        - After each feature (API endpoint + UI component) is verified working
        - After visual verification / screenshot capture
        - After E2E test passes for a user flow
        - After API contract change is implemented on both sides
        - After authentication/authorization flow milestone
        """)
    elif config.has_web_backend():
        checkpoint_freq = dedent("""\
        ### Checkpoint Frequency (Web Backend Project)

        - After each API endpoint is implemented and tested
        - After database migration is applied and verified
        - After authentication/authorization flow milestone
        - After service integration is verified (external APIs, queues, etc.)
        - After load/performance test results are captured
        """)
    elif config.has_frontend_involvement():
        checkpoint_freq = dedent("""\
        ### Checkpoint Frequency (Frontend / Static Site)

        - After each page/component is implemented and visually verified
        - After build verification passes (SSG build, lighthouse audit)
        - After responsive design verification at key breakpoints
        - After accessibility audit milestone
        """)
    else:
        checkpoint_freq = dedent("""\
        ### Checkpoint Frequency

        - After each significant feature or module is complete
        - After test suite passes for a module
        - After integration milestone with external systems
        - Before starting any task expected to take >5 minutes
        """)

    # Strategy-specific behavior
    strategy = config.strategy.value
    if strategy == "auto-pilot":
        strategy_note = "Save checkpoints silently. No human notification needed."
    elif strategy == "micro-manage":
        strategy_note = "Announce each checkpoint save to the human with a brief summary of what was captured."
    else:
        strategy_note = "Save checkpoints silently. Mention checkpoint saves in status reports only."

    return f"""\
    ---
    name: checkpoint
    description: "Save, load, or manage agent checkpoint for session persistence and cross-session resume"
    argument-hint: "[save|load|check-stop|status]"
    ---

    # Agent Checkpoint Protocol

    > Lifecycle ceremony — session persistence for stop/resume across all project types.

    **Strategy ({strategy})**: {strategy_note}

    ## Commands

    ### `save` — Write Rich Checkpoint

    1. Determine your agent type from your instruction file (e.g., `backend-developer`, `team-leader`)
    2. Build the checkpoint JSON object with ALL of the following fields:
       - `version`: "1"
       - `agent_type`: your agent type
       - `agent_name`: your chosen name (MUST be consistent across ALL checkpoints — never change it)
       - `parent_agent`: agent type of your parent (null if you are Team Leader)
       - `spawned_at`: ISO timestamp of when you were first spawned
       - `updated_at`: current ISO timestamp
       - `status`: "active" (normal), "stopping" (stop signal received), "stopped" (work halted), "complete" (all tasks done)
       - `iteration`: current iteration number (integer)
       - `phase`: current phase — one of PLAN, EXECUTE, TEST, INTEGRATE, REVIEW, CRITIQUE, DECISION
       - `phase_progress_pct`: estimated progress within current phase (0-100)
       - `current_task`: object with {{id, description, jira_ticket, started_at, step_index, total_steps, step_description}} or null
       - `completed_tasks`: list of completed task objects (same schema as current_task)
       - `pending_tasks`: list of task description strings queued for later
       - `context_summary`: 2-5 sentences summarizing your current mental model, key state, and what you understand about the project so far
       - `decisions_made`: list of {{decision, reasoning, timestamp}} objects for every architectural/technical decision
       - `blockers`: list of current blockers or open questions
       - `recent_conversation`: last 30 significant conversation entries (skip routine file reads) — each as {{role, content (truncated to 500 chars), timestamp, tool_name}}
       - `conversation_summary`: summary of older conversation not in recent_conversation
       - `files_modified`: list of file paths you have modified
       - `files_created`: list of file paths you have created
       - `branches`: list of git branches you work on
       - `commits`: list of recent commit hashes by you
       - `sub_agents`: list of {{agent_type, agent_name, task, status}} for agents you've spawned
       - `cost_usd`: your estimated cost so far
       - `tool_call_count`: total tool calls this session
       - `error`: last error message if any, otherwise null
       - `handoff_notes`: detailed instructions for your future self — what to do next, what's in progress, what to watch out for
    3. Ensure checkpoint directory exists: `mkdir -p .forge/checkpoints/{{your-agent-type}}/`
    4. Write atomically: write to `.forge/checkpoints/{{your-agent-type}}/{{your-agent-name}}.json.tmp` first, then rename to `.forge/checkpoints/{{your-agent-type}}/{{your-agent-name}}.json`
    5. Verify the write succeeded by reading back the file

    ### `load` — Resume from Checkpoint

    1. Read `.forge/checkpoints/{{your-agent-type}}/{{your-agent-name}}.json`
    2. ADOPT the `agent_name` from the checkpoint — do NOT generate a new name
    3. Resume from `current_task.step_index` — do NOT restart completed work
    4. Re-read your instruction file from `.claude/agents/{{your-agent-type}}.md` (it may have been updated between sessions)
    5. Review `context_summary` and `decisions_made` to restore your mental model
    6. Review `handoff_notes` for specific next actions
    7. Check `sub_agents` — re-spawn any that were `active` with their checkpoint context injected into the spawn prompt
    8. Verify `files_modified` still exist and haven't been reverted (check git status)
    9. Verify `branches` still exist in git
    10. If your instruction file has changed since last session, adapt to new guidance while preserving your task state and decisions

    ### `check-stop` — Check for Stop Signal

    1. Check: does `.forge/STOP_REQUESTED` exist?
    2. If YES:
       a. Run `/checkpoint save` with `status: "stopping"`
       b. Commit all work-in-progress: `git add -A && git commit -m "wip({{your-agent-name}}): checkpoint before stop"`
       c. Update checkpoint `status` to `"stopped"` and save again
       d. Write detailed `handoff_notes` explaining exactly what to do when you resume
       e. If you have sub-agents, message each to stop and checkpoint
       f. Report to parent agent: "Checkpoint saved, stopping gracefully"
       g. STOP ALL WORK immediately
    3. If NO: Continue working normally

    ### `status` — Show Checkpoint State

    1. Read all checkpoint files in `.forge/checkpoints/` (recursive — search subdirectories)
    2. For each checkpoint, display:
       - Agent name and type
       - Status (active/stopping/stopped/complete)
       - Iteration and phase
       - Last updated timestamp and staleness
       - Current task description (if any)
       - Cost accumulated

    ## Checkpoint Discipline

    ### First Checkpoint (CRITICAL)

    Your FIRST action after reading your instruction file and choosing your name must be to run `/checkpoint save`. Do this BEFORE starting any real work. This initial checkpoint establishes your identity and makes crash recovery possible from the very start. If the session is interrupted before your first checkpoint, all context is lost.

    {checkpoint_freq}
    ### Universal Rules (NON-NEGOTIABLE)

    - Save your FIRST checkpoint within the first 5 tool calls after initialization
    - Save IMMEDIATELY after: task completion, phase transition, sub-agent spawn/complete, any significant decision
    - Save BEFORE: starting any task that will take >5 minutes
    - Maximum interval between checkpoints: 10 minutes — if you haven't saved in 10 minutes, save NOW
    - Check stop signal BEFORE: starting any new major task
    - ALWAYS include accurate `handoff_notes` — your future self depends on them
    - ALWAYS include a meaningful `context_summary` — this is the most critical field for resume quality
    - Your `agent_name` MUST be identical across every checkpoint you save — never change it
    - Checkpoint files live in `.forge/checkpoints/{{your-agent-type}}/{{your-agent-name}}.json` — never write them elsewhere
    {non_neg}
    $ARGUMENTS
    """
