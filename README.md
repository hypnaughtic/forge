# Forge

> Config-driven project initializer for Claude Code CLI agent teams.

Forge reads a `forge.yaml` and generates customized agent instruction files,
CLAUDE.md, skills, team-init-plan.md, and strategy-enforced permissions for your
project workspace. Configure once, then let Claude Code agents build your project
with precision.

---

## Installation

### Homebrew

```bash
brew tap Rushabh1798/forge
brew install forge-init
forge --version
```

### pip

```bash
pip install -e .
forge --version
```

### Development

```bash
git clone https://github.com/Rushabh1798/forge.git && cd forge
pip install -e ".[test]"
```

---

## Quick Start

### Option A — Interactive setup (recommended)

```bash
forge init
# Follow the 8-step wizard (use Up/Down arrows to navigate between steps)
# Confirm and generate

forge start
# Launches Claude with the team init prompt — fully interactive session
```

### Option B — Config file

```bash
# 1. Start from the example config
cp examples/forge-config.yaml .forge/forge.yaml
# Edit .forge/forge.yaml with your project details

# 2. Generate files
forge generate --project-dir ./my-project

# 3. Start building
forge start
# OR: cd my-project && claude
# Then tell Claude: "Read team-init-plan.md and initialize the team"
```

---

## CLI Commands

Forge provides seven commands that form a complete lifecycle:

```text
forge init → forge generate → forge refine → forge eval → forge start
forge stop → (edit config, refine, etc.) → forge resume
```

### `forge init`

Interactively build a `forge.yaml` configuration through an 8-step wizard.

```bash
forge init                         # Save to .forge/forge.yaml (default)
forge init --output my-config.yaml # Custom output path
```

| Step | What it configures |
|------|--------------------|
| 1 | Project description, requirements, plan file, context files, type |
| 2 | Quality mode (mvp / production-ready / no-compromise) |
| 3 | Execution strategy (auto-pilot / co-pilot / micro-manage) |
| 4 | Tech stack (languages, frameworks, databases, infrastructure) |
| 5 | Team configuration (profile, sub-agents, naming, cost cap) |
| 6 | Atlassian integration (Jira/Confluence) |
| 7 | LLM Gateway |
| 8 | Non-negotiables (absolute requirements) |

**Navigation:** Use Up arrow to go back to the previous step, Down arrow or Enter
to proceed. Full cursor editing (Home, End, arrow keys) in all text prompts.

After all steps, Forge shows a summary for confirmation, saves the config file,
and optionally runs generation immediately.

### `forge generate`

Generate agent instruction files from a `forge.yaml` config.

```bash
forge generate                                # Auto-detect config
forge generate --config .forge/forge.yaml     # Explicit config path
forge generate --project-dir ./my-project     # Custom output directory
forge generate --validate-only                # Validate config without generating
forge generate -v                             # Verbose logging
```

Config auto-detection order:

1. `.forge/forge.yaml` (canonical)
2. `forge.yaml` (project root)
3. `.forge/forge-config.yaml` (legacy)
4. `forge-config.yaml` (legacy)

Backward compatibility: `forge --config .forge/forge.yaml` routes to `generate`.

### `forge refine`

Refine generated files using LLM scoring and iterative improvement. Each `.md`
file is scored against weighted quality criteria and iteratively improved until
it meets a configurable threshold (default 90%).

```bash
forge refine                                  # Auto-detect config
forge refine --config .forge/forge.yaml       # Explicit config path
forge refine --project-dir ./my-project       # Custom project directory
forge refine -v                               # Verbose logging
```

Requires `llm-gateway`: `pip install -e ".[refinement]"`

### `forge start`

Launch an interactive Claude CLI session with the team init prompt.

```bash
forge start                                   # Auto-detect, auto-detect tmux
forge start --config .forge/forge.yaml        # Explicit config path
forge start --project-dir ./my-project        # Custom project directory
forge start --tmux                            # Force tmux split-pane session
forge start --no-tmux                         # Force direct Claude session
```

When tmux is available, creates a named session (`forge-<project-name>`) for
monitoring agent activity in split panes. Falls back to direct Claude session
if tmux is not installed.

### `forge eval`

