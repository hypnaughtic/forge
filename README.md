# Forge -- AI Software Forge

> A team of AI agents, powered by Claude Code, that collaborate to build your software.

Forge orchestrates a team of specialized AI agents -- each running in its own tmux
session with its own Claude Code instance -- to design, implement, test, and ship
software projects. Think of it as a virtual development team: a Team Leader decomposes
your requirements, an Architect designs the system, Backend and Frontend developers
write code, a QA Engineer tests everything, a Critic enforces quality gates, and a
DevOps Specialist wires up CI/CD and infrastructure.

You describe what you want to build, choose a quality mode and an execution strategy,
then run `./forge start`. The Team Leader spawns the appropriate agents, assigns tasks,
manages iteration cycles, and drives the project to completion -- while you watch,
guide, or step away entirely.

**How it works under the hood:**

- **Process isolation via tmux.** Each agent runs in its own tmux window. Agents
  cannot interfere with each other's Claude Code context.
- **File-based messaging.** Agents communicate through a shared filesystem
  (`shared/.queue/`, `.status/`, `.memory/`, `.decisions/`). Messages are individual
  markdown files moved atomically to prevent partial reads.
- **Iterative development with quality gates.** Work proceeds in iterations through
  plan, execute, test, integrate, review, and critique phases. The Critic scores every
  iteration, and it only advances when the mode's pass-rate threshold is met.
- **Seamless stop and resume.** Fleet state is captured as JSON snapshots. Stop tonight,
  resume tomorrow exactly where you left off.
- **Human override at any time.** Even in Auto Pilot mode, intervene via
  `./forge tell "message"` or by attaching to the Team Leader's interactive session.

---

## Prerequisites

**Required:**

| Tool | Purpose | Install |
|------|---------|---------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI (`claude`) | Powers every agent | `npm install -g @anthropic-ai/claude-code` |
| tmux | Process isolation for agents | `sudo apt install tmux` / `brew install tmux` |
| git | Version control, branch management | `sudo apt install git` / `brew install git` |
| yq | YAML config parsing | `sudo apt install yq` / `brew install yq` |

**Optional:** docker (Production Ready+ modes), jq (enhanced status display),
Node.js 18+ (JS/TS projects), Python 3.11+ (Python/AI-ML projects).

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/forge.git && cd forge

# 2. Validate dependencies
./forge setup

# 3. Configure your project (pick one)
./forge init                          # Interactive wizard (recommended)
# OR edit config/team-config.yaml and config/project-requirements.md directly

# 4. Start the team
./forge start

# 5. Talk to the Team Leader
#    Type directly in the interactive tmux session, or from any terminal:
./forge tell "Focus on the authentication module first"
```

When done for the day, tell the Team Leader "stop for today" or run `./forge stop`.
Resume with `./forge start` -- it auto-detects the saved snapshot and offers to
pick up where you left off.

---

## Configuration Guide

All configuration lives in `config/team-config.yaml`. See
`config/team-config.example.yaml` for a fully worked example.

### `project` -- What to build
```yaml
project:
  description: ""                              # Short inline description (simple projects)
  requirements_file: "config/project-requirements.md"  # Detailed requirements (overrides description)
  type: "new"                                  # "new" (greenfield) | "existing" (brownfield)
  existing_project_path: ""                    # Required if type is "existing"
```
### `mode` and `strategy`
```yaml
mode: "mvp"          # "mvp" | "production-ready" | "no-compromise" (see Mode Comparison)
strategy: "co-pilot"  # "auto-pilot" | "co-pilot" | "micro-manage" (see Strategy Comparison)
```

### `cost` -- Budget limits
```yaml
cost:
  max_development_cost: 50       # Max USD for Claude Code usage. "no-cap" for unlimited.
  max_project_runtime_cost: "no-cap"  # Max USD for project infra/API costs.
```
At 80% of cap, the Team Leader reduces parallelism. At 100%, non-critical agents pause.

### `agents` -- Team composition
```yaml
agents:
  team_profile: "auto"    # "auto" | "lean" | "full" | "custom"
  exclude: []             # Remove agents, e.g. ["security-tester"]
  additional: []          # Add agents, e.g. ["performance-engineer"]
  include: []             # Only for team_profile: "custom"
