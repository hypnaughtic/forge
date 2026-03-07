"""Generate reusable skills for .claude/skills/ directory."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from forge_cli.config_schema import ForgeConfig


def generate_skills(config: ForgeConfig, skills_dir: Path) -> None:
    """Generate reusable skill files based on project configuration."""
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Always generate status skill
    _write_skill(skills_dir / "team-status.md", _status_skill())

    # Always generate iteration skill
    _write_skill(skills_dir / "iteration-review.md", _iteration_review_skill())

    # Spawn agent skill (if sub-agent spawning enabled)
    if config.agents.allow_sub_agent_spawning:
        _write_skill(skills_dir / "spawn-agent.md", _spawn_agent_skill())

    # Atlassian skills
    if config.atlassian.enabled:
        _write_skill(skills_dir / "jira-update.md", _jira_update_skill(config))
        _write_skill(skills_dir / "sprint-report.md", _sprint_report_skill(config))

    # Smoke test skill
    _write_skill(skills_dir / "smoke-test.md", _smoke_test_skill())

    # Screenshot review skill (visual verification)
    _write_skill(skills_dir / "screenshot-review.md", _screenshot_review_skill())

    # PR workflow skill
    _write_skill(skills_dir / "create-pr.md", _pr_workflow_skill(config))

    # Release management skill
    _write_skill(skills_dir / "release.md", _release_management_skill(config))

    # Architecture review skill
    _write_skill(skills_dir / "arch-review.md", _arch_review_skill())


def _write_skill(path: Path, content: str) -> None:
    path.write_text(content)


def _status_skill() -> str:
    return dedent("""\
    ---
    name: team-status
    description: "Get a comprehensive status report of all active agents and current iteration"
    argument-hint: ""
    ---

    # Team Status Report

    Collect and present a comprehensive status report:

    1. **Current Iteration**: Number, phase, progress percentage
    2. **Active Agents**: List all spawned agents, their current tasks, and status
    3. **Blockers**: Any agents that are blocked and what they need
    4. **Completed Work**: Tasks finished in this iteration
    5. **Upcoming Work**: Next tasks in the pipeline
    6. **Integration Status**: Branch merge status, any conflicts

    Present this in a clean, formatted summary for the human.
    """)


def _iteration_review_skill() -> str:
    return dedent("""\
    ---
    name: iteration-review
    description: "Review current iteration deliverables and decide: proceed, rework, rollback, or escalate"
    argument-hint: "[iteration-number]"
    ---

    # Iteration Review

    Review the current iteration and make a DECISION:

    1. **Collect all deliverables** from this iteration
    2. **Verify against acceptance criteria** for each task
    3. **Check quality gates**:
       - All tests pass?
       - Code review completed?
       - Application starts and responds?
       - Coverage meets threshold?
    4. **Run smoke test** (use /smoke-test skill)
    5. **Decision**: PROCEED | REWORK | ROLLBACK | ESCALATE

    If PROCEED: tag the iteration as verified, plan next iteration.
    If REWORK: identify specific issues and route back to agents.
    If ROLLBACK: restore last verified tag.
    If ESCALATE: present situation to human with options.

    $ARGUMENTS
    """)


def _spawn_agent_skill() -> str:
    return dedent("""\
    ---
    name: spawn-agent
    description: "Spawn a new agent with the correct instruction file"
    argument-hint: "<agent-type> <task-description>"
    ---

    # Spawn Agent

    Spawn a new agent from the forge instruction files.

    **Agent type**: First word of $ARGUMENTS
    **Task**: Remaining words of $ARGUMENTS

    Steps:
    1. Read the instruction file from `.claude/agents/<agent-type>.md`
    2. Use the Agent tool to spawn a sub-agent with that instruction file as context
    3. Include the task description in the spawn prompt
    4. The sub-agent will follow all protocols defined in its instruction file

    Available agent types are listed in `.claude/agents/` directory.

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
    **Status transitions**: To Do → In Progress → In Review → Testing → Done

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


def _smoke_test_skill() -> str:
    return dedent("""\
    ---
    name: smoke-test
    description: "Run smoke tests to verify the application works end-to-end"
    argument-hint: ""
    ---

    # Smoke Test Protocol

    Verify the application actually works from a user's perspective.

    1. **Start the application**: Run the appropriate start command. Verify no startup errors.
    2. **Test backend**: For every API endpoint, make a real HTTP request. Check status codes and response bodies.
    3. **Test frontend**: Verify pages load, assets serve correctly, at least one user flow works.
    4. **Capture screenshots**: Take full-page screenshots of all UI pages using Playwright.
       Save to `docs/screenshots/smoke-test/`. Use the Read tool to verify visual correctness.
    5. **Test integrations**: Database connects, services communicate, full-stack operations work.
    6. **Report results**: List each test and its pass/fail status. Include screenshots as visual evidence.

    Any failure is a BLOCKER. Do not mark the iteration complete until all smoke tests pass.

    $ARGUMENTS
    """)