Evaluate generated files against 350+ quality assertions (deterministic + LLM-judged).
Results are saved as benchmark reports in `.forge/`.

```bash
forge eval                                        # Full eval (deterministic + LLM grading)
forge eval --config .forge/forge.yaml             # Explicit config path
forge eval --project-dir ./my-project             # Custom project directory
forge eval --no-llm                               # Deterministic checks only (no LLM cost)
forge eval --optimize-descriptions                # Also optimize skill trigger descriptions
forge eval -v                                     # Verbose logging
```

Eval checks include: `contains`, `not_contains`, `regex`, `section_present`,
`frontmatter_field`, `config_fidelity`, and `llm_judge`. Cases have applicability
predicates (`is_cli_project`, `has_web_backend`, `atlassian_enabled`, etc.) so only
relevant assertions run for each project type.

### `forge stop`

Signal all running agents to gracefully stop and checkpoint their state.

```bash
forge stop                                        # Gracefully stop all agents
forge stop --project-dir ./my-project             # Custom project directory
forge stop --timeout 120                          # Wait up to 120s for agents to checkpoint
```

Agent checkpoints are saved to `.forge/checkpoints/` and can be resumed later.

### `forge resume`

Resume a previously stopped session from checkpoints.

```bash
forge resume                                      # Resume from last checkpoint
forge resume --config .forge/forge.yaml           # Explicit config path
forge resume --project-dir ./my-project           # Custom project directory
forge resume --tmux                               # Resume in a tmux session
forge resume --no-tmux                            # Force direct Claude session
```

On resume, Forge detects file changes since the last stop and re-reads the latest
instruction files from `.claude/agents/`.

---

## Configuration

All configuration lives in a single `forge.yaml` file, stored in `.forge/` by default.
See [`examples/forge-config.yaml`](examples/forge-config.yaml) for a comprehensive
annotated example covering every option.

### Minimal example

```yaml
project:
  description: "E-commerce platform"
  context_files:
    - PLAN.md                    # Forge derives requirements from these files
  type: new

mode: production-ready
strategy: co-pilot
```

### Full example

```yaml
project:
  description: "E-commerce platform"
  context_files:                 # Files or directories for project context
    - PLAN.md                    # Scanned for .md, .txt, .yaml files
    - specs/
  plan_file: PLAN.md             # Authoritative implementation blueprint
  type: new                      # new | existing
  existing_project_path: ./app   # Path if type=existing
  directory: .                   # Project directory (default: .)

mode: production-ready           # mvp | production-ready | no-compromise
strategy: co-pilot               # auto-pilot | co-pilot | micro-manage

cost:
  max_development_cost: 50       # USD cap

agents:
  team_profile: auto             # auto | lean | full | custom
  include: []                    # agent list for custom profile
  exclude: []                    # agents to remove from profile
  additional: []                 # extra agents to add
  allow_sub_agent_spawning: true
  custom_instructions:
    backend-developer: "Use PostgreSQL, not SQLite"

tech_stack:
  languages: [typescript, python]
  frameworks: [react, fastapi]
  databases: [postgresql]
  infrastructure: [docker]

atlassian:
  enabled: true
  jira_project_key: ECOM
  jira_base_url: "https://your-domain.atlassian.net"
  confluence_space_key: ECOM
  confluence_base_url: "https://your-domain.atlassian.net/wiki"
  create_sprint_board: true      # Auto-create Jira sprint board
  create_confluence_space: true  # Auto-create Confluence space
  scrum_ceremonies: true         # Enable sprint ceremonies tracking

agent_naming:
  enabled: true
  style: creative                # creative | functional | codename

llm_gateway:
  enabled: true
  local_claude_model: "claude-sonnet-4-20250514"
  enable_local_claude: true
  cost_tracking: true

git:
  ssh_key_path: "~/.ssh/id_ed25519"  # SSH auth for git (empty = disabled)

non_negotiables:
  - "All APIs must require authentication"
  - "100% test coverage on core business logic"
  - "No raw SQL queries — use ORM exclusively"

compaction:
  compaction_threshold_tokens: 100000  # Token count triggering compaction
  enable_context_anchors: true         # Periodic context anchor writes
  anchor_interval_minutes: 15          # Minutes between anchor updates

refinement:
  enabled: false                 # default: false
  provider: local_claude         # local_claude | anthropic
  model: claude-opus-4-6
  max_tokens: 8192               # max tokens per LLM call
  score_threshold: 90            # 0-100, files must score >= this
  max_iterations: 5              # max refine loops per file
  max_concurrency: 0             # 0 = all files in parallel (default)
  timeout_seconds: 300           # per-LLM-call timeout
  cost_limit_usd: 10.0           # stop if cumulative cost exceeds this
```

