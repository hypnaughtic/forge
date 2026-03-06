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