```
- **auto**: `lean` for MVP, `full` for Production Ready+.
- **lean**: 8 agents with merged roles. Cost-efficient.
- **full**: 12 specialized agents. Production-grade.
- **custom**: explicit agent list via `include`.

### `claude_md` -- CLAUDE.md integration
```yaml
claude_md:
  source: "both"            # "project" | "global" | "both" | "none"
  priority: "project-first" # "project-first" | "global-first"
  global_path: ""           # Default: ~/.claude/CLAUDE.md
  project_path: ""          # Default: {project_root}/CLAUDE.md
```
See [CLAUDE.md Integration](#claudemd-integration) below.

### `tech_stack` -- Technology preferences
```yaml
tech_stack:
  languages: []        # e.g. ["typescript", "python"]
  frameworks: []       # e.g. ["nextjs", "fastapi"]
  databases: []        # e.g. ["postgresql", "redis"]
  infrastructure: []   # e.g. ["aws", "docker", "kubernetes"]
```
Leave arrays empty for the team to decide based on requirements.

### `llm_gateway` -- LLM integration for AI projects
```yaml
llm_gateway:
  local_claude_model: "claude-sonnet-4-20250514"  # Model for integration tests
  enable_local_claude: true                        # Use Claude CLI for integration tests
  cost_tracking: true                              # Track LLM token usage
```
All LLM calls in built projects must use [llm-gateway](https://github.com/Rushabh1798/llm-gateway).

### `bootstrap_template` -- Starter scaffolding
Set to `"auto"` (Architect selects), a template name, comma-separated names, or `""` to skip.
Templates are reference scaffolding -- the Architect adapts them to actual requirements.

### `session` and `usage_limits`
```yaml
session:
  snapshot_retention: 5                   # Snapshots to keep (oldest deleted first)
  auto_stop_after_hours: 0               # Auto-stop after N hours (0 = disabled)
  shutdown_grace_period_seconds: 60       # Grace period before forced shutdown
usage_limits:
  proactive_save_interval_hours: 4       # Proactive state save interval
  estimated_refresh_window_hours: 1      # Estimated rate limit refresh time
  auto_resume_after_limit: true          # Auto-resume after refresh
  fleet_limit_threshold: 3              # N+ agents limited triggers fleet stop
  scheduled_resume_time: ""             # Optional fixed resume time, e.g. "06:00"