### Plan file vs context files

- **`plan_file`**: An authoritative implementation blueprint. When set, generated files
  instruct agents to follow the plan exactly — phases, milestones, architecture, and
  sequencing. The agent team executes the plan using parallel agentic collaboration.

- **`context_files`**: Reference material (specs, previous discussions, architecture docs).
  Forge summarizes these into `.forge/project-context.md` and uses the context to generate
  more tailored agent instructions. Accepts individual files or directories (scanned
  recursively for `.md`, `.txt`, `.yaml`, `.yml`, `.rst` files).

### Refinement (LLM-powered)

After generating files, Forge can optionally refine them using an LLM to improve
quality. Each `.md` file is scored against weighted quality criteria and iteratively
improved until it meets a configurable threshold (default 90%). All files are refined
in parallel for fast turnaround (~4-7 minutes for 18 files with `local_claude`).

Refinement reports are saved to `.forge/refinement-report.json` and
`.forge/refinement-report.md` with per-file iteration details, suggestions,
changes, scores, and next scope of improvement.

**Scoring criteria** (weighted):

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Completeness | 25% | Covers all role responsibilities and protocols |
| Config fidelity | 25% | Accurately reflects project config (mode, stack, agents) |
| Specificity | 20% | Uses project-specific details, not generic placeholders |
| Clarity | 20% | Clear, actionable instructions an AI agent can follow |
| Consistency | 10% | Internally consistent, no contradictions |

### `non_negotiables`

A list of absolute requirements injected into every generated file:

- **Team Leader**: Enforcement framing — rejects work that violates these, includes compliance checks in every iteration review
- **Critic**: Evaluation framing — every critique includes a Non-Negotiable Compliance section scoring each rule as PASS/FAIL
- **All other agents**: Compliance framing — must verify compliance before reporting work as complete

When the list is empty (default), no non-negotiables section appears in generated files.

### Mode

| Mode | Critic Pass | Testing | Default Team |
|------|------------|---------|--------------|
| `mvp` | 70% | Happy-path + smoke | Lean (8 agents) |
| `production-ready` | 90% | >90% coverage + integration | Full (12 agents) |
| `no-compromise` | 100% | Exhaustive + chaos | Full (12 agents) |

### Strategy

| Strategy | Tool Access | Agent Behavior | `.claude/settings.json` |
|----------|------------|----------------|------------------------|
| `auto-pilot` | All tools allowed | Full autonomy — all decisions made by agents | Generated (all tools) |
| `co-pilot` | All tools allowed | Full implementation autonomy — agents only ask human for architecture/scope/domain decisions not covered by requirements | Generated (all tools) |
| `micro-manage` | Default prompting | Every significant decision presented to human | **Not generated** |

**Co-pilot** is ideal when you want agents to build freely but consult you on project-level
questions like "monolith vs microservices?", "which payment provider?", or "should we support
multi-tenancy?". Agents will never ask permission to edit files, run tests, or execute commands.

### Team Profiles

- **lean** (8 agents): team-leader, research-strategist, architect, backend-developer, frontend-engineer, qa-engineer, devops-specialist, critic
- **full** (12 agents): Adds frontend-designer, frontend-developer, security-tester, performance-engineer, documentation-specialist
- **auto**: lean for MVP, full for production-ready and no-compromise
- **custom**: Explicit agent list via `agents.include`

Atlassian integration automatically adds a scrum-master agent.

---

## Generated Files

