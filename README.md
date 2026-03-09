# Forge

> Config-driven project initializer for Claude Code CLI agent teams.

Forge reads a `forge-config.yaml` and generates customized agent instruction files,
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
# Follow the 8-step wizard → confirm → generate
cd my-project
claude
# Tell Claude: "Read team-init-plan.md and initialize the team"
```

### Option B — Config file

```bash
# 1. Start from the example config
cp examples/forge-config.yaml forge-config.yaml
# Edit forge-config.yaml with your project details

# 2. Generate files
forge --config forge-config.yaml --project-dir ./my-project

# 3. Start building
cd my-project
claude
# Tell Claude: "Read team-init-plan.md and initialize the team"
```

### Other commands

```bash
# Validate config without generating files
forge --config forge-config.yaml --validate-only

# Generate with LLM-powered refinement
forge --config forge-config.yaml --project-dir ./my-project --refine
```

---

## Interactive Setup (`forge init`)

`forge init` walks you through building a `forge-config.yaml` interactively:

| Step | What it configures |
|------|--------------------|
| 1 | Project description, requirements, type (new/existing) |
| 2 | Quality mode (mvp / production-ready / no-compromise) |
| 3 | Execution strategy (auto-pilot / co-pilot / micro-manage) |
| 4 | Tech stack (languages, frameworks, databases, infrastructure) |
| 5 | Team configuration (profile, sub-agents, naming, cost cap) |
| 6 | Atlassian integration (Jira/Confluence) |
| 7 | LLM Gateway |
| 8 | Non-negotiables (absolute requirements) |

After all steps, Forge shows a summary for confirmation, saves the config file,
and optionally runs generation immediately. No YAML editing required.

```bash
forge init
forge init --output my-config.yaml   # custom output path
```

---

## Configuration

All configuration lives in a single `forge-config.yaml` file.

See [`examples/forge-config.yaml`](examples/forge-config.yaml) for a comprehensive
annotated example covering every option.

### Minimal example

```yaml
project:
  description: "E-commerce platform"
  requirements: "Build a full-stack e-commerce platform with auth, product catalog, cart, and checkout"
  type: new

mode: production-ready
strategy: co-pilot
```

### Full example

```yaml
project:
  description: "E-commerce platform"
  requirements: "Build a full-stack e-commerce platform with auth, product catalog, cart, and checkout"
  type: new                      # new | existing

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

agent_naming:
  enabled: true
  style: creative                # creative | functional | codename

llm_gateway:
  enabled: true
  local_claude_model: "claude-sonnet-4-20250514"
  enable_local_claude: true
  cost_tracking: true

non_negotiables:
  - "All APIs must require authentication"
  - "100% test coverage on core business logic"
  - "No raw SQL queries — use ORM exclusively"

refinement:
  enabled: false                 # default: false
  provider: local_claude         # local_claude | anthropic
  model: claude-opus-4-6
  score_threshold: 90            # 0-100, files must score >= this
  max_iterations: 5              # max refine loops per file
  max_concurrency: 0             # 0 = all files in parallel (default)
  timeout_seconds: 180           # per-LLM-call timeout
  cost_limit_usd: 10.0           # stop if cumulative cost exceeds this
```

### Refinement (LLM-powered)

After generating files, Forge can optionally refine them using an LLM to improve
quality. Each `.md` file is scored against weighted quality criteria and iteratively
improved until it meets a configurable threshold (default 90%). All files are refined
in parallel for fast turnaround (~4–7 minutes for 18 files with `local_claude`).

**Scoring criteria** (weighted):

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Completeness | 25% | Covers all role responsibilities and protocols |
| Config fidelity | 25% | Accurately reflects project config (mode, stack, agents) |
| Specificity | 20% | Uses project-specific details, not generic placeholders |
| Clarity | 20% | Clear, actionable instructions an AI agent can follow |
| Consistency | 10% | Internally consistent, no contradictions |

CLI override:

```bash
# Force refinement on (overrides config)
forge --config forge-config.yaml --project-dir ./my-project --refine

# Force refinement off
forge --config forge-config.yaml --project-dir ./my-project --no-refine
```

Install the refinement dependency:

```bash
pip install -e ".[refinement]"
```

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
      spawn-agent.md                 # When sub-agent spawning enabled
      jira-update.md                 # When Atlassian enabled
      sprint-report.md               # When Atlassian enabled
    mcp.json                         # MCP server configuration
    settings.json                    # Strategy-enforced permissions (auto-pilot/co-pilot)
  .env.example                       # Required environment variables
```

---

## Development & Testing

```bash
# Run all tests (dry-run mode, no LLM needed)
make test

# Run unit tests only
python -m pytest tests/test_generators.py tests/test_config_schema.py \
  tests/test_config_loader.py tests/test_refinement.py -v

# Run integration tests (dry-run, uses FakeLLMProvider)
FORGE_TEST_DRY_RUN=1 python -m pytest tests/test_integration.py -v

# Run refinement tests with real LLM (requires local_claude)
FORGE_TEST_DRY_RUN=0 python -m pytest tests/test_integration.py -v \
  -k "Refinement" --timeout=1200

# Full CI mirror
make ci-local
```

### Test structure

| File | Scope | Count | LLM? |
|------|-------|-------|------|
| `test_generators.py` | Generator unit tests (agents, CLAUDE.md, skills, settings, etc.) | ~73 | No |
| `test_config_schema.py` | Config schema validation | ~15 | No |
| `test_config_loader.py` | YAML loading/round-trip | ~9 | No |
| `test_refinement.py` | Refinement unit tests (FakeLLMProvider) | ~20 | No |
| `test_integration.py` | Full pipeline, CLI, strategy enforcement, live Claude CLI tests | ~195 | Dry-run default |

The `FORGE_TEST_DRY_RUN` environment variable controls whether integration tests
use a `FakeLLMProvider` (instant, default) or real `local_claude` (requires
`llm-gateway` and Claude CLI). CI always runs in dry-run mode.

### Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

Hooks run yamllint, markdownlint, and pytest unit tests before every commit.

---

## License

MIT — see [LICENSE](LICENSE) for details.