```

---

## Agent Roster and Team Profiles

Each agent runs in its own Claude Code session inside a dedicated tmux window.

### Lean Team (8 agents) -- Default for MVP

| Agent | Merges | Role |
|-------|--------|------|
| Team Leader | -- | Orchestration, task assignment, human interface |
| Research-Strategist | Researcher + Strategist | Research, strategy, iteration planning |
| Architect | -- | System design, API contracts, template selection |
| Backend Developer | -- | Server-side implementation (multiple instances supported) |
| Frontend Engineer | Designer + Developer | UI/UX design and frontend implementation |
| QA Engineer | Manual + Automation | Testing, coverage, bug tracking |
| DevOps Specialist | -- | CI/CD, Docker, infrastructure as code |
| Critic | -- | Quality gates, acceptance criteria, scoring |

Lean team advantage: ~40% fewer context windows, ~60% less inter-agent messaging.

### Full Team (12 agents) -- Default for Production Ready / No Compromise

Splits merged roles and adds specialists beyond the lean roster:

| Agent | Why Separate |
|-------|-------------|
| Researcher (standalone) | Deep research: vendor benchmarks, competitor analysis |
| Strategist (standalone) | Complex tradeoff analysis, capacity planning, roadmaps |
| Frontend Designer (standalone) | Design system: tokens, component library, accessibility |
| Frontend Developer (standalone) | Production-grade implementation, state management |
| Security Tester (new) | Independent security review, separate from code authors |
| Performance Engineer (new) | Load testing, profiling, caching, capacity planning |
| Documentation Specialist (new) | API docs, architecture diagrams, runbooks |

QA Engineer is always merged (manual + automation) in both profiles -- the context
overlap is too high to justify separation. Spawn multiple QA instances if needed.

### Auto Selection

| Mode | Profile | Notes |
|------|---------|-------|
| MVP | Lean (8) | Cost-efficient, fewer context windows |
| Production Ready | Full (12) | Specialized roles, objective security reviews |
| No Compromise | Full (12) | Performance Engineer always included |

Override with `team_profile`, `exclude`, and `additional` in config.

---

## CLAUDE.md Integration

Claude Code uses `CLAUDE.md` files for project conventions, coding standards, and
preferences. Forge incorporates these into agent instruction files during init.

### Source Options

| Source | Behavior | Best For |
|--------|----------|----------|
| `"project"` | Project's `CLAUDE.md`, falls back to global | Brownfield with established conventions |
| `"global"` | `~/.claude/CLAUDE.md`, falls back to none | Personal coding style enforcement |
| `"both"` | Merge both; project overrides global on conflict | Most users (default) |
| `"none"` | Agents use only their own instruction files | Clean, reproducible setups |

### Priority (when source is "both")

- **`"project-first"`** (default): Project rules override global. Best for brownfield.
- **`"global-first"`**: Global overrides project. Rare -- for enforcing personal standards.

### Brownfield Projects

For existing projects (`project.type: "existing"`), use `source: "project"` or `"both"`
so agents inherit your coding conventions, linting rules, and architectural patterns.
Agents analyze your codebase and adapt to existing patterns rather than imposing defaults.

---

## Mode Comparison

| Aspect | MVP | Production Ready | No Compromise |
|--------|-----|-----------------|---------------|
| **Goal** | Working prototype | Industrial-grade software | Market-ready product |
| **Critic Pass Rate** | 70% per category | 90% per category | 100% per category |
| **Default Team** | Lean (8 agents) | Full (12 agents) | Full (12 agents) |
| **Testing** | Happy-path tests | >90% coverage + integration | Exhaustive + chaos/fault injection |
| **CI/CD** | None required | GitHub Actions, pre-commit | Full pipeline + single-click deploy |
| **Infrastructure** | Local only | Docker Compose, scalable | IaC (Terraform/Pulumi), LocalStack |
| **Documentation** | Basic README | API docs, arch diagrams | Full traceability, runbooks |
| **Architecture** | Monolith OK | DDD, bounded contexts | Horizontal scaling, capacity plan |
| **LLM Integration** | llm-gateway | + local-claude testing | + cost estimation |

Switch modes mid-session: tell the Team Leader "Switch to production-ready mode".
It re-evaluates work, spawns agents if needed, and updates Critic thresholds.

---

## Strategy Comparison

| Aspect | Auto Pilot | Co-Pilot | Micro-Manage |
|--------|-----------|----------|-------------|
| **Human Involvement** | Zero (observe only) | Design approvals only | Every significant decision |
| **Decision Authority** | Fully autonomous | Architecture + tech choices | Everything modifying state |
| **Permissions** | All autonomous | File/command ops autonomous | All permissions required |
| **Best For** | Overnight runs | Default -- balanced control | Critical projects, learning |
| **Override Available** | Yes (always) | Yes (always) | Yes (always) |
| **Cost Cap** | Enforced | Enforced | Enforced |

All strategies monitor `shared/.human/override.md` -- you can always intervene.

---

## Human Override

You can intervene in any mode, including Auto Pilot, at any time.

**`./forge tell`** -- send a directive without entering tmux:
```bash
./forge tell "Switch to production-ready mode"
./forge tell "Focus on the payment service, deprioritize admin panel"
./forge tell "Pause all work"
```
The message is written to `shared/.human/override.md` and processed at the next
task boundary.

**`./forge attach`** -- enter the Team Leader's interactive tmux session:
```bash
./forge attach
# Type naturally: "What's the status?", "Stop for today", etc.
# Ctrl+B then D to detach without stopping.
```

**Direct file edit** -- write to `shared/.human/override.md` with any editor.
Useful for scripted interventions.

---

## Stopping and Resuming Sessions

### Three ways to stop

1. **Talk to the Team Leader.** Type "Stop for today" in the interactive session.
   It coordinates graceful shutdown, saves a snapshot, and confirms completion.
2. **`./forge stop`.** Same graceful shutdown from outside tmux. Agents finalize
   working memory, checkpoint-commit, release locks, and set status to `suspended`.
3. **`./forge tell "stop for today"`.** Via the override channel.

Agents receive `PREPARE_SHUTDOWN` and get a grace period (default: 60s) to finalize.

### Resuming

```bash
./forge start
# [Forge] Found previous session from 2025-07-15 18:30
# [Forge]   Iteration: 3 (phase: EXECUTE)
# [Forge]   Agents: 5 active | Cost: $12.50 / $50.00
# [Forge]   Resume? [Y/n/fresh]
```

- **Y** (default): resume from where you left off.
- **n**: exit without starting.
- **fresh**: archive snapshot and start new session.
- Specific snapshot: `./forge start --snapshot path/to/snapshot.json`

### What snapshots contain

Snapshots capture iteration number and phase, agent roster with status and working
memory references, cost tracking totals, decision log state, dependency graph, and
configuration. Stored in `shared/.snapshots/` with retention controlled by
`session.snapshot_retention` (default: 5).

---

## Customization

**Adding a custom agent:** Create a markdown file in `agents/` following the
12-section structure from `agents/_base-agent.md` (Identity, Responsibilities,
Skills, Inputs, Outputs, Communication, Collaboration, Quality, Iteration, Mode
Behavior, Memory, Artifacts). Add the name to `agents.additional` or use
`team_profile: "custom"` with an explicit `include` list.

**Modifying existing agents:** Edit the markdown file in `agents/` directly. Changes
take effect on next spawn. For mid-session changes, stop and restart the agent.

**Runtime changes:** Tell the Team Leader "Spin up another backend developer" or
"Kill the frontend designer." It manages lifecycle via `scripts/spawn-agent.sh`
and `scripts/kill-agent.sh`.

**Switching profiles:** Tell the Team Leader "Switch to full team" or change
`agents.team_profile` in config and restart.

---

## Templates

Forge includes 34 project templates across 8 categories. Templates provide reference
scaffolding -- the Architect adapts them to actual requirements.

### Template Catalog

| Category | Template | Description |
|----------|----------|-------------|
| **Backend** | python-fastapi | Python + FastAPI, SQLAlchemy, Alembic, Pydantic v2 |
| | node-express-api | Node.js + Express, TypeScript, Prisma, JWT auth |
| | go-microservice | Go + Gin, GORM, Docker multi-stage build |
| | graphql-api | GraphQL with Apollo Server or Strawberry |
| | grpc-service | gRPC + Protobuf, streaming, health checks |
| **Frontend** | react-spa | React + TypeScript, Vite, Tailwind, React Router |
| | vue-spa | Vue 3 + TypeScript, Vite, Pinia, Tailwind |
| | react-native-mobile | React Native + Expo, React Navigation |
| | flutter-mobile | Flutter + Riverpod, GoRouter, Dio |
| **Full Stack** | nextjs-fullstack | Next.js App Router, Prisma, NextAuth |
| | nuxt-fullstack | Nuxt 3, Nitro, Drizzle ORM |
| | t3-stack | Next.js + tRPC + Prisma + Tailwind |
| | django-fullstack | Django + DRF/HTMX, Celery |
| **AI/ML** | langchain-agent | LangChain/LangGraph agentic AI + llm-gateway |
| | rag-pipeline | RAG: ingestion, vector DB, retrieval + llm-gateway |
| | temporal-ai-workflow | Temporal AI pipelines + llm-gateway |
| | ml-model-serving | FastAPI + model inference, A/B testing |
| | crewai-multi-agent | CrewAI multi-agent + llm-gateway |
| **Event-Driven** | kafka-microservice | Kafka consumer/producer, schema registry |
| | rabbitmq-worker | RabbitMQ task worker, retries, priority queues |
| | temporal-workflow | Temporal durable workflows, saga pattern |
| **Platform** | saas-multi-tenant | SaaS: auth, Stripe billing, tenant isolation |
| | chrome-extension | Chrome Manifest V3, popup, content script |
| | vscode-extension | VS Code commands, webview panels, LSP |
| | cli-tool | CLI subcommands, config files, completions |
| | slack-bot | Slack Bolt: slash commands, event handlers |
| | discord-bot | Discord.js/py: slash commands, embeds |
| **Data** | etl-pipeline | Airflow/Dagster + dbt transformations |
| | streaming-pipeline | Flink/Spark Streaming + Kafka |
| | data-api | dbt models + FastAPI data serving |
| **Infrastructure** | terraform-aws | Terraform IaC: VPC, ECS/EKS, RDS, S3, IAM |
| | pulumi-multi-cloud | Pulumi IaC, TypeScript/Python, multi-cloud |
| | k8s-helm-charts | Kubernetes Helm charts, autoscaling |
| | monorepo-turborepo | Turborepo/Nx monorepo, shared packages |

### How templates work

- **Reference, not mandate.** The Architect adapts scaffolds to fit requirements.
- **Multi-template composition.** Combine templates for complex projects (e.g.,
  `react-spa` + `python-fastapi` + `terraform-aws`). Set `bootstrap_template: "auto"`.
- **Priority templates** (python-fastapi, node-express-api, react-spa,
  nextjs-fullstack, langchain-agent, rag-pipeline) include full working scaffolds.
  Others include pattern docs and minimal placeholders.

### Custom templates

Create a directory in `templates/{category}/` with `README.md`, `PATTERNS.md`,
`template-config.yaml`, and `scaffold/`. Register in `templates/_template-manifest.yaml`.

### AI/ML template notes

All AI/ML templates with LLM calls require
[llm-gateway](https://github.com/Rushabh1798/llm-gateway). Direct vendor SDK calls
(LangChain providers, CrewAI configs) are not permitted. Configure via `llm_gateway`
in `team-config.yaml`.

---

## Troubleshooting

**Agent not responding:** The watchdog (`scripts/watchdog.sh`) monitors health. If a
status file is stale (>5 minutes) or the tmux window has died, the Team Leader
respawns the agent with `--resume`, restoring from working memory. Check manually
with `./forge status`.

**Session will not start:** Run `./forge setup` to re-validate. Common issues:
`claude` CLI not on PATH, `tmux` or `yq` not installed, scripts not executable
(`chmod +x forge scripts/*.sh`).

**Usage limits hit:** Agents auto-execute the `LIMIT_SAVE` protocol: save work, update
memory, set status to `rate-limited`. The watchdog auto-resumes after the estimated
refresh window. If 3+ agents hit limits simultaneously, a full fleet stop preserves
state coherently.

**Secrets in logs or commits:** Agents reference secrets by environment variable name
only. Values are stored in `shared/.secrets/vault.env` (git-ignored). Check
`shared/.logs/` and git history if you suspect a leak.

**tmux issues:** No session found -- run `./forge start` first. Cannot detach --
press `Ctrl+B` then `D`. Sessions are prefixed `forge-` (`tmux list-sessions`).

---

## Cost Management

Forge tracks estimated token usage across all agents via `./forge cost`.

**Setting budgets:** Set `cost.max_development_cost` in `team-config.yaml`. At 80%,
parallelism is reduced. At 100%, non-critical agents pause. Use `"no-cap"` for
unlimited -- costs are always tracked for visibility.

**Lean vs full team:** The lean team (8 agents) uses ~40% fewer context windows and
~60% less messaging than the full team (12 agents). Choose lean for MVP cost
efficiency; full when you need security reviews, performance engineering, and
comprehensive docs.

**Monitoring:**
```bash
./forge cost                             # Breakdown by agent
./forge status                           # Includes cost summary
./forge tell "How much has this cost?"   # Ask Team Leader
```

---

## Advanced Orchestration

**Parallel work streams.** The Team Leader runs independent tasks concurrently --
e.g., backend APIs and frontend scaffolding in parallel once the Architect defines
API contracts. Multiple agent instances can be spawned (`backend-developer-1`,
`backend-developer-2`) for separate services.

**Integration testing.** When components are ready to merge, the Team Leader
coordinates integration. The QA Engineer tests the merged codebase; failures are
routed back to responsible agents with specific details.

**Code review.** All changes pass through the Architect (architectural compliance) and
Critic (quality). In Production Ready+, Security Tester reviews for vulnerabilities.
Feedback becomes corrective tasks for the authoring agent.

**Git workflow.** Agents work on `agent/{agent-name}/{task-id}` branches. Only the
Team Leader merges to main. File locks (`shared/.locks/`) prevent simultaneous edits.
Verified iterations are tagged: `git tag iteration-{N}-verified`.

---

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines on adding agents,
templates, and scripts, as well as bash conventions, testing, and PR process.

---

## License

MIT -- see [LICENSE](LICENSE) for details.