```text
my-project/
  CLAUDE.md                          # Team Leader context
  team-init-plan.md                  # Bootstrap document for first session
  .claude/
    agents/
      team-leader.md
      backend-developer.md
      ...                            # One file per active agent
    skills/
      create-pr.md
      release.md
      arch-review.md
      smoke-test.md
      screenshot-review.md
      iteration-review.md
      team-status.md
      checkpoint.md                  # Checkpoint/resume skill
      spawn-agent.md                 # When sub-agent spawning enabled
      jira-update.md                 # When Atlassian enabled
      sprint-report.md               # When Atlassian enabled
    mcp.json                         # MCP server configuration
    settings.json                    # Strategy-enforced permissions (auto-pilot/co-pilot)
  .forge/
    forge.yaml                       # Project configuration
    session.json                     # Session state (created by forge start)
    project-context.md               # Summarized project context (if context_files set)
    refinement-report.json           # Refinement report (if refinement ran)
    refinement-report.md             # Human-readable refinement report
    benchmark.json                   # Eval benchmark data (if eval was run)
    benchmark.md                     # Eval benchmark report (human-readable)
    token-report.json                # Per-agent context budget (exact token counts)
    checkpoints/                     # Agent checkpoints (hierarchical: type/name.json)
      team-leader/
        agent-name.json
      backend-developer/
        agent-name.json
    events/                          # Event inbox (atomic per-event JSON files)
      *.json
    events-archive.jsonl             # Archived events (appended on materialization)
    hooks/                           # Hook scripts for automatic checkpoint enforcement
      *.sh
    scripts/                         # Helper scripts (identity resolution, etc.)
      resolve_identity.py
  .env.example                       # Required environment variables
```

---

## Architecture

### Source modules

```text
forge_cli/
  __init__.py                  # Package version
  main.py                     # CLI entry point (click commands: init, generate, refine, eval, start, stop, resume)
  config_schema.py             # Pydantic config models, project-type detection, team resolution
  config_loader.py             # YAML loading, config auto-detection, round-trip support
  init_wizard.py               # Interactive 8-step wizard using prompt_toolkit
  progress.py                  # Rich progress displays (generation + refinement)
  checkpoint.py                # Checkpoint/resume system for multi-agent sessions
  generators/
    orchestrator.py            # Top-level generate_all() and run_refinement() coordination
    agent_files.py             # Agent instruction templates (project-type + domain-aware)
    skills.py                  # Skill templates (project-type + domain-aware)
    claude_md.py               # CLAUDE.md generation
    team_init_plan.py          # team-init-plan.md generation
    settings_config.py         # .claude/settings.json generation
    mcp_config.py              # .claude/mcp.json + .env.example generation
    context_summarizer.py      # Context file collection + LLM summarization
    refinement.py              # LLM scoring + iterative refinement loop
    hooks.py                   # Hook scripts for checkpoint enforcement
  evals/
    __init__.py
    eval_cases.py              # 350+ eval case definitions with applicability predicates
    eval_runner.py             # Eval execution engine (deterministic + LLM-judged)
    grading.py                 # LLM grading logic
    benchmark.py               # Benchmark aggregation and reporting
    description_optimizer.py   # Skill description optimization via trigger/non-trigger queries
```

### Key design patterns

- **Config-driven**: All output is derived from `ForgeConfig` (Pydantic model)
- **Project-type detection**: `has_frontend_involvement()`, `has_web_backend()`, `is_cli_project()` tailor templates
- **Domain-aware templates**: Agent and skill generators produce context-specific content based on tech stack, team roster, and project description
- **Strategy enforcement**: `settings_config.py` generates tool permissions; agent templates include strategy-specific behavioral guidance
- **Dependency injection**: `generate_all(config, llm_provider=...)` supports `FakeLLMProvider` for testing

---

## Development & Testing

### Running tests