def _screenshot_review_skill() -> str:
    return dedent("""\
    ---
    name: screenshot-review
    description: "Capture and review screenshots of all key UI pages for iteration review"
    argument-hint: "[url-or-feature]"
    ---

    # Screenshot Review

    Capture a visual summary of the application's current state for iteration review.

    ## Steps

    1. **Start the application** if not already running
    2. **Identify key pages**: List all user-facing pages and critical UI states
    3. **Capture screenshots** using Playwright:
       - Desktop viewport (1280x720): `npx playwright screenshot --full-page http://localhost:{port}/path page-desktop.png`
       - Mobile viewport (375x812): `npx playwright screenshot --full-page --viewport-size=375,812 http://localhost:{port}/path page-mobile.png`
    4. **Capture state variants** for key pages:
       - Default/loaded state
       - Empty state (no data)
       - Error state (if triggerable)
       - Loading state (if capturable)
    5. **Save all screenshots** to `docs/screenshots/{iteration}/`
    6. **View each screenshot** using the Read tool — verify visual correctness
    7. **Compile summary**: List each page with its screenshot path and visual assessment

    ## Output

    Present to Team Leader:
    - Page name → screenshot path → visual status (OK / ISSUE)
    - Any visual issues found with description
    - Overall visual quality assessment

    This helps the human understand what was built without starting the app themselves.

    $ARGUMENTS
    """)


def _pr_workflow_skill(config: ForgeConfig) -> str:
    jira_step = ""
    if config.atlassian.enabled:
        project_key = config.atlassian.jira_project_key or "PROJ"
        jira_step = f"""
    4. **Reference Jira ticket** in the PR description: `Closes {project_key}-<number>`
    5. **Verify branch name** follows convention: `<type>-{project_key}-<N>-<description>`"""
    else:
        jira_step = """
    4. **Reference task ID** in the PR description
    5. **Verify branch name** follows convention: `<type>/<agent-name>/<task-id>-<description>`"""

    return dedent(f"""\
    ---
    name: create-pr
    description: "Create a Pull Request following the team's workflow conventions"
    argument-hint: "<target-branch> [title]"
    ---

    # Create Pull Request

    Create a PR following the team's workflow conventions.

    ## Steps

    1. **Verify all changes are committed** and pushed to the remote branch
    2. **Run tests** locally — ensure they pass before creating the PR
    3. **Create the PR** using `gh pr create` with:
       - Clear, descriptive title
       - Summary of changes in the description
       - Target branch (parent feature branch or default branch){jira_step}
    6. **Request review** from the appropriate lead agent
    7. **Wait for approval** — at least one approval required before merge

    ## PR Size Guidelines

    - **Big PRs** (new features, cross-cutting changes): reviewer should test the feature end-to-end
    - **Small PRs** (docs, config, bug fixes): code review is sufficient

    $ARGUMENTS
    """)


def _release_management_skill(config: ForgeConfig) -> str:
    confluence_step = ""
    if config.atlassian.enabled:
        confluence_step = """
    5. **Update Confluence** release notes page with the release summary
    6. **Update Jira** — mark the release version as released, move remaining tickets to next version"""

    return dedent(f"""\
    ---
    name: release
    description: "Create a GitHub release with tag and release notes"
    argument-hint: "<version-tag> [title]"
    ---

    # Release Management

    Create a GitHub release after a major milestone.

    ## Steps

    1. **Verify readiness**: All tests pass, smoke tests pass, iteration is verified
    2. **Create git tag**: `git tag v<version>` (e.g., `v1.0.0`, `v0.1.0-alpha`)
    3. **Push tag**: `git push origin v<version>`
    4. **Create GitHub release**: `gh release create v<version> --generate-notes --title "<title>"`{confluence_step}

    ## Version Numbering

    - Major releases: `v1.0.0`, `v2.0.0` — breaking changes or major milestones
    - Minor releases: `v1.1.0`, `v1.2.0` — new features
    - Patch releases: `v1.0.1`, `v1.0.2` — bug fixes

    $ARGUMENTS
    """)


def _arch_review_skill() -> str:
    return dedent("""\
    ---
    name: arch-review
    description: "Review code for architecture compliance"
    argument-hint: "<file-or-directory>"
    ---

    # Architecture Review

    Review the specified code for architecture compliance.

    Check for:
    1. **Vendor-agnostic interfaces**: External deps behind abstractions?
    2. **Layer separation**: Business logic separate from transport/persistence?
    3. **API contract compliance**: Endpoints match the defined contracts?
    4. **Error handling**: Consistent error format, no leaked internals?
    5. **Security basics**: Input validation, no hardcoded secrets, auth checks?
    6. **Code organization**: Follows project structure conventions?

    Report findings as: BLOCKER | WARNING | NOTE with specific file and line references.

    $ARGUMENTS
    """)