```bash
# Run full test suite (dry-run mode, no LLM needed)
FORGE_TEST_DRY_RUN=1 python -m pytest tests/ --cov=forge_cli -v

# Run unit tests only (fast, ~2s)
python -m pytest tests/test_generators.py tests/test_config_schema.py \
  tests/test_config_loader.py tests/test_refinement.py \
  tests/test_main.py tests/test_progress.py -v

# Run integration tests (dry-run, uses FakeLLMProvider)
FORGE_TEST_DRY_RUN=1 python -m pytest tests/test_integration.py -v

# Run eval tests
FORGE_TEST_DRY_RUN=1 python -m pytest tests/test_eval_runner.py tests/test_eval_benchmark.py -v

# Run checkpoint/resume tests
python -m pytest tests/test_checkpoint.py tests/test_checkpoint_skill.py \
  tests/test_cli_checkpoint_commands.py -v

# Run context quality tests
FORGE_TEST_DRY_RUN=1 python -m pytest tests/test_context_quality.py -v

# Run e2e tests (checkpoint scenarios)
python -m pytest tests/e2e/ -v

# Run refinement tests with real LLM (requires local_claude or ANTHROPIC_API_KEY)
FORGE_TEST_DRY_RUN=0 python -m pytest tests/test_integration.py -v \
  -k "Refinement" --timeout=1200

# Run context quality LLM-scored tests (requires real LLM)
FORGE_TEST_DRY_RUN=0 python -m pytest tests/test_context_quality.py -v \
  -k "LLM" --timeout=300
```

### Test structure

| File | Scope | Count | LLM? |
|------|-------|-------|------|
| `test_generators.py` | Generator unit tests (agents, CLAUDE.md, skills, settings) | 89 | No |
| `test_config_schema.py` | Config schema validation and project-type detection | 33 | No |
| `test_config_loader.py` | YAML loading, round-trip, auto-detection | 10 | No |
| `test_refinement.py` | Refinement unit tests (scoring, pipeline, FakeLLMProvider) | 100 | No |
| `test_init_wizard.py` | Init wizard steps, validation, CLI routing | 96 | No |
| `test_context_summarizer.py` | Context file collection and summarization | 31 | No |
| `test_main.py` | CLI commands (generate, refine, eval, start, stop, resume) | 24 | No |
| `test_progress.py` | Rich progress displays (generation + refinement) | 27 | No |
| `test_eval_runner.py` | Eval framework (cases, runner, grading, FakeLLMProvider) | 108 | No |
| `test_eval_benchmark.py` | Eval benchmark across 7 quality cases | 28 | Dry-run default |
| `test_checkpoint.py` | Checkpoint/resume system | 48 | No |
| `test_checkpoint_skill.py` | Checkpoint skill generation | 16 | No |
| `test_checkpoint_hierarchy.py` | Hierarchical checkpoint paths and validation | 7 | No |
| `test_cli_checkpoint_commands.py` | CLI stop/resume commands | 31 | No |
| `test_context_compaction.py` | Compaction detection, cooperative respawn, anchors | 90 | No |
| `test_deterministic_resume.py` | Deterministic agent naming and resume prompts | 7 | No |
| `test_event_inbox.py` | Event inbox atomic writes, materialization, archival | 17 | No |
| `test_ghost_detection.py` | Ghost/orphan agent detection in checkpoint tree | 7 | No |
| `test_session.py` | Session state I/O, event application, stop signals | 12 | No |
| `test_tokens.py` | Token counting, budget reporting, token report I/O | 11 | No |
| `test_integration.py` | Full pipeline, CLI end-to-end, strategy enforcement | 204 | Dry-run default |
| `test_co_planner.py` | Co-planner quality cases (generation, refinement, content) | 55 | Dry-run default |
| `test_context_quality.py` | Context derivation quality and passthrough | 18 | Partial (8 LLM-scored) |
| `e2e/test_scenario_*.py` | End-to-end checkpoint scenarios (23 files) | 32 | No |
| **Total** | | **1101** | |

The `FORGE_TEST_DRY_RUN` environment variable controls whether tests use a
`FakeLLMProvider` (instant, default) or real `local_claude` (requires
`llm-gateway` and Claude CLI). CI always runs in dry-run mode.

Coverage threshold: **90%** (enforced in `pyproject.toml`, CI, and pre-commit).

### Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

Hooks run before every commit (identical test suite to CI, dry-run mode):

1. **yamllint** — YAML syntax and style
2. **markdownlint** — Markdown formatting
3. **pytest** — All 27 test files + 23 e2e scenarios with `--cov-fail-under=90` (FORGE_TEST_DRY_RUN=1)

### CI pipeline

GitHub Actions runs on every push and PR:

- YAML lint, Markdown lint
- Full test suite with 90% coverage gate (Python 3.11 + 3.12, Ubuntu + macOS)

---

## License

MIT — see [LICENSE](LICENSE) for details.
