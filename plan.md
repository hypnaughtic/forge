# Project: Forge — AI Software Forge

## Goal

Build a GitHub open-source repository called `forge` that provides **Forge** — a CLI tool and framework for orchestrating a team of specialized AI agents using **Claude Code**, **tmux**, and **bash scripting**. The user installs Forge, runs `./forge start`, and gets an autonomous multi-agent software development team that builds their project. The repository contains agent definition files (markdown), the `forge` CLI, orchestration scripts, configuration templates, and documentation — everything needed to clone the repo, configure a project, and launch a fully coordinated AI development team.

### The `forge` CLI

Forge is primarily a CLI tool. The `forge` executable at the repo root is the single entry point for all operations:

```bash
# Core workflow
./forge setup                        # One-time setup: validate deps, install prerequisites
./forge start                        # Start a new session (or resume if snapshot exists)
./forge stop                         # Graceful shutdown with state snapshot

# Monitoring
./forge status                       # Show all agent statuses, iteration progress, costs
./forge logs                         # Tail combined agent logs
./forge cost                         # Show cost breakdown by agent

# Communication
./forge tell "switch to production-ready"     # Send natural language command to Team Leader
./forge tell "pause all work"                 # Without needing to attach to tmux
./forge attach                                # Attach to Team Leader's interactive tmux session

# Project init
./forge init                         # Interactive project setup (generates config + requirements)
```

The `forge` CLI delegates to scripts in `scripts/` but provides the unified, memorable interface. Every user interaction starts with `forge`.

---

## Execution Guidance for Claude Code

This document is the COMPLETE specification. Build the entire repository in one session by following the Implementation Order (Section 11). Here are the key rules:

1. **Create every file listed in the File Manifest below.** No file should be skipped.
2. **Agent MD files are the most critical outputs.** Each must be a fully self-contained instruction manual that a Claude Code instance can follow without any other context beyond the base protocol. Don't be terse — these files should be 150-300 lines each.
3. **Scripts must be functional bash.** Use `set -euo pipefail`, include `--help` flags, handle errors with meaningful messages.
4. **Templates have TWO tiers**: Priority templates get full scaffolds with working code. Stub templates get README + PATTERNS.md + template-config.yaml only, with scaffold/ containing a minimal placeholder.
5. **Cross-references must be correct.** When an agent file says "see Section X", verify the section number. When a script references a path, verify the path exists in the directory structure.
6. **The `_base-agent.md` file is the shared protocol** that gets loaded into EVERY agent. It must contain all shared protocols consolidated from this spec — don't leave anything scattered.
7. **Use the exact formats specified.** Message format, status file JSON, working memory markdown, log format, etc. — use the exact structures defined in this document.

### File Manifest & Size Guide

Every file to create, organized by priority. **Size** = expected lines of content.

#### Tier 1 — Core Framework (build first)
| File | Size | Description |
|------|------|-------------|
| `README.md` | 400-500 | Comprehensive guide per Section 10 requirements |
| `LICENSE` | 20 | MIT License |
| `forge` | 150-200 | Unified CLI entry point (bash) |
| `setup.sh` | 80-120 | One-time setup with dependency validation |
| `.gitignore` | 30 | Ignore shared/, generated files, .env, etc. |
| `config/team-config.yaml` | 60 | Template config (the YAML from Section 5) |
| `config/team-config.example.yaml` | 70 | Fully filled-in example config |
| `config/project-requirements.md` | 30 | Template with instructions |

#### Tier 2 — Agent Definition Files (build second, most critical)
| File | Size | Description |
|------|------|-------------|
| `agents/_base-agent.md` | 200-250 | Shared protocol: ALL cross-cutting concerns consolidated |
| `agents/team-leader.md` | 350-450 | Most critical file. Full orchestration, NL commands, session management |
| `agents/research-strategist.md` | 150-200 | Lean team: merged researcher + strategist |
| `agents/researcher.md` | 120-150 | Full team: standalone researcher |
| `agents/strategist.md` | 120-150 | Full team: standalone strategist |
| `agents/architect.md` | 180-220 | Systems architect + designer |
| `agents/backend-developer.md` | 150-200 | Backend implementation agent |
| `agents/frontend-engineer.md` | 150-200 | Lean team: merged designer + developer |
| `agents/frontend-designer.md` | 120-150 | Full team: standalone designer |
| `agents/frontend-developer.md` | 120-150 | Full team: standalone developer |
| `agents/qa-engineer.md` | 180-220 | Always merged manual + automation testing |
| `agents/devops-specialist.md` | 150-180 | CI/CD, Docker, IaC |
| `agents/security-tester.md` | 130-160 | Security analysis agent |
| `agents/performance-engineer.md` | 130-160 | Load testing, profiling, optimization |
| `agents/documentation-specialist.md` | 120-150 | Docs agent |
| `agents/critic.md` | 150-200 | Acceptance criteria, scoring, enforcement |

#### Tier 3 — Scripts (build third)
| File | Size | Description |
|------|------|-------------|
| `scripts/start.sh` | 80-120 | Fresh session startup |
| `scripts/stop.sh` | 100-140 | Graceful shutdown + snapshot |
| `scripts/resume.sh` | 80-120 | Restore from snapshot |
| `scripts/spawn-agent.sh` | 120-160 | Core agent spawning logic |
| `scripts/kill-agent.sh` | 40-60 | Graceful agent termination |
| `scripts/broadcast.sh` | 30-50 | Send message to all agents |
| `scripts/status.sh` | 60-80 | Fleet status display |
| `scripts/init-project.sh` | 150-200 | Config parsing, CLAUDE.md merge, agent file generation |
| `scripts/cost-tracker.sh` | 60-80 | Cost estimation and reporting |
| `scripts/watchdog.sh` | 100-140 | Health monitoring daemon |
| `scripts/log-aggregator.sh` | 40-60 | Log collection and rotation |

#### Tier 4 — Documentation (build fourth)
| File | Size | Description |
|------|------|-------------|
| `docs/AGENT-PROTOCOL.md` | 150-200 | Full inter-agent communication spec (Section 8 content) |
| `docs/ARCHITECTURE.md` | 100-150 | How Forge itself works |
| `docs/CONTRIBUTING.md` | 80-100 | Contribution guide |
| `docs/EXAMPLES.md` | 150-200 | Example use cases and walkthroughs |

#### Tier 5 — Templates (build last)
**Priority templates** (full scaffold with working code — sizes are total lines across all files in the template directory):
| Template | Size | Why Priority |
|----------|------|-------------|
| `templates/backend/python-fastapi/` | 200-300 total | Most common Python backend |
| `templates/backend/node-express-api/` | 200-300 total | Most common Node backend |
| `templates/frontend/react-spa/` | 150-250 total | Most common frontend |
| `templates/fullstack/nextjs-fullstack/` | 200-300 total | Most popular fullstack |
| `templates/ai-ml/langchain-agent/` | 250-350 total | Key differentiator, llm-gateway demo |
| `templates/ai-ml/rag-pipeline/` | 200-300 total | Very common AI use case |

Each priority template directory contains: `README.md` (30-50 lines), `PATTERNS.md` (40-80 lines), `template-config.yaml` (15-25 lines), and `scaffold/` with working starter files (the rest).

**Stub templates** (README + PATTERNS.md + template-config.yaml, minimal scaffold placeholder):
All remaining 28 templates. Each stub has ~50-80 lines total. The README explains what a full scaffold would contain. PATTERNS.md describes the patterns without implementing them. scaffold/ has a minimal placeholder file.

| File | Description |
|------|-------------|
| `templates/_template-manifest.yaml` | Full manifest for all 34 templates |

---

## High-Level Architecture

```
forge/
├── README.md                          # Comprehensive setup & usage guide
├── LICENSE                            # MIT License
├── forge                                # Unified CLI entry point (./forge start | stop | status | tell | init)
├── setup.sh                           # One-time setup script (installs deps, validates env)
├── config/
│   ├── team-config.yaml               # User-editable project configuration (template)
│   ├── team-config.example.yaml       # Example filled-in config for reference
│   └── project-requirements.md        # Separate file for detailed project description (referenced by yaml)
├── agents/
│   ├── _base-agent.md                 # Shared agent protocol (communication, file conventions, status reporting, memory management)
│   ├── team-leader.md                 # Team Leader / Orchestrator agent
│   ├── research-strategist.md         # Research & Strategy Lead (lean team: merged researcher + strategist)
│   ├── researcher.md                  # Researcher (full team: standalone)
│   ├── strategist.md                  # Strategist (full team: standalone)
│   ├── architect.md                   # Systems Architect & Designer agent
│   ├── backend-developer.md           # Backend Developer agent (supports multiple instances)
│   ├── frontend-engineer.md           # Frontend Engineer (lean team: merged designer + developer)
│   ├── frontend-designer.md           # Frontend UI/UX Designer (full team: standalone)
│   ├── frontend-developer.md          # Frontend Developer (full team: standalone)
│   ├── qa-engineer.md                 # QA Engineer (always merged: manual testing + automation)
│   ├── devops-specialist.md           # DevOps / Infrastructure agent
│   ├── security-tester.md             # Security Tester / Pen Tester agent (full team only by default)
│   ├── performance-engineer.md        # Performance Engineer (full team only by default)
│   ├── documentation-specialist.md    # Documentation Specialist agent (full team only by default)
│   └── critic.md                      # Critic / Devil's Advocate agent
├── templates/                         # Project reference templates (scaffolding + patterns, not source of truth)
│   ├── _template-manifest.yaml        # Registry of all templates with metadata, tags, and categories
│   ├── backend/
│   │   ├── node-express-api/          # Node.js + Express REST API (TypeScript, Prisma)
│   │   ├── python-fastapi/            # Python + FastAPI (SQLAlchemy, Alembic)
│   │   ├── go-microservice/           # Go microservice (Gin, GORM)
│   │   ├── graphql-api/               # GraphQL API (Apollo Server or Strawberry)
│   │   └── grpc-service/              # gRPC service with Protobuf definitions
│   ├── frontend/
│   │   ├── react-spa/                 # React SPA (Vite, React Router, Tailwind)
│   │   ├── vue-spa/                   # Vue 3 SPA (Vite, Vue Router, Pinia)
│   │   ├── react-native-mobile/       # React Native mobile app
│   │   └── flutter-mobile/            # Flutter cross-platform mobile app
│   ├── fullstack/
│   │   ├── nextjs-fullstack/          # Next.js App Router (Prisma, NextAuth)
│   │   ├── nuxt-fullstack/            # Nuxt 3 full-stack (Nitro, Drizzle)
│   │   ├── t3-stack/                  # T3 Stack (Next.js, tRPC, Prisma, Tailwind)
│   │   └── django-fullstack/          # Django + HTMX/React frontend
│   ├── ai-ml/
│   │   ├── langchain-agent/           # Agentic AI with LangChain/LangGraph + llm-gateway
│   │   ├── temporal-ai-workflow/      # Temporal-orchestrated AI pipelines + llm-gateway
│   │   ├── rag-pipeline/              # RAG system (vector DB, embedding, retrieval, llm-gateway)
│   │   ├── ml-model-serving/          # ML model serving (FastAPI + model inference)
│   │   └── crewai-multi-agent/        # Multi-agent system with CrewAI + llm-gateway
│   ├── event-driven/
│   │   ├── kafka-microservice/        # Kafka consumer/producer microservice
│   │   ├── rabbitmq-worker/           # RabbitMQ task worker
│   │   └── temporal-workflow/         # Temporal durable workflow service
│   ├── platform/
│   │   ├── saas-multi-tenant/         # SaaS multi-tenant platform (auth, billing, tenants)
│   │   ├── chrome-extension/          # Chrome extension (Manifest V3)
│   │   ├── vscode-extension/          # VS Code extension
│   │   ├── cli-tool/                  # CLI tool (Commander.js or Click)
│   │   ├── slack-bot/                 # Slack bot (Bolt framework)
│   │   └── discord-bot/              # Discord bot (Discord.js)
│   ├── data/
│   │   ├── etl-pipeline/             # ETL/ELT data pipeline (Airflow or Dagster)
│   │   ├── streaming-pipeline/        # Real-time streaming (Flink or Spark Streaming)
│   │   └── data-api/                 # Data warehouse API (dbt + API layer)
│   └── infrastructure/
│       ├── terraform-aws/             # Terraform IaC for AWS
│       ├── pulumi-multi-cloud/        # Pulumi IaC (multi-cloud)
│       ├── k8s-helm-charts/           # Kubernetes Helm charts
│       └── monorepo-turborepo/        # Monorepo setup (Turborepo/Nx with shared packages)
├── scripts/
│   ├── start.sh                       # Starts a fresh session (called by forge)
│   ├── stop.sh                        # Graceful fleet shutdown with state snapshot (called by forge or Team Leader)
│   ├── resume.sh                      # Resume from snapshot (called by forge)
│   ├── spawn-agent.sh                 # Spawns a named agent in a new tmux pane/window
│   ├── kill-agent.sh                  # Gracefully stops an agent's tmux session
│   ├── broadcast.sh                   # Sends a message to all active agents via shared file
│   ├── status.sh                      # Prints status of all running agents (with stale detection)
│   ├── init-project.sh                # Reads config, generates project-specific agent files, bootstraps project directory
│   ├── cost-tracker.sh                # Tracks and reports estimated token usage and costs
│   ├── watchdog.sh                    # Agent health monitoring and auto-recovery daemon
│   └── log-aggregator.sh             # Collects and formats logs from all agents
├── shared/                            # Inter-agent communication directory (created at runtime)
│   ├── .queue/                        # Message queue — individual message files per agent inbox
│   │   └── {agent-name}-inbox/        # Directory per agent, one file per message
│   ├── .status/                       # Agent status files (idle, working, blocked, review, done, suspended, rate-limited, error, terminated)
│   ├── .memory/                       # Agent working memory files for context persistence
│   ├── .decisions/                    # Logged architectural and design decisions
│   ├── .iterations/                   # Iteration summaries and verification reports
│   ├── .artifacts/                    # Artifact registry tracking cross-agent dependencies
│   ├── .locks/                        # File reservation locks for shared code files
│   ├── .logs/                         # Structured agent logs for debugging and cost tracking
│   ├── .snapshots/                    # Fleet state snapshots for stop/resume across sessions
│   ├── .secrets/                      # Secret vault (encrypted, never committed, never logged)
│   └── .human/                        # Human override channel (monitored in all modes)
└── docs/
    ├── CONTRIBUTING.md                # How to contribute new agents or improve existing ones
    ├── AGENT-PROTOCOL.md              # Detailed inter-agent communication protocol spec
    ├── ARCHITECTURE.md                # How Forge itself works (not the user's project)
    └── EXAMPLES.md                    # Example use cases and walkthroughs
```

---

## Detailed Requirements

### 1. Agent Definition Files (`agents/*.md`)

Each agent markdown file must contain the following sections. These files serve as the **system prompt / instruction manual** that gets loaded into each Claude Code instance.

#### Required Sections Per Agent File

1. **Identity & Role**: Agent name, domain expertise, one-paragraph mission statement.
2. **Core Responsibilities**: Numbered list of specific duties this agent owns.
3. **Skills & Tools**: What tools, languages, frameworks, and commands this agent is expected to use.
4. **Input Expectations**: What information/artifacts this agent needs before starting work (from Team Leader or other agents).
5. **Output Deliverables**: Exact artifacts this agent produces (files, reports, code, configs) with naming conventions.
6. **Communication Protocol**:
   - How to read messages from the shared queue (`shared/.queue/{agent-name}-inbox/` directory — one file per message).
   - How to write messages to other agents: write to a temp file first, then `mv` atomically to `shared/.queue/{target-agent}-inbox/msg-{timestamp}-{sender}.md`.
   - How to update own status (`shared/.status/{agent-name}.json`): states = `idle`, `working`, `blocked`, `review`, `done`, `suspended` (shutdown), `rate-limited` (usage limit hit), `error`, `terminated`.
   - How to escalate blockers to Team Leader.
   - How to request work from another agent.
   - How to acknowledge messages (delete the message file from inbox after processing).
7. **Collaboration Guidelines**: Which agents this one typically interacts with, handoff protocols, review expectations.
8. **Quality Standards**: Domain-specific quality criteria this agent must meet before marking work as done.
9. **Iteration Protocol**: How this agent participates in iteration cycles — what it reviews, what it re-does, how it incorporates feedback.
10. **Mode-Specific Behavior**: How the agent's behavior changes across MVP, Production Ready, and No Compromise modes (see Section 3).
11. **Memory & Context Management**: How this agent maintains its working memory file, what to persist, and how to recover from a session restart (see Section 13).
12. **Artifact Registration**: How this agent registers produced artifacts and declares dependencies on other agents' artifacts (see Section 15).

#### Agent File Skeleton

Every agent MD file must follow this exact structure. Claude Code should use this skeleton as the starting template for every agent file:

```markdown
# {Agent Name}

> {One-line mission statement}

## 1. Identity & Role

- **Name**: {agent-name} (e.g., backend-developer, qa-engineer)
- **Domain**: {domain expertise}
- **Mission**: {paragraph explaining this agent's purpose and value}

## 2. Core Responsibilities

1. {responsibility 1}
2. {responsibility 2}
...

## 3. Skills & Tools

- **Languages**: {languages this agent works with}
- **Frameworks**: {frameworks}
- **Tools**: {CLI tools, testing tools, etc.}
- **Commands**: {specific shell commands this agent commonly uses}

## 4. Input Expectations

Before starting work, this agent needs:
- From Team Leader: {what}
- From Architect: {what}
- From {other agent}: {what}

## 5. Output Deliverables

This agent produces:
| Artifact | Location | Format | Consumers |
|----------|----------|--------|-----------|
| {artifact} | {path} | {format} | {who uses it} |

## 6. Communication Protocol

{Reference _base-agent.md for shared protocol, then add agent-specific details}

### Messages I Send
- To Team Leader: status updates, deliverables, blockers, confidence signals
- To {agent}: {what and when}

### Messages I Receive
- From Team Leader: task assignments, corrective instructions, PREPARE_SHUTDOWN, COMPACT_MEMORY
- From {agent}: {what and when}

## 7. Collaboration Guidelines

| Agent | Interaction Pattern |
|-------|-------------------|
| {agent} | {how I work with them} |

## 8. Quality Standards

Before marking work as done:
- [ ] {technical quality criterion 1}
- [ ] {technical quality criterion 2}
- [ ] **User-facing quality**: {how this agent ensures its output delivers genuine value to end users — not just technical correctness}
...

## 9. Iteration Protocol

- **PLAN phase**: {what I do}
- **EXECUTE phase**: {what I do}
- **TEST phase**: {what I do}
- **INTEGRATE phase**: {what I do}
- **REVIEW phase**: {what I do}
- **CRITIQUE phase**: {what I do — how I respond to Critic feedback, including user-quality findings}

## 10. Mode-Specific Behavior

### MVP Mode
{how behavior changes}

### Production Ready Mode
{how behavior changes}

### No Compromise Mode
{how behavior changes}

## 11. Memory & Context Management

### What I Persist in Working Memory
- {key items this agent must track}

### Recovery Protocol
When restarting from working memory:
1. {step 1}
2. {step 2}

## 12. Artifact Registration

### Artifacts I Produce
| Artifact ID | Type | Path Pattern |
|-------------|------|-------------|
| {id} | {code/config/doc/test} | {path} |

### Artifacts I Depend On
| Artifact ID | Producer | Why I Need It |
|-------------|----------|---------------|
| {id} | {agent} | {reason} |
```

**Critical**: Each agent file must be a COMPLETE, self-contained instruction manual. An agent reading ONLY its own file + `_base-agent.md` must have everything needed to do its job. Don't be terse — be thorough. Fill every section with meaningful, role-specific content.

#### Base Agent Protocol (`agents/_base-agent.md`)

This file defines the **shared contract** all agents follow. Every agent file must reference it. It includes:

- **File-based message queue protocol**: Each agent has an inbox directory (`shared/.queue/{agent-name}-inbox/`). Messages are individual files. Writers create a temp file in `/tmp/` then `mv` it atomically to the inbox directory to prevent partial reads. Readers process messages in timestamp order and delete after acknowledgment.
- **Status reporting format**: JSON at `shared/.status/{agent-name}.json` with fields: `agent`, `status` (one of: `idle`, `working`, `blocked`, `review`, `done`, `suspended`, `rate-limited`, `error`, `terminated`), `current_task`, `blockers`, `last_updated`, `iteration`, `artifacts_produced`, `estimated_completion`, `session_start`, `messages_processed`, `usage_limits` (object with `warnings_detected`, `last_warning_at`, `status`), `cost_estimate_usd`.
- **Working memory mandate**: Every agent must maintain `shared/.memory/{agent-name}-memory.md` (see Section 13).
- **Structured logging**: Every agent must append structured log entries to `shared/.logs/{agent-name}.log` (see Section 17).
- **Shared decision log format**: Append-only file at `shared/.decisions/decision-log.md`.
- **Git workflow** (see Section 14 for full specification): all agents work on feature branches with naming convention `agent/{agent-name}/{task-id}`, only Team Leader merges to main.
- **File locking conventions**: Before editing any shared code file, check and acquire a lock at `shared/.locks/{filepath-hash}.lock`. Release after commit. If locked by another agent, notify Team Leader and wait (see Section 16).
- **Artifact registration**: Register all produced artifacts in `shared/.artifacts/registry.json` (see Section 15).
- **Error handling**: If an agent encounters an unrecoverable error, write to `shared/.queue/team-leader-inbox/` with `PRIORITY: CRITICAL`.
- **Human override monitoring**: All agents must check `shared/.human/override.md` at the start of every task and after every major operation (see Section 18).
- **Graceful shutdown handling**: On receiving `PREPARE_SHUTDOWN` message, every agent must: stop new subtasks, update working memory with full resume context, checkpoint-commit in-progress work, release all file locks, update status to `suspended`, and acknowledge to Team Leader (see Section 22).
- **Usage limit self-monitoring**: Every agent must monitor for signs of approaching Claude Code usage limits (see Section 20). When a limit warning is detected, the agent immediately executes the `LIMIT_SAVE` protocol: save all work-in-progress, update working memory with exact resume state, checkpoint-commit, update status to `rate-limited`, and notify Team Leader — all BEFORE the limit is actually hit and the session is killed.
- **Vendor-agnostic coding mandate**: All external dependencies must be behind abstract interfaces.
- **LLM Gateway mandate**: Any LLM calls in the project being built must use `llm-gateway` (https://github.com/Rushabh1798/llm-gateway).
- **CLAUDE.md compliance**: If the project's `init-project.sh` has merged external CLAUDE.md guidelines into agent instruction files, agents must respect those guidelines. Project-level CLAUDE.md rules (coding conventions, style preferences, architectural patterns) take precedence over the agent's default behavior when they conflict. See Section 23 for the full CLAUDE.md hierarchy.
- **Secret safety**: Agents must NEVER log, commit, message, or store in working memory any secret values. Reference secrets by environment variable name only. See Section 24.
- **Confidence signaling**: Every deliverable and status-update message to the Team Leader must include a `confidence: high | medium | low` field. Low confidence triggers mandatory review. See Section 29.
- **Memory compaction**: Agents must participate in memory compaction cycles triggered by the Team Leader after each verified iteration. Compact old content to summaries, preserve detail in on-disk reference files. See Section 31.

---

### 2. Team Leader Agent (`agents/team-leader.md`)

The Team Leader is the orchestrator. Its instruction file must be the most comprehensive and cover:

#### Startup Sequence
1. Read `config/team-config.yaml` to understand project requirements, mode, and execution strategy.
2. Analyze the project scope and determine which agents are needed.
3. Initialize its own working memory at `shared/.memory/team-leader-memory.md` with the full project context, agent roster, and iteration plan.
4. Generate project-specific versions of agent MD files (tailored instructions referencing the actual project context) and place them in `{project_root}/.forge/agents/`.
5. Select and apply a project bootstrap template from `templates/` if the tech stack matches (skip for existing projects). Customize the template to match the Architect's initial design.
6. Use `scripts/spawn-agent.sh` to launch each required agent in its own tmux window.
7. Spawn multiple instances of the same agent type if parallel work is needed (e.g., `backend-developer-1`, `backend-developer-2` for independent microservices).
8. Send initial task assignments to each agent via the message queue.
9. Start the watchdog monitoring cycle (or verify `scripts/watchdog.sh` is running).
10. Generate initial acceptance criteria and send to Critic agent for validation.

#### Ongoing Orchestration
- **Task Decomposition**: Break the project goal into epics → tasks → subtasks. Assign to appropriate agents.
- **Dependency Management**: Track inter-agent dependencies using the artifact registry (`shared/.artifacts/registry.json`). Don't assign frontend integration tasks until backend APIs are defined. When an artifact changes, notify all downstream agents automatically.
- **Parallel Execution**: Identify independent workstreams and run them in parallel across agents.
- **Iteration Cycles** (see Section 19 for the formal lifecycle):
  1. Collect status from all agents.
  2. Run QA Engineer and Critic agents to verify work.
  3. Tag git: `git tag iteration-{N}-verified` after each successful iteration.
  4. Write iteration summary to `shared/.iterations/iteration-{N}.md`.
  5. Decide: move to next iteration, re-assign failed tasks, roll back to last verified tag, or escalate to human (in Co-Pilot/Micro-Manage mode).
- **Conflict Resolution**: When agents disagree (e.g., Architect vs. Developer on approach), Team Leader makes the call based on project mode.
- **Goal Verification**: After every iteration, verify progress against the original project requirements. Reference the Critic agent's scored assessment — iterations cannot proceed unless the Critic's pass rate meets the mode threshold (MVP: 70%, Production Ready: 90%, No Compromise: 100%) across ALL three categories: Functional, Technical, AND User-Quality. A feature that passes technically but delivers poor user-facing quality (generic outputs, stale data, non-actionable results) is NOT done.
- **Work Combination**: Merge work from different agents — coordinate git merges, verify integration, resolve conflicts. Use the file locking system to prevent simultaneous edits.
- **Agent Lifecycle**: Spin down agents that are no longer needed. Spin up new ones if scope changes.
- **Agent Health Monitoring**: Consume health reports from `scripts/watchdog.sh`. If an agent is unresponsive (status file not updated for >5 minutes) or its tmux window has died, restart it with its working memory file to resume context (see Section 20).
- **Rollback Protocol**: If an iteration makes things worse (tests that previously passed now fail, Critic rejects), roll back to the last `iteration-{N}-verified` git tag and reassign tasks with corrective instructions.
- **Cost Monitoring**: Track estimated token usage across all agent sessions. Enforce budget caps from config. Use `scripts/cost-tracker.sh`. Monitor `shared/.logs/` for cost data.
- **Mode Switching**: If the human requests a mode change (MVP → Production Ready, etc.), the Team Leader must:
  1. Re-evaluate all current work against new mode's standards.
  2. Spawn additional agents if needed (e.g., Security Tester for Production Ready).
  3. Update all active agents' instructions with new quality thresholds via `scripts/broadcast.sh`.
  4. Update the Critic's acceptance criteria thresholds.
  5. Log the mode switch in the decision log.

#### Execution Strategy Handling
- **Auto Pilot**: Make all decisions autonomously. Log decisions but don't wait for approval. Respect cost caps. Optimize agent model usage for cost when caps are set. Still monitor `shared/.human/override.md` for emergency human intervention.
- **Co-Pilot**: Present design decisions and architectural choices to human for approval (via `shared/.decisions/pending-approval.md`). Skip permission requests for file operations, searches, and commands. All agents must follow this — only project-level decisions need approval.
- **Micro-Manage**: Present every significant decision to human. Only execute when confidence is very high. Ask detailed questions with tradeoff explanations. More thorough than Co-Pilot.

#### Human Communication — Interactive Team Leader Session

The Team Leader runs in an **interactive Claude Code session** in the primary tmux window. The human can type directly to the Team Leader at any time — this is the main human ↔ team interface. The human does NOT need to use scripts or override files for routine commands; they just talk to the Team Leader like they would talk to a project manager.

##### Natural Language Commands the Team Leader Must Understand

The Team Leader's instruction file must include explicit handling for these natural language patterns from the human:

**Session Control:**
- "Stop for today" / "Let's pause" / "Shut down the team" / "We'll continue tomorrow" → Team Leader executes `scripts/stop.sh` internally. This triggers graceful shutdown, snapshot capture, and fleet teardown. The Team Leader is the last to shut down after confirming all other agents are stopped.
- "Take a break for an hour" / "Pause everything" → Team Leader broadcasts `PAUSE` to all agents. Agents stop picking up new tasks but don't shut down. Team Leader resumes on human's next message.
- "What's the status?" / "How are we doing?" / "Give me a summary" → Team Leader runs `scripts/status.sh` and presents a human-friendly summary of all agents, current iteration, blockers, and costs.
- "How much has this cost?" / "Show me the costs" → Team Leader runs `scripts/cost-tracker.sh` and presents the report.
- "Are any agents rate limited?" / "What's the limit situation?" → Team Leader checks `shared/.status/` for agents with `usage_limits.status: "rate-limited"` and reports which agents are waiting, estimated refresh time, and whether any work is blocked.

**Mode & Strategy Changes:**
- "Switch to production-ready mode" / "Let's go no compromise" → Team Leader handles mode switching (re-evaluates work, spawns new agents if needed, updates Critic thresholds).
- "Switch to auto-pilot" / "Go micro-manage from now" → Team Leader updates execution strategy for all agents.

**Agent Management:**
- "Spin up another backend developer" / "We need a security tester" → Team Leader spawns the requested agent.
- "Kill the frontend designer, we don't need it" → Team Leader gracefully stops that agent.
- "What is the backend developer working on?" → Team Leader reads that agent's status and reports.

**Work Direction:**
- "Focus on the auth module first" / "Deprioritize the admin panel" → Team Leader reorders task priorities and reassigns agents.
- "The login flow is wrong, use OAuth2 with PKCE instead" → Team Leader creates corrective tasks, notifies affected agents, and logs the design change.
- "I've made some changes to the code directly, sync up" → Team Leader runs a git diff, identifies external changes, and notifies affected agents to re-read the codebase.

**Feedback & Review:**
- "Show me what's been built so far" / "I want to review" → Team Leader presents the current state: which features are done, running instructions, and asks what the human wants to test.
- "The search results are bad, the LLM responses need to be better" → Team Leader routes this feedback to the appropriate agents with specific improvement instructions.

##### How Stop Works from the Team Leader CLI

When the human types a stop command, the Team Leader:

1. Acknowledges: "Got it. Shutting down the team and saving progress..."
2. Executes `scripts/stop.sh` as a subprocess (or calls the same logic internally).
3. Reports the shutdown progress in real-time: "Backend developer stopped... Frontend developer stopped..."
4. Before its own session ends, confirms: "All agents stopped. Snapshot saved. Run `./forge start` to resume tomorrow."
5. The Team Leader's own Claude Code session then exits.

##### How Resume Works

The next day, the human runs `./forge start` from their terminal. Since a snapshot exists:

```
$ ./forge start
[Forge] Found previous session from 2025-01-15 18:30
[Forge]   Iteration: 3 (phase: EXECUTE)
[Forge]   Agents: 5 active | Cost: $12.50 / $50.00
[Forge]   Resume? [Y/n/fresh]
> Y
[Forge] Resuming...
```

The Team Leader's interactive session starts, it loads its working memory + snapshot, restores the fleet, and greets the human:

```
Team Leader: Session resumed from snapshot. Here's where we left off:
- Iteration 3, phase: EXECUTE
- Backend auth: ✓ Complete
- Payment service: In progress (backend-developer-1, ~60% done)
- Login UI: In progress (frontend-developer, ~40% done)
- 2 unprocessed messages from yesterday's Critic review

All 5 agents are back online. Shall I continue, or would you like to adjust anything first?
```

##### Dual Communication Channels

The Team Leader responds to commands from two sources. Both are always active:

1. **Direct CLI input** (primary): Human types directly in the Team Leader's interactive tmux window. This is the natural, conversational interface.
2. **Override file** (fallback): `shared/.human/override.md` — written to by `./forge tell "<message>"`. Useful when the human doesn't want to attach to the tmux session, or when they want to send a command from a different terminal window.

The Team Leader checks the override file periodically (and at every task boundary), but direct CLI input is processed immediately since it's the active conversation.

- In Co-Pilot and Micro-Manage modes, approval requests are presented directly in the Team Leader's interactive session for the human to respond to.
- In ALL modes (including Auto Pilot), the Team Leader monitors `shared/.human/override.md` for messages sent via `./forge tell`.

#### Team Leader Working Memory
The Team Leader's working memory file (`shared/.memory/team-leader-memory.md`) is critical. It must persist:
- Complete project requirements summary.
- Current iteration number and status.
- Full agent roster with current assignments.
- Dependency graph between agents/tasks.
- Decisions made and their rationale.
- Current blockers and their resolution status.
- Cost tracking totals.
- Mode and strategy in effect.

This file must be updated after every significant action. If the Team Leader's Claude Code session resets, it reads this file first to fully restore context before resuming.

---

### 3. Project Modes (in `config/team-config.yaml`)

The user selects one of three modes. Each mode dictates quality thresholds, testing requirements, architecture complexity, documentation depth, and Critic pass rate thresholds.

#### MVP Mode
- Goal: Working prototype the human can run locally and test functionality.
- Simple but clear usage guidelines (README with setup + run instructions).
- Minimal tests covering core functionality (happy paths).
- Basic documentation explaining what was built and how to use it.
- Single repository is fine. Monolith is acceptable.
- Focus on speed of delivery over architectural perfection.
- Feedback mechanism: Team Leader writes `FEEDBACK-REQUEST.md` at project root when ready for human testing.
- **Critic pass rate threshold: 70%** — applied per category (Functional, Technical, User-Quality). Core features must work and deliver genuine user value, minor gaps acceptable.

#### Production Ready Mode
- Everything in MVP plus:
- Comprehensive documentation (API docs, architecture diagrams, developer guides).
- CI pipelines (GitHub Actions) with pre-commit hooks and linting.
- Code coverage >90% with coverage reports (codecov or equivalent).
- Integration tests that mock external paid services but use real local services (databases, caches, queues spun up via Docker Compose).
- LLM calls must go through `llm-gateway` plugin. Use `local-claude` mode for integration testing when enabled — this calls Claude CLI locally to get actual LLM responses for quality verification.
- Industrial coding standards: proper error handling, logging, monitoring hooks, graceful degradation.
- **Separate repositories/projects** where architecturally appropriate — even for small reusable plugins if they serve multiple projects. No monolithic "backend + frontend" repos. Enforce service boundaries using Domain-Driven Design (DDD) with bounded contexts.
- Scalable infrastructure considerations in all design decisions.
- **Critic pass rate threshold: 90%** — applied per category. All major features must pass technical AND user-quality standards.

#### No Compromise Mode
- Everything in Production Ready plus:
- Zero tolerance on feature completeness — every specified feature must be implemented with the best available algorithm, service, or package, chosen with long-term planning in mind.
- Highly scalable architecture — designed for horizontal scaling, with clear capacity planning.
- All infrastructure as code (Terraform, Pulumi, or equivalent), tested locally using LocalStack.
- Single-click deployment: running one script should take the project from code to live production.
- Zero tolerance for bugs, edge case failures, or functionality breaks — exhaustive testing including chaos/fault injection where applicable.
- Cost estimation and tracking: the team must produce cost estimates for infrastructure (compute, storage, network, third-party services) and actual project development costs (token usage).
- Full traceability: every decision, change, and deployment must be traceable.
- The human should be able to launch the product to market directly from this output.
- When choosing between quality and cost optimization, prefer quality — but document the cost implications.
- **Critic pass rate threshold: 100%** — zero tolerance across all categories. Every criterion must pass in Functional, Technical, AND User-Quality.

#### Mode Switching
The human can switch modes mid-session by instructing the Team Leader (via message or `shared/.human/override.md`). The Team Leader must handle the transition gracefully (see Team Leader section above).

---

### 4. Execution Strategies (in `config/team-config.yaml`)

#### Auto Pilot
- Zero human intervention. Team makes all decisions.
- Cost cap: configurable in `team-config.yaml`. Team Leader monitors total estimated token usage across all agents and the project's own LLM usage (via `llm-gateway`'s `local-claude` mode).
- `no-cap` option: unlimited development spend, but always optimize the project's runtime costs.
- Even on `no-cap`, track and report all costs for visibility.
- The `llm-gateway` plugin supports model switching in `local-claude` mode — use cheaper models for routine tasks, more capable models for complex reasoning, to optimize within budget.
- Human can still intervene via `shared/.human/override.md` at any time (see Section 18).

#### Co-Pilot
- Design approvals required: architecture decisions, technology choices, major refactors.
- No permission needed for: file operations, shell commands, web searches, package installations.
- This applies to ALL agents across ALL tmux sessions, not just the Team Leader.
- Approval mechanism: agent writes to `shared/.decisions/pending-approval.md`, waits for human response.

#### Micro-Manage
- Every significant project decision requires human approval.
- More detailed questions — don't just present a choice, explain tradeoffs thoroughly.
- Only proceed autonomously when confidence is very high.
- All permissions required for commands that modify state.

---

### 5. Configuration File (`config/team-config.yaml`)

The configuration uses YAML for reliable programmatic parsing. Project requirements (which can be lengthy prose) are kept in a separate markdown file referenced by the config.

#### `config/team-config.yaml`
```yaml
# ==============================================================================
# Forge — AI Software Forge — Project Configuration
# ==============================================================================

# --- Project Requirements ---
# Provide EITHER inline description OR a file path to a detailed requirements doc.
# For complex projects, use a separate file for clarity.
project:
  description: ""  # Short description (use for simple projects)
  requirements_file: "config/project-requirements.md"  # Path to detailed requirements (overrides description if set)
  type: "new"  # "new" for greenfield | "existing" for brownfield
  existing_project_path: ""  # Required if type is "existing"

# --- Project Mode ---
# mvp              — Working prototype, minimal tests, basic docs
# production-ready — CI/CD, >90% coverage, DDD, separate repos, industrial standards
# no-compromise    — Zero tolerance, IaC tested with LocalStack, single-click deploy, market-ready
mode: "mvp"

# --- Execution Strategy ---
# auto-pilot   — Zero human intervention, all decisions autonomous
# co-pilot     — Design approvals required, skip command permissions
# micro-manage — Every significant decision needs approval
strategy: "co-pilot"

# --- Cost Configuration ---
cost:
  max_development_cost: 50  # Max USD for the development session. Use "no-cap" for unlimited.
  max_project_runtime_cost: "no-cap"  # Max USD for project's own runtime costs (infra, API calls).

# --- Agent Team ---
# team_profile controls the default agent roster.
#   "lean"   — 8 agents with merged roles (best for MVP, cost-efficient, less coordination overhead)
#   "full"   — 12 agents with specialized roles (best for Production Ready / No Compromise)
#   "custom" — You define exactly which agents to include via include list below
# See Section 6 for the full agent roster and merge rationale.
agents:
  team_profile: "auto"  # "auto" (lean for MVP, full for production-ready+) | "lean" | "full" | "custom"
  exclude: []  # Remove agents from the profile. e.g., ["security-tester", "performance-engineer"]
  additional: []  # Add agents beyond the profile. e.g., ["performance-engineer", "data-engineer"]
  include: []  # Only used when team_profile is "custom". e.g., ["team-leader", "architect", "backend-developer", "qa-engineer", "critic"]

# --- CLAUDE.md Configuration ---
# Controls how existing CLAUDE.md files are incorporated into agent instruction files.
# Claude Code uses CLAUDE.md files for project-specific conventions, coding standards,
# and preferences. This config controls whether/how those are respected.
claude_md:
  # Which CLAUDE.md sources to incorporate when generating agent-specific instruction files.
  # Options:
  #   "project"  — Use the project's own CLAUDE.md (best for brownfield/existing projects
  #                 that already have established conventions). Falls back to global if not found.
  #   "global"   — Use the global ~/.claude/CLAUDE.md (user's personal coding preferences).
  #                 Falls back to none if not found.
  #   "both"     — Merge both: project CLAUDE.md takes precedence, global fills gaps.
  #                 Project-level rules override global rules where they conflict.
  #   "none"     — Don't incorporate any external CLAUDE.md. Agents use only their own
  #                 instruction files. Use this for a clean, reproducible setup.
  source: "both"

  # Priority order when source is "both" and there are conflicts:
  #   "project-first" — Project CLAUDE.md overrides global (recommended for brownfield)
  #   "global-first"  — Global CLAUDE.md overrides project (rare, for enforcing personal standards)
  priority: "project-first"

  # Path overrides (optional, auto-detected if empty):
  global_path: ""  # Default: ~/.claude/CLAUDE.md
  project_path: ""  # Default: {project_root}/CLAUDE.md

# --- Technology Preferences ---
# Leave empty for the team to decide based on project requirements.
tech_stack:
  languages: []  # e.g., ["typescript", "python"]
  frameworks: []  # e.g., ["nextjs", "fastapi"]
  databases: []  # e.g., ["postgresql", "redis"]
  infrastructure: []  # e.g., ["aws", "docker", "kubernetes"]

# --- LLM Gateway Configuration ---
llm_gateway:
  local_claude_model: "claude-sonnet-4-20250514"  # Model for local-claude integration testing
  enable_local_claude: true  # Enable local-claude mode for integration tests
  cost_tracking: true  # Track LLM token usage and costs

# --- Bootstrap Template ---
# Templates are REFERENCE scaffolding, not rigid blueprints.
# The Architect adapts templates to match actual project requirements.
# Set to "auto" for the Architect to select the best match(es).
# For complex projects, the Architect may compose from multiple templates.
bootstrap_template: "auto"  # "auto" (Architect selects) | template name | comma-separated names | ""

# --- Session Management ---
session:
  snapshot_retention: 5  # Number of fleet snapshots to keep (oldest deleted first)
  auto_stop_after_hours: 0  # Auto-stop fleet after N hours (0 = disabled). Safety net for Auto Pilot.
  shutdown_grace_period_seconds: 60  # Time agents get to finalize memory before forced shutdown

# --- Usage Limit Management ---
# Claude Code has usage limits that refresh periodically. These settings control
# how the framework detects, saves state, and auto-resumes when limits are hit.
usage_limits:
  proactive_save_interval_hours: 4  # Agents proactively save state after N hours of continuous work (0 = disabled)
  estimated_refresh_window_hours: 1  # Estimated time for limits to refresh (watchdog uses this for auto-resume timing)
  auto_resume_after_limit: true  # Watchdog auto-resumes agents after estimated refresh window
  fleet_limit_threshold: 3  # If N+ agents hit limits, trigger full fleet stop to preserve all state
  scheduled_resume_time: ""  # Optional: specific time to resume (e.g., "06:00" for next morning). Overrides auto-resume.
```

#### `config/project-requirements.md`
```markdown
# Project Requirements

Describe your project in detail here. Include:

- What the project does (features, user stories, use cases).
- Who the target users are.
- Any specific technical constraints or preferences.
- Third-party services or APIs the project needs to integrate with.
- Performance requirements, scale expectations.
- Any existing documentation, wireframes, or specs (reference file paths).

<!-- Example:
Build a real-time collaborative document editor with the following features:
- Rich text editing with formatting toolbar
- Real-time collaboration (multiple users editing simultaneously)
- Document version history
- User authentication and authorization
- Document sharing via links with permission levels
- Export to PDF and DOCX
-->
```

#### `.gitignore`
```
# Runtime directories (created by scripts, never committed)
shared/

# Generated project-specific agent files
.forge/

# Environment files with secrets
.env
.env.local
.env.*.local

# Secret vault
shared/.secrets/vault.env

# Temporary files
/tmp/forge-*
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.code-workspace
```

#### `config/team-config.example.yaml`
A fully filled-in example showing a realistic project configuration. This helps users understand what values to use.
```yaml
# ==============================================================================
# EXAMPLE: Real-time Collaborative Document Editor
# ==============================================================================

project:
  description: ""
  requirements_file: "config/project-requirements.md"
  type: "new"
  existing_project_path: ""

mode: "production-ready"
strategy: "co-pilot"

cost:
  max_development_cost: 100
  max_project_runtime_cost: "no-cap"

agents:
  team_profile: "auto"  # Will select "full" since mode is production-ready
  exclude: []
  additional: []
  include: []

claude_md:
  source: "both"
  priority: "project-first"
  global_path: ""
  project_path: ""

tech_stack:
  languages: ["typescript"]
  frameworks: ["nextjs", "prisma", "tailwind"]
  databases: ["postgresql", "redis"]
  infrastructure: ["docker", "aws"]

llm_gateway:
  local_claude_model: "claude-sonnet-4-20250514"
  enable_local_claude: true
  cost_tracking: true

bootstrap_template: "auto"

session:
  snapshot_retention: 5
  auto_stop_after_hours: 8
  shutdown_grace_period_seconds: 60

usage_limits:
  proactive_save_interval_hours: 4
  estimated_refresh_window_hours: 1
  auto_resume_after_limit: true
  fleet_limit_threshold: 3
  scheduled_resume_time: ""
```

---

### 6. Individual Agent Specifications

#### Team Profiles & Context Efficiency Rationale

Each agent is a separate Claude Code session with its own context window. More agents means more context windows (more cost), more inter-agent message passing (lossy communication), and more coordination overhead. The tradeoff is **specialization vs. context efficiency**: a specialist agent has focused context but needs more information from others; a generalist agent has broader context but fewer coordination needs.

Forge provides two default team profiles, plus a custom option:

##### Lean Team (8 agents) — Default for MVP

| Agent | Replaces | Why Merged |
|-------|----------|-----------|
| Team Leader | — | Orchestration is always distinct |
| **Research & Strategy Lead** | Researcher + Strategist | Research flows directly into strategy. Splitting them forces the Strategist to re-absorb research context via lossy message summaries. One agent that researches, retains all nuance, and then strategizes produces much better plans. Strategy revisions trigger more research — tight loop in one context. |
| Systems Architect | — | System design is cross-cutting and reviews everyone's work |
| Backend Developer | — | Core implementation; multiple instances for parallel work |
| **Frontend Engineer** | Frontend Designer + Frontend Developer | Modern frontend dev is iterative: design a component → implement → see it doesn't work visually → adjust design → re-implement. Splitting this across two agents adds round-trip overhead for every design decision. One agent that designs the component hierarchy, implements it, and visually verifies in the same context produces tighter feedback loops and fewer design-implementation mismatches. |
| **QA Engineer** | Manual Tester + Automation Tester | Both need to understand the full application behavior. The manual testing discovers bugs; the automation tester writes tests for the same scenarios. In separate agents, you duplicate the entire app understanding across two context windows AND pay message-passing overhead for every bug found. A single QA Engineer runs the app, finds issues, writes tests, and tracks coverage — all in one context. **This merge is always recommended regardless of team profile.** |
| DevOps Specialist | — | Infrastructure is distinct from application code |
| Critic | — | Independence is its entire purpose |

**Lean team advantage**: ~40% fewer context windows, ~60% less inter-agent messaging, significantly lower token cost. Ideal for MVP where speed and cost matter more than deep specialization.

##### Full Team (12 agents) — Default for Production Ready / No Compromise

All lean team agents, PLUS these specialists split out or added:

| Agent | Why Separate in Full Team |
|-------|--------------------------|
| Researcher (standalone) | In production-ready projects, research is deeper and ongoing — benchmarking vendors, analyzing competitors, reviewing academic papers. The volume of research justifies a dedicated context. |
| Strategist (standalone) | Production-ready strategy involves complex tradeoff analysis, capacity planning, multi-milestone roadmaps, and risk matrices. Dedicated context prevents research noise from crowding strategic thinking. |
| Frontend UI/UX Designer (standalone) | For production-ready, the design system is a first-class artifact: design tokens, component library specs, accessibility audit, responsive breakpoints. This volume warrants its own context. |
| Frontend Developer (standalone) | Implementation of a production-grade design system is complex enough to fill its own context: component testing, accessibility compliance, performance optimization, state management patterns. |
| Security Tester | Security review MUST be independent from the developers who wrote the code — same developer doing their own security review has blind spots. Separate agent ensures objective analysis. |
| Performance Engineer (NEW) | Nobody in the lean team owns load testing, profiling, query optimization, caching strategy, or capacity planning. Critical for production-ready and essential for no-compromise. |
| Documentation Specialist | Production-ready docs are comprehensive: API reference, architecture diagrams, operational runbooks, contributing guides. Cross-cutting review of all agents' docs ensures consistency. |

**Full team advantage**: Deep specialization, objective security/performance reviews, comprehensive documentation. Worth the higher cost for production-grade output.

**Note**: QA Engineer is always merged (never split into Manual + Automation) in both profiles. The context overlap between manual testing and test automation is too high to justify separate agents. If more testing capacity is needed, spawn multiple QA Engineer instances working on different features.

##### Auto Selection (`team_profile: "auto"`)
- MVP mode → Lean team
- Production Ready mode → Full team
- No Compromise mode → Full team + Performance Engineer always included

The user can override by setting `team_profile` to `lean`, `full`, or `custom`, and can further adjust with `exclude` and `additional` lists.

---

#### Agent Definitions

Below are the detailed role definitions. **Merged agents** (Research & Strategy Lead, Frontend Engineer, QA Engineer) have their own MD files that combine the responsibilities of their constituent roles. The standalone versions also exist for full team mode.

##### Research & Strategy Lead (`agents/research-strategist.md`) — Lean Team

**Merges**: Researcher + Strategist into a single agent.

- Gathers context about the problem domain, existing solutions, relevant libraries/frameworks/services.
- Produces research reports (`shared/.decisions/research-{topic}.md`) with findings, comparisons, and recommendations.
- Uses research output AND project requirements to produce the technical strategy document.
- Defines milestones, iteration plan, risk assessment, and success criteria.
- Produces `shared/.decisions/strategy.md` and `shared/.decisions/iteration-plan.md`.
- Works with Architect to validate technical feasibility.
- Revisits strategy after each iteration based on progress and blockers — triggers new research when needed without inter-agent round-trips.
- In Production Ready / No Compromise modes: researches best-in-class solutions, benchmarks, and industry standards.
- Registers all research reports and strategy artifacts in the artifact registry.

##### Researcher (`agents/researcher.md`) — Full Team Only

- Gathers context about the problem domain, existing solutions, relevant libraries/frameworks/services.
- Produces research reports (`shared/.decisions/research-{topic}.md`) with findings, comparisons, and recommendations.
- Answers questions from other agents about domain-specific topics.
- In Production Ready / No Compromise modes: researches best-in-class solutions, benchmarks, industry standards, academic papers, competitor analysis.
- Uses web search, documentation reading, and GitHub repository analysis.
- Registers research reports in the artifact registry so dependent agents are notified of updates.

##### Strategist (`agents/strategist.md`) — Full Team Only

- Takes research output and project requirements to produce a technical strategy document.
- Defines milestones, iteration plan, risk assessment, success criteria, and capacity planning.
- Works with Architect to validate technical feasibility of the strategy.
- Produces `shared/.decisions/strategy.md` and `shared/.decisions/iteration-plan.md`.
- Revisits strategy after each iteration based on progress and blockers.
- In No Compromise mode: produces detailed risk matrices, go-to-market timeline, and cost projection models.
- Registers strategy and iteration plan as artifacts; notifies Team Leader and Architect of any changes.

##### Systems Architect (`agents/architect.md`) — Both Profiles

- Designs the system architecture: service boundaries, data models, API contracts, infrastructure topology.
- Produces architecture diagrams (as Mermaid in markdown), API specs (OpenAPI/Swagger), database schemas, and infrastructure diagrams.
- Selects and recommends a bootstrap template from `templates/` for the initial project scaffold when applicable.
- In Production Ready mode: enforces DDD, defines bounded contexts, specifies separate repository boundaries.
- In No Compromise mode: designs for horizontal scaling, defines capacity planning, specifies infrastructure-as-code requirements.
- Reviews all significant code changes for architectural compliance.
- Works closely with DevOps Specialist on infrastructure design.
- **Artifact ownership**: API specs, database schemas, and architecture docs are critical artifacts. When these change, the artifact registry must trigger notifications to all downstream agents.

##### Backend Developer (`agents/backend-developer.md`) — Both Profiles

- Implements server-side code based on Architect's designs and API specs.
- Writes clean, well-documented, vendor-agnostic code with proper abstraction layers.
- Integrates `llm-gateway` for any LLM functionality in the project.
- Produces working code, database migrations, API endpoints, background jobs, etc.
- Writes unit tests for their own code (basic in MVP, comprehensive in Production Ready+).
- Follows the Git workflow (see Section 14): feature branches with naming convention `agent/backend-developer-{N}/{task-id}`, meaningful commits, PRs for Team Leader review.
- **Must acquire file locks** (see Section 16) before editing any file that other agents might also be working on.
- Multiple instances can run in parallel for independent services/microservices.

##### Frontend Engineer (`agents/frontend-engineer.md`) — Lean Team

**Merges**: Frontend UI/UX Designer + Frontend Developer into a single agent.

- Designs AND implements the user interface: wireframes → component hierarchy → design system → working code.
- Produces wireframes (as markdown descriptions or simple HTML mockups), then implements them directly.
- Builds reusable components, handles state management, API integration, routing.
- Ensures accessibility and responsive design compliance — designs with these constraints from the start rather than retrofitting.
- In MVP: simple, functional design implemented quickly. Tight design-implement-verify loop in one context.
- In Production Ready+: polished design system with component library, design tokens, and comprehensive component tests.
- Vendor-agnostic approach: abstract API client layer, configurable themes, pluggable auth.
- **Must acquire file locks** before editing shared code files.

##### Frontend UI/UX Designer (`agents/frontend-designer.md`) — Full Team Only

- Designs the user interface and user experience based on project requirements.
- Produces wireframes (as markdown descriptions or simple HTML mockups), user flow diagrams, component hierarchy, and design system specifications.
- Specifies accessibility requirements, responsive design breakpoints, and interaction patterns.
- In Production Ready+: polished, consistent design system with design tokens, spacing scales, color palettes, and typography.
- Reviews Frontend Developer's implementation for design compliance.

##### Frontend Developer (`agents/frontend-developer.md`) — Full Team Only

- Implements the frontend based on Designer's specs and Architect's API contracts.
- Builds reusable components, handles state management, API integration, routing, etc.
- Writes unit tests and component tests (comprehensive for Production Ready+).
- Ensures accessibility and responsive design compliance.
- Vendor-agnostic approach: abstract API client layer, configurable themes, pluggable auth.
- **Must acquire file locks** before editing shared code files.

##### QA Engineer (`agents/qa-engineer.md`) — Both Profiles (Always Merged)

**Merges**: Manual Tester + Automation Tester. **This merge is permanent** — even in full team mode, testing stays in one agent because the context overlap is too high to justify separation.

- **Manual testing**: Tests the integrated system from an end-user perspective. Writes test plans and executes them by running the application and verifying behavior. Produces bug reports with reproduction steps, expected vs actual behavior, severity ratings.
- **Automated testing**: Writes automated test suites: unit tests, integration tests, and E2E tests. Configures test runners, coverage reporters, and CI test pipelines.
- **Unified workflow**: Discovers bugs manually → immediately writes automated regression tests for those bugs → verifies fixes pass both manual and automated checks. This tight loop in one context eliminates the "found bug, wrote report, sent to other agent, other agent reads report, tries to reproduce, writes test" overhead.
- In MVP: smoke testing core flows + basic test coverage for core functionality.
- In Production Ready: comprehensive test plans + >90% code coverage, integration tests with Docker-based services, mock external paid APIs but use real local services.
- In No Compromise: exhaustive testing including edge cases, error scenarios, performance tests, chaos testing.
- Uses `llm-gateway` in `local-claude` mode for integration tests that involve LLM calls (when enabled in config).
- Files bugs to `shared/.queue/team-leader-inbox/` for triage and assignment.
- Multiple instances can run in parallel for different feature areas.

##### DevOps Specialist (`agents/devops-specialist.md`) — Both Profiles

- Sets up CI/CD pipelines (GitHub Actions), Docker configurations, infrastructure-as-code.
- In MVP: simple Dockerfile and docker-compose for local development.
- In Production Ready: full CI pipeline with linting, testing, building, and deployment stages. Pre-commit hooks.
- In No Compromise: Terraform/Pulumi for infrastructure, LocalStack for local testing of cloud resources, single-click deployment scripts, monitoring and alerting setup.
- Follows Architect's infrastructure topology designs.
- Manages separate repository creation when required by Production Ready / No Compromise modes.

##### Security Tester (`agents/security-tester.md`) — Full Team (or added explicitly)

- Performs security analysis of the codebase and infrastructure **independently** from the developers who wrote the code.
- In MVP (if included): basic security checklist (no hardcoded secrets, input validation, HTTPS).
- In Production Ready: OWASP Top 10 review, dependency vulnerability scanning, auth/authz testing.
- In No Compromise: penetration testing simulation, security headers audit, rate limiting verification, data encryption at rest and in transit verification, compliance check relevant to the domain.
- Produces security reports with severity ratings, remediation steps, and verification criteria.
- **Must be a separate agent** — developers reviewing their own code for security have inherent blind spots.

##### Performance Engineer (`agents/performance-engineer.md`) — Full Team (NEW)

- Owns all performance-related concerns: load testing, profiling, query optimization, caching strategy, bundle size optimization, and capacity planning.
- In Production Ready: sets up basic load testing (k6, Artillery, or equivalent), profiles database queries, identifies N+1 query issues, recommends indexing strategies, measures and optimizes frontend bundle size and core web vitals.
- In No Compromise: comprehensive load testing with realistic traffic patterns, stress testing to find breaking points, profiling under load to identify bottlenecks, cache warming strategies, CDN configuration recommendations, capacity planning documents with projected costs at various traffic levels.
- Works closely with Backend Developer (query optimization), Frontend Engineer/Developer (bundle size, rendering performance), and Architect (capacity planning).
- Produces performance reports with benchmarks, bottleneck analysis, and specific optimization recommendations.
- Registers performance benchmarks as artifacts so regressions can be detected in future iterations.

##### Documentation Specialist (`agents/documentation-specialist.md`) — Full Team (or added explicitly)

- Documents everything: API docs, architecture docs, developer guides, user guides, deployment guides.
- Maintains documentation structure and consistency.
- In MVP (if included): README with setup/run instructions, basic API documentation.
- In Production Ready: comprehensive docs including architecture diagrams, API reference, contributing guide, changelog.
- In No Compromise: all of the above plus operational runbooks, incident response procedures, capacity planning docs, cost analysis docs.
- Reviews all other agents' documentation contributions for quality and completeness.
- Maintains a living `docs/` directory structure in the project.
- **In lean team mode** (when this agent is absent): documentation responsibilities are distributed — each agent documents its own work, and the Team Leader reviews for consistency.

##### Critic / Devil's Advocate (`agents/critic.md`) — Both Profiles

- **Core mandate**: Remember the human's original requirements and goals at all times. Never compromise. The Critic evaluates TWO dimensions: (1) technical quality and (2) user-facing quality — both must pass.
- At project start, generates `shared/.iterations/acceptance-criteria.md` — a scored checklist of non-negotiable acceptance criteria derived from the original project requirements and the selected mode's quality standards. Each criterion has a unique ID and is marked pass/fail after each iteration.

###### Two Dimensions of Quality

**Dimension 1 — Technical Quality** (what the existing review pipeline already covers):
- Code correctness, test coverage, security, performance, architecture compliance.
- This is what the Architect, QA Engineer, and Security Tester also review. The Critic validates their conclusions independently.

**Dimension 2 — User-Facing Quality** (the Critic's UNIQUE contribution — no other agent owns this):
- **Result quality**: Does the feature produce genuinely useful, accurate, actionable results for the end user? Not just "does the feature work" but "does it work WELL from the user's perspective?"
- **Data freshness**: If the feature involves external data (job listings, news, prices, availability), is the data current? Stale data is a user-facing bug even if the code is technically correct.
- **Actionable outputs**: If the feature produces recommendations, links, or suggestions, are they specific and actionable? A job board that links to generic company career pages instead of specific job postings is technically functional but useless. A travel planner that suggests "visit Paris" without specific restaurants, timings, or booking links is low-quality output.
- **Edge case UX**: What happens when the user inputs something unexpected, empty, or at the boundary? Does the UI show a helpful message or a blank screen? Does the API return a useful error or a stack trace?
- **Completeness from user's perspective**: The user asked for X — did they get X, or did they get a technically-correct approximation that misses the point? If the requirement says "show nearby restaurants with ratings and prices", showing restaurants without prices is a user-facing quality failure.
- **Realistic testing with real-world scenarios**: The Critic must test features with realistic user scenarios, not just synthetic test data. If the project is a resume builder, the Critic should evaluate with an actual resume's worth of content, not `test_name` and `test_email@example.com`.

###### Acceptance Criteria Categories

Every acceptance criterion must be categorized:

```markdown
## Acceptance Criteria: {project-name}

### Functional Requirements (from project requirements)
- [AC-F001] {criterion} — Category: FUNCTIONAL
- [AC-F002] {criterion} — Category: FUNCTIONAL

### Technical Quality
- [AC-T001] Test coverage meets mode threshold — Category: TECHNICAL
- [AC-T002] No critical security vulnerabilities — Category: TECHNICAL
- [AC-T003] API response times under {threshold} — Category: TECHNICAL

### User-Facing Quality
- [AC-U001] {Feature X} produces specific, actionable results (not generic placeholders) — Category: USER-QUALITY
- [AC-U002] All external data displayed to users is fresh (within {timeframe}) — Category: USER-QUALITY
- [AC-U003] Error states show user-friendly messages with clear next steps — Category: USER-QUALITY
- [AC-U004] Core user workflows tested with realistic data and scenarios — Category: USER-QUALITY
- [AC-U005] Output links/URLs are specific and functional (not generic landing pages) — Category: USER-QUALITY
```

The Critic must generate USER-QUALITY criteria for every user-facing feature. These are NOT optional — a feature that passes all FUNCTIONAL and TECHNICAL criteria but fails USER-QUALITY criteria is NOT done.

###### Scoring & Reports

- After each iteration, independently reviews ALL work against these criteria and produces a scored report:
  - Each criterion: `PASS` or `FAIL` with evidence.
  - Overall pass rate as a percentage.
  - **Separate pass rates per category**: Functional X%, Technical Y%, User-Quality Z%. All three must independently meet the mode threshold.
  - Specific improvement demands for each `FAIL`.
  - For USER-QUALITY failures: include specific examples of what the user would experience and what "good" looks like.
- **Enforcement mechanism**: The Team Leader cannot proceed to the next iteration unless the Critic's pass rate meets the mode's threshold:
  - MVP: ≥70% pass rate (per category — 70% Functional AND 70% Technical AND 70% User-Quality)
  - Production Ready: ≥90% pass rate (per category)
  - No Compromise: 100% pass rate (veto power — any single FAIL in any category blocks progress)
- Sends improvement demands to Team Leader — the Team Leader must address them or provide explicit justification for overriding (only allowed in MVP mode, and the override must be logged in the decision log).
- Should flag scope creep, feature drift, quality degradation, **and user experience degradation** (features that technically work but have gotten worse from the user's perspective across iterations).
- The Critic's acceptance criteria file is an artifact in the registry — if requirements change, the Critic updates criteria (including user-quality criteria) and notifies all agents.

###### User-Quality Review Examples

To illustrate the Critic's user-facing quality bar:

| Feature | TECHNICAL PASS but USER-QUALITY FAIL | What USER-QUALITY PASS looks like |
|---------|--------------------------------------|-----------------------------------|
| Job search | Returns results from API, displays in UI, tests pass. Links go to company career pages. | Returns results with direct job posting URLs, posted date visible, stale listings (>30 days) filtered out, salary range shown when available. |
| Restaurant finder | Fetches restaurants from API, shows names and addresses. | Shows restaurants with ratings, price range, photos, hours, distance from user, and a "directions" link. Handles "no results" with helpful suggestions. |
| Email drafter | Generates email text based on prompt. | Generates email with appropriate tone for context, correct greeting/sign-off, reasonable length, and specific content (not vague platitudes). Offers 2-3 variants for sensitive messages. |
| Dashboard | Charts render with correct data. | Charts have clear labels, appropriate scales, color-blind-friendly palette, responsive on mobile, loading states, and empty-state messages. Key metrics are highlighted, not buried. |
| Authentication | Login/signup works, tokens are valid. | Login remembers last email, shows password requirements upfront (not just on failure), "forgot password" flow is complete and sends actual emails, OAuth buttons are prominent, error messages are specific ("wrong password" not just "authentication failed"). |

The Critic should generate similar examples for the specific project being built and use them as the basis for USER-QUALITY acceptance criteria.

---

### 7. Scripts & CLI

#### `forge` — Unified CLI Entry Point

The `forge` script is the single entry point for all human interactions with the framework. It removes the need to remember individual script names.

```bash
# First-time setup
./forge setup

# Initialize a new project (interactive config generation)
./forge init
# Prompts: project name, mode, strategy, tech stack → generates team-config.yaml

# Start a new project session
./forge start

# Start — but if a previous session snapshot exists, auto-prompt to resume
./forge start
# Output: "Found previous session snapshot from 2025-01-15 18:30 (iteration 3, phase: EXECUTE). Resume? [Y/n]"

# Explicitly resume from a specific snapshot
./forge start --snapshot shared/.snapshots/snapshot-1705312200.json

# Stop the fleet (graceful shutdown with snapshot)
./forge stop
./forge stop --pause   # Stop agents but keep tmux session alive for inspection

# Check fleet status without entering tmux
./forge status

# View aggregated cost report
./forge cost

# Send a natural language command to Team Leader without entering tmux
./forge tell "Switch to production-ready mode"
./forge tell "Pause all work"
./forge tell "What's the status of the payment service?"

# Attach to Team Leader's interactive tmux session
./forge attach

# View combined logs
./forge logs
./forge logs --agent backend-developer-1
./forge logs --tail
```

##### `forge` Internal Logic

```
./forge start
    │
    ├── Has snapshot in shared/.snapshots/?
    │   ├── YES → Prompt: "Resume from {snapshot}? [Y/n/fresh]"
    │   │          ├── Y → calls scripts/resume.sh
    │   │          ├── n → exits
    │   │          └── fresh → archives old snapshot, calls scripts/start.sh (new session)
    │   └── NO → calls scripts/start.sh (new session)
    │
./forge stop
    │
    └── calls scripts/stop.sh (graceful shutdown + snapshot)
    │
./forge init
    │
    └── Interactive project setup wizard:
        1. Prompts for project name, description
        2. Prompts for mode (MVP/Production Ready/No Compromise)
        3. Prompts for strategy (Auto Pilot/Co-Pilot/Micro-Manage)
        4. Prompts for tech preferences (optional)
        5. Generates config/team-config.yaml + config/project-requirements.md
    │
./forge tell "<message>"
    │
    └── writes message to shared/.human/override.md
        (Team Leader and monitoring loop pick it up)
```

The key insight: `./forge start` is the ONLY command the human needs to remember for running. It handles both fresh starts and resumption seamlessly. `./forge init` is a convenience — the human can also just edit `team-config.yaml` directly.

##### `forge init` Implementation

The `forge init` command runs an interactive wizard that generates `config/team-config.yaml` and `config/project-requirements.md`. It asks:

1. **Project name**: Free text → sets in config header comment
2. **Project description**: Free text → writes to `config/project-requirements.md`
3. **New or existing project?** → sets `project.type` to `"new"` or `"existing"`. If existing, asks for path → sets `project.existing_project_path`
4. **Mode**: Choice of MVP / Production Ready / No Compromise → sets `mode`
5. **Strategy**: Choice of Auto Pilot / Co-Pilot / Micro-Manage → sets `strategy`
6. **Cost cap**: Number or "no-cap" → sets `cost.max_development_cost`
7. **Tech preferences** (optional): Languages, frameworks, databases → sets `tech_stack` fields
8. **Template** (optional): Auto or specific name → sets `bootstrap_template`

Uses simple `read -p` prompts with sensible defaults (mode: mvp, strategy: co-pilot, cost: 50, template: auto). Writes the YAML using `cat` heredocs (no dependency on `yq` for generation — `yq` is only needed for parsing during `start`).

#### `setup.sh`
- Checks prerequisites: `claude` CLI installed, `tmux` installed, `git` installed, `docker` installed (for Production Ready+), `yq` installed (for YAML parsing).
- Installs any missing tools where possible (or provides instructions).
- Validates the `config/team-config.yaml` file has been filled in and is valid YAML.
- Creates the `shared/` directory structure with all subdirectories.
- Makes all scripts executable.
- Symlinks `./forge` to the system path if the user opts in.

#### `scripts/start.sh`
- Called by `./forge start` for fresh sessions (not resume).
- Reads `config/team-config.yaml` using `yq`.
- Starts a new tmux session named `forge-{project-name}`.
- Runs `scripts/init-project.sh` to generate project-specific agent files.
- Starts `scripts/watchdog.sh` as a background daemon in its own tmux window.
- Starts `scripts/log-aggregator.sh` as a background daemon in its own tmux window.
- Spawns the Team Leader agent in an **interactive** tmux window — the human can directly type to the Team Leader here. This is the primary human ↔ Team Leader interface (see Section 22).
- The Team Leader then takes over and spawns other agents as needed.
- In ALL modes: the monitoring loop watches `shared/.human/override.md` for messages written via `./forge tell`.
- In Co-Pilot/Micro-Manage modes: additionally watches `shared/.decisions/pending-approval.md` and forwards approval requests to the Team Leader's interactive window for the human to see.

#### `scripts/stop.sh`
- Called by `./forge stop` OR by the Team Leader when the human types a stop command in the Team Leader's interactive session.
- Gracefully shuts down the entire agent fleet and captures a state snapshot for later resumption.
- Sequence:
  1. Broadcasts a `PREPARE_SHUTDOWN` message to all agents via `broadcast.sh`, giving them the configured grace period (default 60 seconds) to finalize working memory and commit in-progress work.
  2. After grace period, collects a fleet state snapshot (see Section 22) and writes it to `shared/.snapshots/snapshot-{timestamp}.json`.
  3. Broadcasts a `SHUTDOWN` message to all agents.
  4. Waits up to 30 seconds for agents to acknowledge and gracefully exit.
  5. Force-kills any remaining tmux windows in the `forge-{project-name}` session.
  6. Kills the watchdog and log-aggregator daemons.
  7. Destroys the tmux session.
  8. Prints a summary: snapshot file path, agents stopped, iteration status, and the command to resume.
- Can also be invoked with `--pause` flag which stops agents but keeps the tmux session alive for inspection.

#### `scripts/resume.sh`
- Called by `./forge resume` or by `./forge start` when the user chooses to resume.
- Arguments: `--snapshot <path>` (optional — defaults to the most recent snapshot in `shared/.snapshots/`).
- Sequence:
  1. Reads the snapshot file to reconstruct the fleet state.
  2. Validates that the project directory and `shared/` state are intact.
  3. Starts a new tmux session `forge-{project-name}`.
  4. Starts watchdog and log-aggregator daemons.
  5. Spawns the Team Leader in an **interactive** window with `--resume` flag. The Team Leader's working memory + snapshot summary are loaded as initial context.
  6. Team Leader reads the snapshot, determines which agents need to be restarted, and spawns them with `--resume` flag.
  7. Each agent loads its working memory, catches up on any unprocessed inbox messages, and resumes from its "Next Steps".
  8. Team Leader sends a status check to all agents and writes an iteration status update.
  9. The human can now type directly to the Team Leader to give further instructions.
- Usage: `./forge resume` (uses latest snapshot) or `./forge resume --snapshot shared/.snapshots/snapshot-1705312200.json`.

#### `scripts/spawn-agent.sh`
- Arguments: `--agent-type <type>`, `--instance-id <id>` (optional, for multiple instances), `--project-dir <path>`, `--resume` (optional, to resume from working memory).
- Creates a new tmux window named `{agent-type}-{instance-id}`.
- Creates the agent's inbox directory: `shared/.queue/{agent-name}-inbox/`.
- Launches a Claude Code session in that window using the exact invocation pattern (see Section 12).
- If `--resume` flag is set: includes the agent's working memory file (`shared/.memory/{agent-name}-memory.md`) as initial context for session recovery.
- Writes agent status as `idle` to `shared/.status/{agent-name}.json`.
- Registers the agent with the watchdog by writing to `shared/.status/{agent-name}.json` with `session_start` timestamp.

#### `scripts/kill-agent.sh`
- Gracefully stops an agent: writes a `SHUTDOWN` message to its inbox directory, waits for acknowledgment (up to 30 seconds), then kills the tmux window.
- Updates agent status to `terminated` in status file.
- Does NOT delete the agent's working memory — it persists for potential restart.

#### `scripts/broadcast.sh`
- Writes a message file to ALL active agents' inbox directories simultaneously (e.g., mode switch notifications, emergency stops).
- Uses atomic `mv` for each write to prevent partial reads.

#### `scripts/status.sh`
- Reads all files in `shared/.status/` and prints a formatted summary table of agent states.
- **Stale detection**: Flags any agent whose `last_updated` timestamp is more than 5 minutes old as `POSSIBLY STALE`.
- **Dead detection**: Cross-references with tmux window list — if an agent has a status file but no tmux window, flags as `DEAD`.
- Shows cost summary from `scripts/cost-tracker.sh` output.
- Shows last snapshot info if one exists.

#### `scripts/init-project.sh`
- Reads `config/team-config.yaml` using `yq`.
- **Resolves team profile**: Based on `agents.team_profile` and `mode`, determines which agent MD files to use (lean merged agents vs. full team standalone agents). Applies `exclude` and `additional` overrides.
- **Resolves CLAUDE.md sources** (see Section 23):
  1. Reads `claude_md.source` from config.
  2. If `"global"` or `"both"`: loads `~/.claude/CLAUDE.md` (or custom `global_path`).
  3. If `"project"` or `"both"`: loads `{project_root}/CLAUDE.md` (or custom `project_path`). For brownfield projects, this is the existing project's CLAUDE.md.
  4. If `"both"`: merges the two files with the configured priority. Project-specific rules override global rules where they conflict.
  5. If `"none"`: skips CLAUDE.md entirely.
- **Generates project-specific agent files**: Takes each agent's template MD file, injects the project context (requirements, mode, strategy, tech preferences, non-negotiable principles), and prepends the resolved CLAUDE.md guidelines as a `## Project-Wide Conventions` section at the top of each agent file. This ensures every agent inherits the same coding standards, style preferences, and architectural patterns.
- Places generated agent files in `{project_root}/.forge/agents/`.
- Initializes the project's git repository if `project_type: new`.
- If `bootstrap_template` is set (or "auto"), copies the matching template from `templates/` to scaffold the project. If "auto", the Team Leader / Architect will decide later.

#### `scripts/cost-tracker.sh`
- Reads structured logs from `shared/.logs/` and extracts cost-related entries.
- Estimates token usage per agent based on log entries and session duration.
- Reports estimated cost per agent and total.
- Alerts if approaching the configured cost cap.
- Outputs a JSON summary to `shared/.logs/cost-summary.json`.

#### `scripts/watchdog.sh`
- Runs as a background daemon in its own tmux window.
- Every 60 seconds:
  1. Checks all agent status files in `shared/.status/`.
  2. Cross-references with tmux window list (`tmux list-windows`).
  3. For any agent whose tmux window has died: writes a `CRITICAL` message to Team Leader's inbox reporting the dead agent.
  4. For any agent whose `last_updated` is stale (>5 minutes): writes a `WARNING` message to Team Leader's inbox.
  5. For rate-limited or crashed sessions: detects error patterns in `shared/.logs/{agent-name}.log` and reports to Team Leader.
  6. **Usage limit monitoring**: Checks agent status files for `usage_limits.status` == `"rate-limited"` or `"approaching-limit"`. Checks agent logs for rate limit error patterns (HTTP 429, "rate limit", "usage limit", "too many requests", "capacity"). When detected, writes a `LIMIT_DETECTED` message to Team Leader's inbox with the affected agent name and estimated wait time if available.
  7. **Auto-resume after limits refresh**: For agents with status `rate-limited`, periodically checks (every 5 minutes) whether the limit has likely refreshed by attempting a lightweight probe. When limits appear refreshed, notifies Team Leader to restart the agent with `--resume`.
- The Team Leader then decides: restart the agent with `spawn-agent.sh --resume`, reassign its tasks, or escalate to human.

#### `scripts/log-aggregator.sh`
- Runs as a background daemon.
- Tails all agent log files in `shared/.logs/`.
- Produces a combined, chronologically ordered log at `shared/.logs/combined.log`.
- Rotates logs when they exceed 10MB.

---

### 8. Inter-Agent Communication Protocol (`docs/AGENT-PROTOCOL.md`)

Define a simple, file-based protocol since all agents share the same filesystem. This protocol must handle concurrent access safely.

#### Message Format

Each message is an individual file in the target agent's inbox directory. This avoids append conflicts on a single file.

```
File: shared/.queue/{target-agent}-inbox/msg-{unix-timestamp}-{sender}.md
```

```markdown
---
id: msg-1705312200-backend-developer-1
from: backend-developer-1
to: team-leader
priority: normal  # normal | high | critical
timestamp: 2025-01-15T10:30:00Z
type: status-update  # status-update | request | response | blocker | deliverable | review-request | review-response | dependency-change
confidence: high  # high | medium | low (required on deliverable and status-update types, see Section 29)
---

## Subject: API endpoints for user service complete

Body of the message with details...

### Artifacts
- `src/services/user-service/routes.ts`
- `src/services/user-service/controllers/`

### Needs From
- Frontend Developer: integration testing
- QA Engineer: endpoint test coverage
```

#### Atomic Write Protocol

To prevent any agent from reading a partially written message:

```bash
# Writer: create temp file, then move atomically
TEMP_FILE=$(mktemp /tmp/forge-msg-XXXXXX.md)
# ... write message content to $TEMP_FILE ...
mv "$TEMP_FILE" "shared/.queue/${TARGET_AGENT}-inbox/msg-$(date +%s)-${MY_NAME}.md"
```

```bash
# Reader: process messages in timestamp order, delete after processing
for msg in $(ls shared/.queue/${MY_NAME}-inbox/ | sort); do
  # ... process message ...
  rm "shared/.queue/${MY_NAME}-inbox/$msg"
done
```

#### Status File Format

Valid `status` values: `idle`, `working`, `blocked`, `review`, `done`, `suspended`, `rate-limited`, `error`, `terminated`.

```json
{
  "agent": "backend-developer-1",
  "status": "working",
  "current_task": "Implementing user authentication endpoints",
  "blockers": [],
  "iteration": 2,
  "last_updated": "2025-01-15T10:30:00Z",
  "session_start": "2025-01-15T08:00:00Z",
  "artifacts_produced": ["src/services/user-service/"],
  "estimated_completion": "30 minutes",
  "messages_processed": 15,
  "usage_limits": {
    "warnings_detected": 0,
    "last_warning_at": null,
    "status": "normal"
  },
  "cost_estimate_usd": 1.25
}
```

---

### 9. Non-Negotiable Principles

These must be embedded in EVERY agent's instructions:

1. **Vendor Agnostic Code**: All external dependencies (databases, caches, cloud services, LLM providers, auth providers, payment processors, etc.) must be behind abstract interfaces with pluggable implementations. Easy to switch vendors in the future.

2. **LLM Gateway Mandate**: Any LLM functionality in the project being built MUST use the `llm-gateway` plugin (https://github.com/Rushabh1798/llm-gateway). If the plugin needs new features or vendor implementations, update the plugin repo directly (it's owned by us). Use `local-claude` mode for integration testing to get actual LLM responses for quality verification.

3. **Cost Optimization**: Dual concern — optimize the cost of the AI development process (token usage across agents) AND optimize the project's own runtime costs (infrastructure, API calls, etc.). Always report costs transparently.

4. **Reusability of Forge Repo**: The repository itself must be well-documented and configurable enough for others to clone and use for their own projects with minimal changes. The README must be comprehensive.

5. **Existing Project Support**: The framework must handle both greenfield (new) projects and brownfield (existing) projects. For existing projects, agents must first understand the current codebase before making changes.

6. **Working Memory Persistence**: Every agent must maintain its working memory file. Sessions can and will restart — the agent must be able to fully resume from its working memory alone (see Section 13).

7. **Artifact Registration**: Every produced artifact must be registered in the artifact registry. Every consumed artifact must be declared as a dependency. Changes to artifacts trigger downstream notifications (see Section 15).

8. **Usage Limit Self-Preservation**: Every agent must monitor for signs of approaching Claude Code usage limits and execute the `LIMIT_SAVE` protocol immediately when detected — saving working memory, checkpoint-committing, releasing locks, and notifying the Team Leader — all BEFORE the session is killed. The 10-minute memory update rule is the safety net for cases where limits hit without warning (see Section 20).

9. **User-Facing Quality**: Features must not only work correctly but deliver genuine value to the end user. Technical correctness is necessary but not sufficient. The Critic evaluates every user-facing feature for result quality (are outputs specific and useful, not generic?), data freshness (is external data current, not stale?), actionability (do links go to specific resources, not generic pages?), and realistic UX (tested with real-world scenarios, not synthetic test data). All agents must build with the end user's experience in mind, not just technical requirements.

---

### 10. README.md Requirements

The repository's README must include:

1. **What is Forge**: Clear explanation of the concept — a team of AI agents that collaborate to build software.
2. **Prerequisites**: Claude Code CLI, tmux, git, docker (for Production Ready+), Node.js, Python, `yq` (for YAML parsing).
3. **Quick Start**: 5-step guide: clone → `./forge setup` → edit `config/team-config.yaml` (or run `./forge init`) → `./forge start` → talk to Team Leader.
4. **Configuration Guide**: Detailed explanation of every field in `team-config.yaml` with examples.
5. **Agent Roster & Team Profiles**: Lean team (8 agents) vs Full team (12 agents) comparison table. Which agents are merged and why. When to use each profile. How `auto` selects based on mode.
6. **CLAUDE.md Integration**: How Forge respects existing CLAUDE.md files. Source options (project, global, both, none). How brownfield projects inherit existing conventions. How to configure priority.
7. **Mode Comparison**: Table comparing MVP vs Production Ready vs No Compromise (including Critic thresholds and default team profile).
8. **Strategy Comparison**: Table comparing Auto Pilot vs Co-Pilot vs Micro-Manage.
9. **Human Override**: How to intervene in any mode using the override channel.
10. **Stopping & Resuming Sessions**: Three ways to stop (talk to Team Leader, `./forge stop`, override file). How `./forge start` auto-detects snapshots for seamless resume. What snapshots contain, edge cases (manual changes, config changes, partial resume).
11. **Customization**: How to add custom agents, modify existing ones, change team composition, switch between team profiles.
12. **Templates**: Full catalog of available templates by category, how templates work (reference not mandate), how multi-template composition works, how to add custom templates, AI/ML template special notes regarding llm-gateway.
13. **Troubleshooting**: Common issues and solutions, including agent recovery, session restarts, usage limit handling, and secret management.
14. **Cost Management**: How cost tracking works, how to set budgets, how to optimize. Include comparison of lean vs full team cost implications.
15. **Advanced Orchestration**: How parallel work streams work, integration testing protocol, code review protocol, environment configuration strategy.
16. **Contributing**: Link to CONTRIBUTING.md.

#### `docs/ARCHITECTURE.md` Content Requirements
- How Forge's own architecture works (not the user's project). Include:
  - Diagram of the agent orchestration flow (Team Leader → agents → shared filesystem).
  - How tmux sessions map to agents. How the shared/ directory enables communication.
  - The iteration lifecycle with all 7 phases explained.
  - How the working memory system prevents context loss.
  - How the watchdog, log-aggregator, and cost-tracker work as background daemons.
  - How stop/resume captures and restores fleet state via snapshots.
  - How the CLAUDE.md hierarchy flows from global → project → agent files.
  - Design decisions and tradeoffs (file-based messaging vs. database, tmux vs. docker containers, etc.).

#### `docs/CONTRIBUTING.md` Content Requirements
- How to contribute to the Forge framework itself. Include:
  - How to add a new agent type (create MD file with all 12 sections, register in team profiles, update init-project.sh).
  - How to add a new template (create directory with README, PATTERNS.md, scaffold, template-config.yaml; add to manifest).
  - How to modify existing agents (which sections to update, how to test changes).
  - How to add new scripts or CLI commands.
  - Code style for bash scripts (set -euo pipefail, error handling patterns, help flags).
  - How to test changes (dry run process).
  - PR guidelines, issue templates.

#### `docs/EXAMPLES.md` Content Requirements
- Walkthrough examples showing Forge in action. Include at minimum:
  - **Example 1: MVP SaaS App** — Full walkthrough from config to running agents. Show the team-config.yaml, what happens when `./forge start` runs, how agents communicate, what the first iteration looks like, and what output the human gets.
  - **Example 2: Adding AI Features to Existing Project** — Brownfield project example. Show `project.type: "existing"`, how agents analyze the codebase, how CLAUDE.md is inherited, and how agents respect existing conventions.
  - **Example 3: Production-Ready with Full Team** — Show the difference between lean and full team, how Security Tester and Performance Engineer add value, what a No Compromise Critic review looks like.
  - For each example: show the key config, key agent interactions (sample messages), iteration flow, and final output.

---

### 11. Implementation Order

Build the repository in this sequence:

1. **Phase 1 — Foundation**: Create directory structure, `.gitignore`, `LICENSE`, `config/team-config.yaml` template, `config/team-config.example.yaml`, `config/project-requirements.md`.
2. **Phase 2 — Base Protocol**: Write `agents/_base-agent.md` — the shared protocol loaded by ALL agents. Must consolidate ALL cross-cutting concerns into one file: message queue protocol, status reporting, working memory mandate, structured logging, decision log, git workflow, file locking, artifact registration, error handling, human override monitoring, graceful shutdown (PREPARE_SHUTDOWN), usage limit detection (LIMIT_SAVE), vendor-agnostic mandate, LLM gateway mandate, CLAUDE.md compliance, secret safety rules, confidence signaling, and memory compaction. Also write `docs/AGENT-PROTOCOL.md` with the full inter-agent communication spec.
3. **Phase 3 — Core Scripts & CLI**: `forge` unified CLI entry point, `setup.sh`, `scripts/start.sh`, `scripts/spawn-agent.sh`, `scripts/kill-agent.sh`, `scripts/status.sh`, `scripts/broadcast.sh`. The `forge` script must handle auto-detection of snapshots for seamless resume-on-start.
4. **Phase 4 — Infrastructure Scripts**: `scripts/watchdog.sh`, `scripts/log-aggregator.sh`, `scripts/cost-tracker.sh`.
5. **Phase 5 — Session Management Scripts**: `scripts/stop.sh` (fleet snapshot + graceful shutdown), `scripts/resume.sh` (restore fleet from snapshot).
6. **Phase 6 — Team Leader**: Write the complete `agents/team-leader.md` — this is the most critical file. Must include: interactive session design (human types directly to Team Leader), natural language command handling (all command categories from Section 2), session stop/resume orchestration, parallel work stream management (Section 26), integration checkpoint coordination (Section 27), code review routing, confidence-based routing rules (Section 29), memory compaction triggers (Section 31), and all orchestration duties. This file must be 350-450 lines.
7. **Phase 7 — Agent Files**: Write ALL other agent MD files. Each must have all 12 required sections (Section 1). Include role-specific details from Section 6 definitions. Cross-cutting protocols (secrets, confidence, code review format, compaction) are inherited from `_base-agent.md` — each agent file should reference the base protocol and add role-specific behavior on top. Write both merged versions (research-strategist, frontend-engineer, qa-engineer) and standalone versions (researcher, strategist, frontend-designer, frontend-developer). Also write performance-engineer.md and documentation-specialist.md.
8. **Phase 8 — Critic System**: Write `agents/critic.md` with: scored acceptance criteria across three categories (Functional, Technical, User-Quality), per-category pass rate enforcement, mode-specific thresholds (70%/90%/100% applied independently to each category), user-facing quality evaluation methodology (result quality, data freshness, actionability, realistic scenario testing), and example quality criteria table showing PASS vs FAIL for common feature types.
9. **Phase 9 — Init Script**: `scripts/init-project.sh` with YAML parsing via `yq`, team profile resolution (lean vs full vs custom), CLAUDE.md source resolution and merging, template selection, secret vault directory setup, and project-specific agent file generation to `{project_root}/.forge/agents/`.
10. **Phase 10 — Templates**: Create template library. **Priority templates first** (full scaffold): `python-fastapi`, `node-express-api`, `react-spa`, `nextjs-fullstack`, `langchain-agent`, `rag-pipeline`. Each needs: `README.md`, `PATTERNS.md`, `scaffold/` with working starter code, `template-config.yaml`. **Then stub templates** for all remaining 28: each gets `README.md` (what it would provide), `PATTERNS.md` (patterns without implementation), `template-config.yaml`, and a minimal `scaffold/` placeholder. Write `templates/_template-manifest.yaml` with full metadata for all 34. AI/ML templates must demonstrate `llm-gateway` integration patterns.
11. **Phase 11 — Documentation**: `README.md` (comprehensive, 400-500 lines, per Section 10), `docs/ARCHITECTURE.md`, `docs/CONTRIBUTING.md`, `docs/EXAMPLES.md`.
12. **Phase 12 — Verification & Polish**: Review all files for consistency. Verify: every agent MD has all 12 sections, all cross-references point to correct section numbers, all script paths match the directory tree, all status values use the canonical set, all message formats match the spec, `.gitignore` covers all generated/runtime files. Make all scripts executable (`chmod +x`). Ensure every script has `set -euo pipefail`, `--help` handling, and proper error messages.

---

### 12. Claude Code Invocation Specification

This is the exact method for launching Claude Code sessions for each agent. Every script that spawns an agent must use this pattern.

#### Base Command
```bash
# spawn-agent.sh core logic
AGENT_NAME="${AGENT_TYPE}-${INSTANCE_ID}"
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
BASE_PROTOCOL="agents/_base-agent.md"
MEMORY_FILE="shared/.memory/${AGENT_NAME}-memory.md"

# Agent MD file: use the project-specific generated version (which already includes
# merged CLAUDE.md guidelines from init-project.sh) if it exists, otherwise fall back
# to the template version from agents/
GENERATED_AGENT_MD="${PROJECT_DIR}/.forge/agents/${AGENT_TYPE}.md"
TEMPLATE_AGENT_MD="agents/${AGENT_TYPE}.md"
AGENT_MD="${GENERATED_AGENT_MD}"
[ ! -f "$AGENT_MD" ] && AGENT_MD="${TEMPLATE_AGENT_MD}"

# The project's CLAUDE.md is also loaded directly so Claude Code's native CLAUDE.md
# handling can apply. The generated agent MD already has the merged guidelines baked in,
# but loading the raw CLAUDE.md ensures Claude Code's built-in behavior also respects it.
PROJECT_CLAUDE_MD="${PROJECT_DIR}/CLAUDE.md"

# Build the initial prompt that loads the agent's context
INITIAL_PROMPT="You are ${AGENT_NAME}. Read and follow these instruction files carefully:
1. Your agent instructions (includes project-specific conventions): $(cat ${AGENT_MD})
2. Base protocol: $(cat ${BASE_PROTOCOL})"

# Add project CLAUDE.md if it exists (for Claude Code's native handling)
if [ -f "$PROJECT_CLAUDE_MD" ]; then
  INITIAL_PROMPT="${INITIAL_PROMPT}
3. Project CLAUDE.md (respect these conventions): $(cat ${PROJECT_CLAUDE_MD})"
fi

# Add working memory for session recovery
if [ "$RESUME" = true ] && [ -f "$MEMORY_FILE" ]; then
  INITIAL_PROMPT="${INITIAL_PROMPT}
4. YOUR PREVIOUS SESSION STATE (resume from here): $(cat ${MEMORY_FILE})"
fi

# Add any pending inbox messages
INBOX_DIR="shared/.queue/${AGENT_NAME}-inbox"
if [ -d "$INBOX_DIR" ] && [ "$(ls -A $INBOX_DIR 2>/dev/null)" ]; then
  INITIAL_PROMPT="${INITIAL_PROMPT}
5. PENDING MESSAGES IN YOUR INBOX:"
  for msg in $(ls "$INBOX_DIR" | sort); do
    INITIAL_PROMPT="${INITIAL_PROMPT}
--- MESSAGE: $msg ---
$(cat "$INBOX_DIR/$msg")"
  done
fi

# Launch in tmux window
# CRITICAL: Team Leader runs in INTERACTIVE mode (human types directly to it).
# All other agents run in HEADLESS mode (instructions piped in, no human interaction).
if [ "${AGENT_TYPE}" = "team-leader" ]; then
  # Interactive mode: write instructions to a temp file, then start Claude Code
  # in interactive mode with --resume or by reading the instruction file first.
  INSTRUCTION_FILE=$(mktemp /tmp/forge-init-XXXXXX.md)
  echo "${INITIAL_PROMPT}" > "$INSTRUCTION_FILE"
  tmux new-window -t "forge-${PROJECT_NAME}" -n "${AGENT_NAME}" \
    "cd ${PROJECT_DIR} && claude --resume || cat '${INSTRUCTION_FILE}' | claude"
  # The Team Leader's tmux window stays open for human input.
  # If Claude Code supports --system-prompt or --init-file, use that instead.
else
  # Headless mode: pipe instructions, agent works autonomously
  tmux new-window -t "forge-${PROJECT_NAME}" -n "${AGENT_NAME}" \
    "cd ${PROJECT_DIR} && echo '${INITIAL_PROMPT}' | claude --print --output-format text"
fi
```

**Note on Team Leader interactive mode**: The Team Leader's tmux window is the human's primary interface. After the initial prompt loads the Team Leader's context, the session stays open for the human to type natural language commands. The exact Claude Code flags for interactive mode may vary — `setup.sh` should detect the installed version and determine:
- If Claude Code supports `--system-prompt <file>`: use that to load context, then run interactively.
- If Claude Code supports `--resume` with conversation persistence: prefer that.
- Fallback: pipe the initial context, then use `/chat` or similar to continue interactively.
- The key requirement is that after initial context loading, the human can type freely.

#### Notes on Claude Code CLI
- The exact CLI flags may vary based on the Claude Code version installed. The `setup.sh` script should detect the installed version and adapt.
- If Claude Code supports a `--system-prompt` flag, use that instead of piping. Check `claude --help` during setup.
- If Claude Code supports a `--continue` or `--resume` flag for session persistence, prefer that over manual working memory. But always maintain working memory as a fallback.
- The `INITIAL_PROMPT` approach (piping context into claude) is the most universally compatible method.

---

### 13. Agent Memory & Context Persistence

Claude Code sessions have finite context windows. Long-running agents will eventually lose early context. Every agent must proactively manage its own persistent memory to survive context overflow and session restarts.

#### Working Memory File

Each agent maintains: `shared/.memory/{agent-name}-memory.md`

#### Required Structure
```markdown
# Working Memory: {agent-name}
## Last Updated: {ISO 8601 timestamp}

## Session Info
- Session started: {timestamp}
- Current iteration: {N}
- Messages processed this session: {count}

## My Current Assignment
{Description of what this agent is currently working on}

## Completed Work This Session
- {task 1}: {status} — {artifact produced}
- {task 2}: {status} — {artifact produced}

## Key Decisions Made
- {decision 1}: {rationale}
- {decision 2}: {rationale}

## Dependencies I'm Waiting On
- {agent}: {what I need from them}

## Important Context
{Any domain-specific knowledge, constraints, or discoveries that would be lost if the session restarted. For developers, this includes: which files they've modified, architectural patterns they're following, gotchas they've discovered.}

## Next Steps
1. {next task}
2. {next task}
```

#### Memory Update Rules
- Update working memory after completing any task or subtask.
- Update working memory after any significant decision.
- Update working memory after processing any message from another agent.
- **Update working memory at least every 10 minutes during active work.** This is non-negotiable — it is the safety net for abrupt session kills from usage limits. If the session dies without warning, the last memory update determines how much context is lost.
- On `LIMIT_SAVE` trigger: update working memory IMMEDIATELY with the Limit Save Context section (see Section 20), even if a regular update was recent.
- The working memory file must be self-sufficient: reading it alone should give the agent everything needed to resume work.

#### Session Recovery Protocol
When an agent starts with the `--resume` flag (triggered by watchdog or Team Leader after a crash):
1. Read working memory file.
2. Read current status file.
3. Check inbox for any messages received while the agent was down.
4. Resume from the "Next Steps" section of working memory.
5. Notify Team Leader that session has been recovered.

---

### 14. Git Workflow Specification

Multiple agents committing code simultaneously requires a well-defined Git workflow to prevent conflicts and maintain code integrity.

#### Branch Naming Convention
```
agent/{agent-name}/{task-id}-{short-description}
```
Examples:
- `agent/backend-developer-1/TASK-001-user-auth-endpoints`
- `agent/frontend-developer/TASK-005-login-component`
- `agent/devops-specialist/TASK-010-ci-pipeline`

#### Commit Message Format
```
[{agent-name}] {type}: {short description}

{Optional body explaining what and why}

Task: {task-id}
Iteration: {N}
```
Types: `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, `chore`

Example:
```
[backend-developer-1] feat: implement user registration endpoint

Added POST /api/users/register with email/password validation,
bcrypt hashing, and JWT token generation.

Task: TASK-001
Iteration: 2
```

#### Merge Protocol
- Only the Team Leader merges feature branches into `main`.
- Before merging, Team Leader verifies:
  1. No merge conflicts with current `main`.
  2. Relevant tests pass.
  3. Artifact registry is updated.
- Team Leader uses regular merges (not squash) to preserve agent attribution in git history.
- After each successful iteration, Team Leader tags: `git tag iteration-{N}-verified`.

#### Conflict Resolution
- If two agents have modified the same file (detected via `git diff` against `main`):
  1. Team Leader identifies the conflict.
  2. Team Leader assigns resolution to the agent with deeper context on that file (check file lock history and artifact registry).
  3. The resolving agent merges the other branch into theirs, resolves conflicts, and notifies Team Leader.
- The file locking system (Section 16) should minimize but won't eliminate all conflicts.

---

### 15. Artifact Registry & Dependency Tracking

Agents produce artifacts that other agents depend on. When an artifact changes, downstream agents must be notified.

#### Registry File: `shared/.artifacts/registry.json`

```json
{
  "artifacts": [
    {
      "id": "api-spec-user-service",
      "path": "docs/api/user-service.yaml",
      "type": "api-spec",
      "produced_by": "architect",
      "version": 3,
      "last_updated": "2025-01-15T10:30:00Z",
      "dependents": ["backend-developer-1", "frontend-developer", "qa-engineer"],
      "description": "OpenAPI spec for the User Service"
    },
    {
      "id": "user-auth-implementation",
      "path": "src/services/user-service/auth/",
      "type": "code",
      "produced_by": "backend-developer-1",
      "version": 1,
      "last_updated": "2025-01-15T12:00:00Z",
      "depends_on": ["api-spec-user-service"],
      "dependents": ["qa-engineer", "frontend-developer"],
      "description": "User authentication implementation"
    }
  ]
}
```

#### Protocol
- **Registration**: When an agent produces a new artifact, it appends an entry to `registry.json` (use file locking for concurrent writes).
- **Dependency Declaration**: When an agent starts consuming another agent's artifact, it adds itself to the `dependents` array.
- **Change Notification**: When an agent updates an artifact, it:
  1. Increments the `version` number.
  2. Updates `last_updated`.
  3. Sends a `dependency-change` message to all agents listed in `dependents`.
- **Team Leader Oversight**: The Team Leader periodically reviews the registry to detect circular dependencies, missing dependencies, and orphaned artifacts.

---

### 16. File Locking for Shared Code

When two developers (or any agents) might edit the same source code file, a file locking mechanism prevents wasted work from conflicting edits.

#### Lock File Location
```
shared/.locks/{md5-hash-of-filepath}.lock
```

#### Lock File Contents
```json
{
  "locked_by": "backend-developer-1",
  "file_path": "src/services/user-service/auth/handler.ts",
  "locked_at": "2025-01-15T10:30:00Z",
  "reason": "Implementing password reset flow",
  "expected_duration_minutes": 30
}
```

#### Locking Protocol
1. **Before editing a shared file**: Check if a lock file exists for that filepath hash.
2. **If no lock exists**: Create the lock file atomically (`mv` from temp).
3. **If lock exists**:
   a. Check if the lock is stale (older than `expected_duration_minutes` × 2).
   b. If stale: notify Team Leader, who decides whether to break the lock.
   c. If fresh: send a message to the locking agent requesting coordination. Wait for response or Team Leader mediation.
4. **After committing changes**: Delete the lock file.
5. **On crash recovery**: Watchdog detects dead agent → Team Leader cleans up their stale locks.

#### Scope
- File locking is only required for source code files that multiple agents might edit.
- Configuration files, documentation, and agent-specific files don't need locks.
- The Architect's API specs are read-only for everyone except the Architect — no lock needed, but change notifications are mandatory (via artifact registry).

---

### 17. Structured Logging

Every agent must write structured log entries for debugging, cost tracking, and audit trails.

#### Log File Location
```
shared/.logs/{agent-name}.log
```

#### Log Entry Format
Each line is a JSON object (JSONL format):
```json
{"timestamp": "2025-01-15T10:30:00Z", "agent": "backend-developer-1", "level": "INFO", "category": "task", "message": "Started implementing user registration endpoint", "task_id": "TASK-001", "iteration": 2}
{"timestamp": "2025-01-15T10:45:00Z", "agent": "backend-developer-1", "level": "INFO", "category": "artifact", "message": "Created file src/services/user-service/routes.ts", "file_path": "src/services/user-service/routes.ts"}
{"timestamp": "2025-01-15T10:50:00Z", "agent": "backend-developer-1", "level": "INFO", "category": "cost", "message": "Estimated tokens used in last operation", "tokens_in": 5000, "tokens_out": 2000, "estimated_cost_usd": 0.03}
{"timestamp": "2025-01-15T11:00:00Z", "agent": "backend-developer-1", "level": "ERROR", "category": "error", "message": "Test failure in auth handler", "details": "Expected 200, got 401 for valid credentials"}
```

#### Log Categories
- `task`: Task starts, completions, transitions.
- `artifact`: File creation, modification, deletion.
- `communication`: Messages sent and received.
- `decision`: Decisions made with rationale.
- `cost`: Token usage estimates and cost calculations.
- `error`: Errors, failures, exceptions.
- `recovery`: Session restarts, memory loads, state recovery.

#### Log Rotation
- `log-aggregator.sh` handles rotation when files exceed 10MB.
- Old logs are compressed and moved to `shared/.logs/archive/`.

---

### 18. Human Override Channel

In all execution modes — including Auto Pilot — the human must be able to intervene at any time without killing the session.

#### Override File: `shared/.human/override.md`

```markdown
---
timestamp: 2025-01-15T11:30:00Z
type: directive  # directive | pause | resume | mode-switch | strategy-switch | abort
---

## Directive

{Human writes their instruction here}

<!-- Examples:
- "Stop all frontend work. We're pivoting to API-only for now."
- "Switch to production-ready mode immediately."
- "The authentication approach is wrong. Use OAuth2 with PKCE, not session-based auth."
- "Pause all work. I need to review progress before continuing."
- "Abort the project. Clean up and produce a final status report."
-->
```

#### Monitoring Protocol
- `start.sh` runs a monitoring loop that watches this file for changes (using `inotifywait` or polling).
- When a change is detected:
  1. The monitoring loop reads the override.
  2. Writes a `CRITICAL` priority message to Team Leader's inbox with the override contents.
  3. For `pause` type: also broadcasts a `PAUSE` message to all agents via `broadcast.sh`.
  4. For `abort` type: broadcasts `SHUTDOWN` to all agents and produces a final status report.
- The Team Leader processes the override and adjusts the team's work accordingly.
- After processing, the Team Leader writes an acknowledgment to `shared/.human/override-ack.md` so the human knows their input was received.

#### Agent-Level Monitoring
Every agent must check `shared/.human/override.md` file modification time:
- At the start of every new task.
- After every major operation (file creation, test run, etc.).
- If the file has been modified since the agent last checked: read it and follow any `pause` or `abort` directives immediately, or forward `directive` types to Team Leader if not already addressed.

---

### 19. Iteration Lifecycle Definition

Each iteration follows a formal lifecycle so all agents share a common understanding of the workflow.

#### Iteration Phases

```
┌─────────┐    ┌─────────┐    ┌──────────┐    ┌───────────┐    ┌────────┐    ┌──────────┐    ┌──────────┐
│  PLAN   │───▶│ EXECUTE │───▶│   TEST   │───▶│ INTEGRATE │───▶│ REVIEW │───▶│ CRITIQUE │───▶│ DECISION │
└─────────┘    └─────────┘    └──────────┘    └───────────┘    └────────┘    └──────────┘    └──────────┘
     │              │                                                                              │
     │     (parallel streams                                                                       │
     │      if applicable)        ┌────────────────────────────────────────────────────────────────┘
     │                            │
     │    ┌────┴─────┐
     │    │ PROCEED  │──▶ Next iteration (tag: iteration-{N}-verified) + memory compaction
     │    │ REWORK   │──▶ Back to PLAN with corrective instructions
     │    │ ROLLBACK │──▶ git checkout iteration-{N-1}-verified, then PLAN
     │    │ ESCALATE │──▶ Human approval needed (Co-Pilot/Micro-Manage)
     │    └──────────┘
     │
     ▼
```

#### Phase Details

1. **PLAN** (Team Leader + Research & Strategy Lead)
   - Entry: Start of project or completion of previous iteration's DECISION phase.
   - Activities: Decompose goals into tasks, assign to agents, define success criteria for this iteration. Identify independent features for parallel work streams (see Section 26). Define integration points between streams.
   - Exit: All agents have received their task assignments (organized into work streams if applicable).

2. **EXECUTE** (All assigned agents)
   - Entry: Task assignments received.
   - Activities: Agents work on their tasks. If parallel work streams are active, each stream operates independently with its own agents. Use file locks, update working memory, log progress, register artifacts. Include confidence levels in all deliverable messages (see Section 29).
   - Exit: All agents report status as `review` or `done` for their assigned tasks. Stream-level tests pass.

3. **TEST** (QA Engineer)
   - Entry: All implementation tasks are done (or all streams report done).
   - Activities: Run test suites, perform manual testing, produce bug reports. Run contract tests to verify API conformance before integration.
   - Exit: Test report published. All critical bugs filed. Contract tests pass.

4. **INTEGRATE** (Team Leader + QA Engineer) — *Only when parallel streams are active or multi-component work occurred*
   - Entry: Test phase complete. All streams pass stream-level tests and contract tests.
   - Activities: Merge all work stream branches to integration branch. Run smoke tests. Run cross-component integration tests. Verify API contracts hold end-to-end. See Section 27 for full protocol.
   - Exit: Integration tests pass. Single integrated codebase on main branch. If integration fails: route failures back to responsible agents for fixing.
   - *Skipped when*: Single work stream or single-component iteration with no integration concerns.

5. **REVIEW** (Architect + Security Tester + Documentation Specialist — using structured review protocol, Section 25)
   - Entry: Integration phase complete (or test phase if no integration needed).
   - Activities: Architectural compliance review, security review, documentation completeness check. All reviews follow the formal review request/findings format with severity levels.
   - Exit: Review reports published. All BLOCKERs resolved.

6. **CRITIQUE** (Critic)
   - Entry: Review phase complete.
   - Activities: Score all acceptance criteria (pass/fail) across all three categories: Functional, Technical, and User-Quality. Calculate overall pass rate AND per-category pass rates. For user-facing features, test with realistic scenarios and evaluate result quality, data freshness, actionability, and edge case UX. Produce critique report with specific improvement demands for each FAIL, including user-quality examples showing what "good" looks like.
   - Exit: Critique report published with pass rates (overall and per-category) and specific improvement demands.

7. **DECISION** (Team Leader)
   - Entry: Critique report available.
   - Activities: Evaluate pass rate against mode threshold. Decide next action.
   - Exit: One of:
     - **PROCEED**: Pass rate meets threshold. Tag git `iteration-{N}-verified`. Trigger memory compaction (Section 31). Move to next iteration.
     - **REWORK**: Pass rate below threshold. Create corrective tasks and return to PLAN.
     - **ROLLBACK**: Iteration made things worse. Restore `iteration-{N-1}-verified` tag and return to PLAN.
     - **ESCALATE**: In Co-Pilot/Micro-Manage mode, present status to human for guidance.

---

### 20. Agent Health Checks & Recovery

Agent sessions can fail for many reasons: context overflow, rate limiting, Claude Code crashes, tmux errors, usage limit exhaustion, or unhandled exceptions. The system must detect and recover from these automatically.

#### Health Check Criteria

| Signal | Detection Method | Severity |
|--------|-----------------|----------|
| Tmux window died | `tmux list-windows` doesn't include agent | CRITICAL |
| Status file stale (>5 min) | `last_updated` timestamp check | WARNING |
| Status file stale (>15 min) | `last_updated` timestamp check | CRITICAL |
| Error spike in logs | >5 ERROR entries in last 5 min in `shared/.logs/{agent}.log` | WARNING |
| No log activity (>10 min) | Last log entry timestamp check | WARNING |
| Explicit error status | `status` field is `error` | CRITICAL |
| Usage limit approaching | Agent self-reports `usage_limits.status: "approaching-limit"` | WARNING |
| Usage limit hit | Agent status is `rate-limited` or logs show 429/limit errors | CRITICAL |
| Session killed by limit | Tmux window dies AND last log contains rate limit errors | CRITICAL (LIMIT) |

#### Recovery Protocol

1. **WARNING level**: Watchdog notifies Team Leader. Team Leader sends a health check message to the agent's inbox. If agent responds within 2 minutes, issue resolved.

2. **CRITICAL level**: Watchdog notifies Team Leader with `PRIORITY: CRITICAL`.
   - Team Leader reads the dead agent's working memory from `shared/.memory/{agent-name}-memory.md`.
   - Team Leader checks if the agent had any file locks → releases them.
   - Team Leader runs: `scripts/spawn-agent.sh --agent-type {type} --instance-id {id} --project-dir {dir} --resume`.
   - The restarted agent reads its working memory, catches up on missed messages, and resumes.
   - Team Leader verifies the agent is operational by checking for status updates within 2 minutes.

3. **CRITICAL (LIMIT) level** — Usage limit exhaustion (see detailed protocol below):
   - Do NOT immediately respawn — the new session will hit the same limit.
   - Team Leader marks the agent as `awaiting-limit-refresh`.
   - If the agent successfully executed `LIMIT_SAVE` before dying: the state is fully preserved, just wait for refresh.
   - If the agent died abruptly without `LIMIT_SAVE`: Team Leader checks working memory freshness (last update <10 min ago means state is mostly preserved due to regular memory updates).
   - Watchdog monitors for limit refresh and notifies Team Leader when it's safe to respawn.

4. **Repeated failures** (same agent crashes 3+ times in an hour):
   - Team Leader reassigns the agent's tasks to a new instance or different agent.
   - Logs the issue for human review.
   - In Co-Pilot/Micro-Manage mode: escalates to human.

---

#### Usage Limit Detection & LIMIT_SAVE Protocol

Claude Code has usage limits that refresh periodically. When an agent hits these limits, its session is terminated — potentially mid-task, mid-file-write, or mid-commit. Without proactive handling, all in-flight context is lost. This protocol ensures agents save their state BEFORE limits are hit.

##### How Agents Detect Approaching Limits

Each agent must monitor for these signals during its normal operation:

| Signal | How to Detect | Urgency |
|--------|--------------|---------|
| Claude Code warning messages | CLI output contains "approaching limit", "usage warning", "nearing capacity" | HIGH — execute LIMIT_SAVE immediately |
| Increasing response latency | Responses taking 2-3x longer than earlier in the session | MEDIUM — prepare to save |
| Rate limit errors (HTTP 429) | Tool calls or API requests return 429 status | CRITICAL — save immediately, session may die any moment |
| Explicit limit notifications | Claude Code outputs a limit notification or countdown | CRITICAL — save immediately |
| Session running for extended period | Session active for >4 hours continuously (configurable) | LOW — proactively save state as a precaution |

**Important**: Agents should NOT wait for a hard limit error. The goal is to save state while they still have the ability to execute commands. Once the limit is hit, the agent may not be able to write files.

##### LIMIT_SAVE Protocol (Agent-Side)

When any limit signal is detected, the agent immediately executes this protocol — dropping whatever task it's working on:

```
Agent detects limit signal
        │
        ▼
┌──────────────────────────────┐
│ 1. STOP CURRENT WORK         │  Do not start any new file writes, commands,
│                              │  or tool calls. Finish only the current atomic
│                              │  operation if possible.
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 2. SAVE WORKING MEMORY       │  Update working memory with LIMIT_SAVE context:
│    (HIGHEST PRIORITY)        │  - Exact state of in-flight work
│                              │  - What was being written/modified
│                              │  - Precise resume instructions
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 3. CHECKPOINT COMMIT         │  git add + commit on current branch:
│                              │  "[{agent}] chore: LIMIT_SAVE checkpoint"
│                              │  Even partial work — better saved than lost.
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 4. UPDATE STATUS FILE        │  Set status to "rate-limited"
│                              │  Set usage_limits.status to "rate-limited"
│                              │  Set usage_limits.last_warning_at to now
│                              │  Set usage_limits.limit_save_completed to true
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 5. RELEASE FILE LOCKS        │  Release all held locks to unblock other agents.
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 6. NOTIFY TEAM LEADER        │  Write CRITICAL message to Team Leader inbox:
│                              │  "LIMIT_SAVE executed. Ready for session end.
│                              │   Resume from working memory when limits refresh."
└──────────────────────────────┘
```

The entire LIMIT_SAVE sequence should take <30 seconds. It is designed to use minimal tokens/tool calls since the agent is close to its limit.

##### Working Memory — Limit Save Context

When LIMIT_SAVE is triggered, the working memory must include this section (in addition to the standard Resume Context):

```markdown
## Limit Save Context
- **Trigger**: {what signal triggered the save: "429 error" | "CLI warning" | "latency spike" | "proactive 4hr save"}
- **Timestamp**: {ISO 8601}
- **In-flight operation**: {exact description of what was happening when limit was detected}
- **Files being modified**: {list of files that were open/being written, with what changes were in progress}
- **Checkpoint commit**: {git hash of the LIMIT_SAVE commit, or "failed to commit" if git was unavailable}
- **Uncommitted changes**: {git diff summary of any changes that couldn't be committed}
- **Resume instruction**: {Step-by-step what the agent should do FIRST when it restarts:
  e.g., "1. Check if src/auth/handler.ts was fully written (it was mid-write).
         2. If incomplete, rewrite from the function `handlePasswordReset`.
         3. Run tests to verify state.
         4. Continue with next task: implement /api/users/profile endpoint."}
- **Estimated limit refresh**: {if known, when limits should refresh, otherwise "unknown"}
```

##### Team Leader Response to LIMIT_SAVE

When the Team Leader receives a `LIMIT_SAVE` notification from an agent:

1. **Acknowledge**: Log the limit event in `shared/.decisions/limit-events.md`.
2. **Assess impact**: Check if the rate-limited agent is blocking other agents. If so:
   - Reassign blocked tasks to available agents (if possible without duplicating work).
   - Notify dependent agents that the rate-limited agent is temporarily unavailable.
3. **Do NOT respawn immediately** — the new session will hit the same limit.
4. **Evaluate fleet-wide limit risk**: If one agent hit limits, others may be close. The Team Leader can:
   - Proactively trigger `LIMIT_SAVE` on other agents that have been running for similar durations.
   - Reduce the active agent count temporarily (fewer agents = slower limit consumption).
   - In extreme cases (multiple agents rate-limited): execute a full fleet `stop.sh` to preserve state and resume when limits refresh.
5. **Queue for auto-resume**: Mark the agent for automatic restart when the watchdog detects limits have refreshed.

##### Watchdog — Limit Refresh Detection & Auto-Resume

The watchdog has special handling for rate-limited agents:

1. **Tracking**: Maintains a list of rate-limited agents with their `last_warning_at` timestamps.
2. **Refresh polling**: Every 5 minutes, for each rate-limited agent:
   - Checks if sufficient time has passed since the limit was hit (configurable, default: estimated from the provider's refresh window, typically 1-4 hours).
   - After the estimated refresh window, notifies Team Leader: `LIMIT_REFRESH_LIKELY` for agent `{name}`.
3. **Team Leader auto-resume**: On receiving `LIMIT_REFRESH_LIKELY`, Team Leader spawns the agent with `--resume`. If the agent starts successfully and can execute commands, the limit has refreshed. If it immediately hits limits again, the watchdog increases the wait estimate and tries later.
4. **Fleet-wide resume**: If all agents were stopped due to limits (via `stop.sh`), the watchdog can trigger `resume.sh` after the estimated refresh window, or at a configured time (see `auto_resume_after_limit` config).

##### Configuration

```yaml
# --- Usage Limit Management --- (in team-config.yaml)
usage_limits:
  proactive_save_interval_hours: 4  # Agents proactively LIMIT_SAVE after this many hours of continuous work (0 = disabled)
  estimated_refresh_window_hours: 1  # Estimated time for usage limits to refresh (used by watchdog for auto-resume timing)
  auto_resume_after_limit: true  # Watchdog auto-resumes agents after estimated refresh window
  fleet_limit_threshold: 3  # If this many agents hit limits, trigger full fleet stop.sh to preserve state
  scheduled_resume_time: ""  # Optional: specific time to resume (e.g., "06:00" for next morning). Overrides auto-resume.
```

##### Abrupt Session Kill (No LIMIT_SAVE Possible)

If an agent's session is killed by the limit before it can execute LIMIT_SAVE:

1. **Watchdog detects**: Tmux window dies + last log entries contain limit errors → classified as `CRITICAL (LIMIT)`.
2. **State assessment**: Team Leader reads the agent's working memory. If `last_updated` was within the last 10 minutes (thanks to the "update every 10 minutes" rule), most context is preserved.
3. **Git state check**: Team Leader checks the agent's branch for uncommitted changes (`git stash` can recover them).
4. **Queued for resume**: Same auto-resume flow as a successful LIMIT_SAVE, but the resume instructions may be less precise. The agent will need to verify its state more carefully on restart.

This is why the Memory Update Rule of "update at least every 10 minutes" is critical — it's the safety net for abrupt session kills.

---

### 21. Project Bootstrap Templates

#### Philosophy: Reference, Not Source of Truth

Templates are **scaffolding and pattern libraries**, not rigid blueprints. They serve two purposes:

1. **Scaffolding**: Save 30-60 minutes of boilerplate by providing working project structure, build config, Docker setup, CI skeleton, and dependency manifests.
2. **Pattern reference**: Demonstrate idiomatic patterns for the given stack — how to structure services, where to put tests, how to configure the ORM, how to wire up middleware. Agents use these patterns as a starting point and adapt to the actual project requirements.

**Critical rule**: Templates MUST NOT constrain the Architect's design decisions. If the project requirements call for a different structure, database, or pattern than what the template provides, the Architect overrides the template. The template is a suggestion, the project requirements are the mandate.

**Agents should treat templates as**: "Here's a well-structured example of this stack. Use the patterns and structure that make sense for our project, discard what doesn't, and add what's missing."

#### Template Structure

Each template directory contains:
```
templates/{category}/{template-name}/
├── README.md              # What this template provides, patterns demonstrated, intended use case
├── PATTERNS.md            # Specific patterns this template demonstrates (with explanations of WHY)
├── scaffold/              # The actual template files (selectively copied/adapted to project)
│   ├── src/
│   ├── package.json       # (or requirements.txt, go.mod, etc.)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .gitignore
│   ├── .env.example
│   └── ...
└── template-config.yaml   # Metadata: category, languages, frameworks, tags, suitable modes
```

**Key addition**: `PATTERNS.md` — this file explains the architectural patterns used in the template and WHY they were chosen. This helps agents understand the reasoning, not just the code, so they can make informed decisions about what to keep, adapt, or discard.

#### Template Categories & Manifest

The templates are organized into categories. Each template has rich metadata for intelligent matching.

##### `templates/_template-manifest.yaml`

```yaml
# ==============================================================================
# Forge Template Manifest — Registry of all available project templates
# ==============================================================================
# Templates are REFERENCE scaffolding, not rigid blueprints.
# The Architect selects and adapts templates to match project requirements.
# Multiple templates can be combined for complex projects (e.g., backend + frontend + infra).

categories:
  backend: "Server-side APIs and services"
  frontend: "Client-side applications (web and mobile)"
  fullstack: "Combined frontend + backend in a single project"
  ai-ml: "AI/ML applications, agentic systems, and intelligent pipelines"
  event-driven: "Message queue and event-driven architectures"
  platform: "Platform tools, extensions, bots, and SaaS"
  data: "Data pipelines, ETL, and analytics"
  infrastructure: "Infrastructure as code, deployment, and orchestration"

templates:

  # ============================================================================
  # BACKEND — Server-side APIs and services
  # ============================================================================

  - name: "node-express-api"
    category: "backend"
    description: "Node.js REST API with Express, TypeScript, Prisma ORM, JWT auth"
    languages: ["typescript"]
    frameworks: ["express", "prisma"]
    tags: ["rest", "api", "orm", "auth"]
    suitable_for: ["backend", "api", "microservice"]
    patterns: ["repository pattern", "middleware chain", "DTO validation (zod)", "error handling middleware"]
    min_mode: "mvp"

  - name: "python-fastapi"
    category: "backend"
    description: "Python API with FastAPI, SQLAlchemy, Alembic migrations, Pydantic v2"
    languages: ["python"]
    frameworks: ["fastapi", "sqlalchemy", "alembic"]
    tags: ["rest", "api", "orm", "async", "openapi-auto"]
    suitable_for: ["backend", "api", "microservice"]
    patterns: ["repository pattern", "dependency injection", "async handlers", "Pydantic models"]
    min_mode: "mvp"

  - name: "go-microservice"
    category: "backend"
    description: "Go microservice with Gin, GORM, Docker multi-stage build, structured logging"
    languages: ["go"]
    frameworks: ["gin", "gorm"]
    tags: ["rest", "api", "microservice", "high-performance"]
    suitable_for: ["backend", "microservice"]
    patterns: ["clean architecture", "interface-driven design", "graceful shutdown", "health checks"]
    min_mode: "production-ready"

  - name: "graphql-api"
    category: "backend"
    description: "GraphQL API with Apollo Server (TS) or Strawberry (Python), DataLoader pattern"
    languages: ["typescript", "python"]
    frameworks: ["apollo-server", "strawberry"]
    tags: ["graphql", "api", "dataloader", "subscriptions"]
    suitable_for: ["backend", "api", "bff"]
    patterns: ["resolver pattern", "DataLoader batching", "schema-first design", "auth directives"]
    min_mode: "mvp"

  - name: "grpc-service"
    category: "backend"
    description: "gRPC service with Protobuf definitions, streaming support, health checks"
    languages: ["go", "python", "typescript"]
    frameworks: ["grpc", "protobuf"]
    tags: ["grpc", "rpc", "protobuf", "inter-service", "streaming"]
    suitable_for: ["backend", "microservice", "inter-service-communication"]
    patterns: ["proto-first design", "interceptors/middleware", "streaming patterns", "service reflection"]
    min_mode: "production-ready"

  # ============================================================================
  # FRONTEND — Client-side applications
  # ============================================================================

  - name: "react-spa"
    category: "frontend"
    description: "React SPA with TypeScript, Vite, React Router, Tailwind, Zustand/React Query"
    languages: ["typescript"]
    frameworks: ["react", "vite", "tailwind"]
    tags: ["spa", "web", "responsive"]
    suitable_for: ["frontend", "spa", "dashboard"]
    patterns: ["component composition", "custom hooks", "API client abstraction", "route-based code splitting"]
    min_mode: "mvp"

  - name: "vue-spa"
    category: "frontend"
    description: "Vue 3 SPA with TypeScript, Vite, Vue Router, Pinia, Tailwind"
    languages: ["typescript"]
    frameworks: ["vue", "vite", "pinia", "tailwind"]
    tags: ["spa", "web", "responsive"]
    suitable_for: ["frontend", "spa", "dashboard"]
    patterns: ["composables", "Pinia stores", "route guards", "auto-import"]
    min_mode: "mvp"

  - name: "react-native-mobile"
    category: "frontend"
    description: "React Native mobile app with Expo, TypeScript, React Navigation, Zustand"
    languages: ["typescript"]
    frameworks: ["react-native", "expo"]
    tags: ["mobile", "ios", "android", "cross-platform"]
    suitable_for: ["mobile", "app"]
    patterns: ["screen navigation", "platform-specific code", "offline-first", "push notifications"]
    min_mode: "mvp"

  - name: "flutter-mobile"
    category: "frontend"
    description: "Flutter cross-platform mobile app with Riverpod, GoRouter, Dio HTTP client"
    languages: ["dart"]
    frameworks: ["flutter", "riverpod"]
    tags: ["mobile", "ios", "android", "cross-platform"]
    suitable_for: ["mobile", "app"]
    patterns: ["BLoC/Riverpod state management", "repository pattern", "platform channels"]
    min_mode: "mvp"

  # ============================================================================
  # FULLSTACK — Combined frontend + backend
  # ============================================================================

  - name: "nextjs-fullstack"
    category: "fullstack"
    description: "Next.js App Router with Prisma, NextAuth, Server Components, API routes"
    languages: ["typescript"]
    frameworks: ["nextjs", "prisma", "nextauth"]
    tags: ["fullstack", "ssr", "web"]
    suitable_for: ["fullstack", "web-app", "saas"]
    patterns: ["server components", "server actions", "middleware auth", "optimistic UI"]
    min_mode: "mvp"

  - name: "nuxt-fullstack"
    category: "fullstack"
    description: "Nuxt 3 full-stack with Nitro server, Drizzle ORM, Nuxt Auth"
    languages: ["typescript"]
    frameworks: ["nuxt", "nitro", "drizzle"]
    tags: ["fullstack", "ssr", "web"]
    suitable_for: ["fullstack", "web-app"]
    patterns: ["auto-imports", "server routes", "composable data fetching", "hybrid rendering"]
    min_mode: "mvp"

  - name: "t3-stack"
    category: "fullstack"
    description: "T3 Stack: Next.js + tRPC + Prisma + Tailwind, end-to-end type safety"
    languages: ["typescript"]
    frameworks: ["nextjs", "trpc", "prisma", "tailwind"]
    tags: ["fullstack", "type-safe", "web"]
    suitable_for: ["fullstack", "web-app", "saas"]
    patterns: ["end-to-end type safety", "tRPC routers", "Prisma schemas", "type-safe API client"]
    min_mode: "mvp"

  - name: "django-fullstack"
    category: "fullstack"
    description: "Django full-stack with Django REST Framework or HTMX, Celery for background tasks"
    languages: ["python"]
    frameworks: ["django", "drf", "celery"]
    tags: ["fullstack", "web", "admin"]
    suitable_for: ["fullstack", "web-app", "admin-heavy"]
    patterns: ["Django ORM", "class-based views", "Celery tasks", "Django admin customization"]
    min_mode: "mvp"

  # ============================================================================
  # AI/ML — Agentic AI, intelligent pipelines, ML serving
  # ============================================================================

  - name: "langchain-agent"
    category: "ai-ml"
    description: "Agentic AI with LangChain/LangGraph, tool use, memory, llm-gateway integration"
    languages: ["python"]
    frameworks: ["langchain", "langgraph", "llm-gateway"]
    tags: ["ai-agent", "llm", "tool-use", "agentic", "langchain"]
    suitable_for: ["ai-agent", "chatbot", "automation", "agentic-workflow"]
    patterns: ["agent-tool pattern", "LangGraph state machines", "memory management (conversation + vector)",
               "structured output parsing", "llm-gateway abstraction for vendor-agnostic LLM calls",
               "human-in-the-loop checkpoints", "retry/fallback chains"]
    includes:
      - "LangGraph workflow definitions with conditional edges and state persistence"
      - "Tool definitions with proper error handling and rate limiting"
      - "Vector store integration (abstract interface, pluggable backends)"
      - "llm-gateway integration for all LLM calls (mandatory per Forge non-negotiable principles)"
      - "Streaming support for real-time agent responses"
      - "Observability with LangSmith-compatible tracing"
    min_mode: "mvp"
    notes: "All LLM calls MUST go through llm-gateway, not direct LangChain LLM providers."

  - name: "temporal-ai-workflow"
    category: "ai-ml"
    description: "Temporal-orchestrated AI pipelines: durable, retryable, observable AI workflows"
    languages: ["python", "typescript"]
    frameworks: ["temporal", "llm-gateway"]
    tags: ["ai-workflow", "durable-execution", "orchestration", "temporal", "llm"]
    suitable_for: ["ai-pipeline", "workflow-automation", "long-running-ai-tasks", "data-processing"]
    patterns: ["Temporal workflows with activities for each AI step", "saga pattern for multi-step AI processes",
               "retry policies for transient LLM failures", "signal handling for human-in-the-loop",
               "child workflows for parallel AI tasks", "llm-gateway for all model calls",
               "workflow versioning for safe deployments"]
    includes:
      - "Temporal workflow and activity definitions"
      - "Worker setup with proper concurrency limits"
      - "Docker Compose with Temporal server, PostgreSQL, and Elasticsearch"
      - "llm-gateway integration in activities (not directly in workflows)"
      - "Observability: Temporal UI + custom metrics"
      - "Retry and timeout policies tuned for LLM call patterns"
    min_mode: "production-ready"
    notes: "Temporal activities wrap llm-gateway calls. Workflows orchestrate but never call LLMs directly."

  - name: "rag-pipeline"
    category: "ai-ml"
    description: "RAG system: document ingestion, embedding, vector storage, retrieval, generation via llm-gateway"
    languages: ["python"]
    frameworks: ["langchain", "llm-gateway"]
    tags: ["rag", "vector-db", "embedding", "search", "llm"]
    suitable_for: ["search", "knowledge-base", "qa-system", "document-ai"]
    patterns: ["chunking strategies (recursive, semantic)", "embedding abstraction (pluggable providers)",
               "vector store abstraction (pluggable: Pinecone, Qdrant, pgvector, ChromaDB)",
               "retrieval strategies (similarity, MMR, hybrid)", "reranking pipeline",
               "prompt templating with context injection", "evaluation framework (RAGAS-style)"]
    includes:
      - "Document loaders for PDF, DOCX, Markdown, web pages"
      - "Configurable chunking pipeline"
      - "Vector store with abstract interface + pluggable backends"
      - "Retrieval chain with llm-gateway for generation"
      - "Evaluation scripts for retrieval quality (precision, recall, faithfulness)"
    min_mode: "mvp"

  - name: "ml-model-serving"
    category: "ai-ml"
    description: "ML model serving API: FastAPI + model inference, batch prediction, A/B testing"
    languages: ["python"]
    frameworks: ["fastapi", "torch", "scikit-learn"]
    tags: ["ml-serving", "inference", "model-api", "batch-prediction"]
    suitable_for: ["ml-serving", "prediction-api", "model-deployment"]
    patterns: ["model registry abstraction", "pre/post processing pipelines",
               "async prediction endpoints", "batch prediction jobs",
               "model versioning and A/B routing", "health checks with model warmup"]
    min_mode: "production-ready"

  - name: "crewai-multi-agent"
    category: "ai-ml"
    description: "Multi-agent system with CrewAI: specialized agents with roles, tasks, and collaboration"
    languages: ["python"]
    frameworks: ["crewai", "llm-gateway"]
    tags: ["multi-agent", "crew", "ai-agent", "collaboration", "llm"]
    suitable_for: ["multi-agent-ai", "automation", "content-generation", "research-automation"]
    patterns: ["agent role definition", "task delegation", "sequential and parallel crew execution",
               "tool sharing between agents", "llm-gateway for all model calls",
               "output parsing and validation"]
    min_mode: "mvp"
    notes: "All LLM calls MUST go through llm-gateway, not direct CrewAI LLM configs."

  # ============================================================================
  # EVENT-DRIVEN — Message queues and async architectures
  # ============================================================================

  - name: "kafka-microservice"
    category: "event-driven"
    description: "Kafka consumer/producer microservice with schema registry, dead letter queue"
    languages: ["typescript", "python", "go"]
    frameworks: ["kafka", "avro"]
    tags: ["kafka", "event-driven", "streaming", "microservice"]
    suitable_for: ["event-driven", "microservice", "real-time"]
    patterns: ["consumer groups", "exactly-once semantics", "schema evolution", "DLQ handling",
               "idempotent processing", "outbox pattern"]
    min_mode: "production-ready"

  - name: "rabbitmq-worker"
    category: "event-driven"
    description: "RabbitMQ task worker with retries, dead letter exchange, priority queues"
    languages: ["python", "typescript"]
    frameworks: ["rabbitmq", "celery"]
    tags: ["rabbitmq", "worker", "task-queue", "async"]
    suitable_for: ["background-jobs", "task-processing", "async-work"]
    patterns: ["task routing", "retry with exponential backoff", "dead letter exchange",
               "priority queues", "result backend"]
    min_mode: "mvp"

  - name: "temporal-workflow"
    category: "event-driven"
    description: "Temporal durable workflow service: long-running processes, saga pattern, cron schedules"
    languages: ["typescript", "python", "go"]
    frameworks: ["temporal"]
    tags: ["temporal", "workflow", "durable-execution", "saga", "orchestration"]
    suitable_for: ["workflow-orchestration", "long-running-processes", "saga", "scheduling"]
    patterns: ["workflow-activity separation", "saga pattern with compensation",
               "signal and query handlers", "child workflows", "cron schedules",
               "workflow versioning", "testing framework"]
    includes:
      - "Docker Compose with Temporal server stack"
      - "Workflow and activity definitions"
      - "Worker with proper concurrency and timeout tuning"
      - "Integration test setup with Temporal test server"
    min_mode: "production-ready"

  # ============================================================================
  # PLATFORM — Tools, extensions, bots, and SaaS
  # ============================================================================

  - name: "saas-multi-tenant"
    category: "platform"
    description: "SaaS multi-tenant platform: auth, billing (Stripe), tenant isolation, admin dashboard"
    languages: ["typescript"]
    frameworks: ["nextjs", "prisma", "stripe"]
    tags: ["saas", "multi-tenant", "billing", "auth", "admin"]
    suitable_for: ["saas", "platform", "b2b"]
    patterns: ["tenant isolation (row-level vs schema-level)", "Stripe integration (subscriptions, webhooks)",
               "role-based access control", "tenant-scoped API middleware",
               "admin dashboard", "onboarding flow"]
    min_mode: "production-ready"

  - name: "chrome-extension"
    category: "platform"
    description: "Chrome extension (Manifest V3) with popup, content script, background service worker"
    languages: ["typescript"]
    frameworks: ["chrome-extension-mv3", "vite"]
    tags: ["chrome", "extension", "browser"]
    suitable_for: ["browser-extension", "chrome-extension", "productivity-tool"]
    patterns: ["message passing (content ↔ background ↔ popup)", "storage API", "content script injection",
               "declarativeNetRequest", "side panel"]
    min_mode: "mvp"

  - name: "vscode-extension"
    category: "platform"
    description: "VS Code extension with commands, webview panels, language server protocol"
    languages: ["typescript"]
    frameworks: ["vscode-api"]
    tags: ["vscode", "extension", "ide", "developer-tool"]
    suitable_for: ["developer-tool", "ide-extension", "code-analysis"]
    patterns: ["activation events", "command palette", "webview panels", "tree view providers",
               "LSP integration", "workspace configuration"]
    min_mode: "mvp"

  - name: "cli-tool"
    category: "platform"
    description: "CLI tool with subcommands, config files, interactive prompts, shell completions"
    languages: ["typescript", "python", "go"]
    frameworks: ["commander", "click", "cobra"]
    tags: ["cli", "terminal", "developer-tool"]
    suitable_for: ["cli-tool", "developer-tool", "automation"]
    patterns: ["subcommand routing", "config file loading (YAML/TOML)", "interactive prompts",
               "progress bars", "shell completion generation", "colored output"]
    min_mode: "mvp"

  - name: "slack-bot"
    category: "platform"
    description: "Slack bot with Bolt framework: slash commands, event handlers, interactive modals"
    languages: ["typescript", "python"]
    frameworks: ["slack-bolt"]
    tags: ["slack", "bot", "chat", "integration"]
    suitable_for: ["chatbot", "slack-integration", "team-tool"]
    patterns: ["event subscription", "slash commands", "interactive modals",
               "message shortcuts", "scheduled messages"]
    min_mode: "mvp"

  - name: "discord-bot"
    category: "platform"
    description: "Discord bot with slash commands, embeds, buttons, and voice support"
    languages: ["typescript", "python"]
    frameworks: ["discord.js", "discord.py"]
    tags: ["discord", "bot", "chat", "community"]
    suitable_for: ["chatbot", "discord-bot", "community-tool"]
    patterns: ["slash commands", "embed builders", "button/select interactions",
               "voice channel management", "permission checks"]
    min_mode: "mvp"

  # ============================================================================
  # DATA — Pipelines, ETL, and analytics
  # ============================================================================

  - name: "etl-pipeline"
    category: "data"
    description: "ETL/ELT data pipeline with Airflow or Dagster, dbt for transformations"
    languages: ["python", "sql"]
    frameworks: ["airflow", "dagster", "dbt"]
    tags: ["etl", "data-pipeline", "orchestration", "dbt"]
    suitable_for: ["data-engineering", "etl", "analytics"]
    patterns: ["DAG definition", "idempotent tasks", "data quality checks",
               "incremental loading", "dbt models and tests"]
    min_mode: "production-ready"

  - name: "streaming-pipeline"
    category: "data"
    description: "Real-time streaming pipeline with Flink or Spark Streaming, Kafka integration"
    languages: ["python", "java", "scala"]
    frameworks: ["flink", "spark", "kafka"]
    tags: ["streaming", "real-time", "data-pipeline"]
    suitable_for: ["real-time-analytics", "stream-processing", "event-processing"]
    patterns: ["windowing (tumbling, sliding, session)", "watermarks", "state management",
               "exactly-once semantics", "sink connectors"]
    min_mode: "production-ready"

  - name: "data-api"
    category: "data"
    description: "Data warehouse API: dbt models + API layer for serving analytics"
    languages: ["python", "sql"]
    frameworks: ["dbt", "fastapi"]
    tags: ["data-api", "analytics", "data-warehouse"]
    suitable_for: ["analytics-api", "data-serving", "business-intelligence"]
    patterns: ["dbt models as source of truth", "materialized views", "caching layer",
               "pagination for large datasets", "API key auth"]
    min_mode: "production-ready"

  # ============================================================================
  # INFRASTRUCTURE — IaC, deployment, and orchestration
  # ============================================================================

  - name: "terraform-aws"
    category: "infrastructure"
    description: "Terraform IaC for AWS: VPC, ECS/EKS, RDS, S3, CloudFront, IAM modules"
    languages: ["hcl"]
    frameworks: ["terraform", "aws"]
    tags: ["iac", "terraform", "aws", "cloud"]
    suitable_for: ["infrastructure", "aws-deployment", "cloud-setup"]
    patterns: ["module composition", "remote state (S3 + DynamoDB)", "workspace per environment",
               "variable validation", "output references"]
    min_mode: "production-ready"

  - name: "pulumi-multi-cloud"
    category: "infrastructure"
    description: "Pulumi IaC in TypeScript/Python: multi-cloud support, component resources"
    languages: ["typescript", "python"]
    frameworks: ["pulumi"]
    tags: ["iac", "pulumi", "multi-cloud"]
    suitable_for: ["infrastructure", "multi-cloud", "cloud-setup"]
    patterns: ["component resources", "stack references", "config + secrets",
               "policy as code", "dynamic providers"]
    min_mode: "production-ready"

  - name: "k8s-helm-charts"
    category: "infrastructure"
    description: "Kubernetes Helm charts: app deployment, service mesh, autoscaling, monitoring"
    languages: ["yaml"]
    frameworks: ["kubernetes", "helm"]
    tags: ["k8s", "helm", "container-orchestration", "deployment"]
    suitable_for: ["kubernetes-deployment", "container-orchestration"]
    patterns: ["Helm values hierarchy", "configmap/secret management", "HPA autoscaling",
               "liveness/readiness probes", "ingress configuration"]
    min_mode: "production-ready"

  - name: "monorepo-turborepo"
    category: "infrastructure"
    description: "Monorepo with Turborepo/Nx: shared packages, workspace protocols, CI optimization"
    languages: ["typescript"]
    frameworks: ["turborepo", "pnpm"]
    tags: ["monorepo", "workspace", "shared-packages"]
    suitable_for: ["monorepo", "multi-package", "shared-libraries"]
    patterns: ["workspace package structure", "shared tsconfig/eslint", "internal packages",
               "turbo pipeline caching", "changeset-based versioning"]
    min_mode: "mvp"
```

#### Template Selection & Usage Rules

##### Selection
- If `bootstrap_template` in config is a specific name (e.g., `"langchain-agent"`): use that template.
- If `bootstrap_template` is `"auto"`: the Architect analyzes project requirements and selects the best-matching template(s) from the manifest. The Architect may select MULTIPLE templates for complex projects (e.g., `react-spa` + `python-fastapi` + `terraform-aws` for a full-stack app with infra).
- If `bootstrap_template` is empty: skip templating entirely. Agents start from scratch.

##### Multi-Template Composition
For complex projects, the Architect can compose from multiple templates:
- Backend from `python-fastapi` + Frontend from `react-spa` + Infra from `terraform-aws` + AI features from `langchain-agent`
- Each template's scaffold is adapted and placed in the appropriate service/directory boundary.
- The Architect resolves conflicts between template patterns (e.g., different auth approaches in backend vs fullstack templates).

##### Usage Rules (CRITICAL — every agent must follow these)

1. **Templates are reference, not mandate.** If the project requirements conflict with a template's patterns, the project requirements win. Always.
2. **Adapt, don't copy blindly.** Agents should understand WHY the template uses each pattern (read `PATTERNS.md`), then decide if that pattern fits the actual project.
3. **Templates are starting points, not ceilings.** If the project needs something the template doesn't have, add it. If the template has something the project doesn't need, remove it.
4. **Vendor-agnostic principle overrides templates.** Even if a template uses a specific vendor (e.g., PostgreSQL), the agent must ensure the implementation uses abstract interfaces so the vendor can be swapped.
5. **LLM Gateway mandate overrides templates.** All AI/ML templates must route LLM calls through `llm-gateway`, even if the underlying framework (LangChain, CrewAI) has its own LLM configuration. The template should demonstrate how to wire the framework through `llm-gateway`.
6. **Template structure can be reorganized.** If the Architect's design calls for a different directory structure than the template provides, restructure. The template's structure is a suggestion.
7. **For brownfield projects**: Templates are used as PATTERN REFERENCE ONLY — not for scaffolding. Agents read the template's `PATTERNS.md` to understand best practices for the stack, but adapt their work to the existing codebase's structure and conventions.

#### AI/ML Template Special Notes

AI/ML templates deserve special attention because they involve the `llm-gateway` mandate:

- **All LLM calls through `llm-gateway`**: LangChain, CrewAI, and similar frameworks have their own LLM provider abstractions. These must NOT be used directly. Instead, the templates demonstrate how to create a custom LLM class/provider that wraps `llm-gateway` and plugs into the framework's interface. Example pattern for LangChain:

```python
# WRONG — direct LangChain LLM usage (violates vendor-agnostic principle)
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4")

# CORRECT — llm-gateway wrapper that implements LangChain's BaseLLM interface
from llm_gateway import LLMGateway
from langchain_core.language_models import BaseChatModel

class GatewayLLM(BaseChatModel):
    """LangChain-compatible LLM that routes through llm-gateway."""
    gateway: LLMGateway

    def _generate(self, messages, stop=None, **kwargs):
        response = self.gateway.chat(messages=messages, stop=stop, **kwargs)
        return self._convert_response(response)

llm = GatewayLLM(gateway=LLMGateway(mode="local-claude"))
```

- **Temporal + AI templates**: Temporal activities (not workflows) should call `llm-gateway`. Workflows orchestrate but never make direct LLM calls. This ensures Temporal's deterministic replay works correctly.

- **RAG templates**: The embedding provider and generation LLM must both be abstracted. The vector store must use a pluggable interface. The template demonstrates all three abstractions.

#### Adding Custom Templates

Users can add their own templates:

1. Create a new directory under the appropriate `templates/{category}/` path.
2. Include `README.md`, `PATTERNS.md`, `scaffold/`, and `template-config.yaml`.
3. Add the template entry to `_template-manifest.yaml`.
4. The template is immediately available for selection.

---

### 22. Fleet Session Management (Stop / Resume)

Agent teams may run for hours or days. The human needs the ability to gracefully stop the entire fleet (e.g., end of workday, cost concerns, need to review progress offline) and resume later exactly where things left off.

#### Three Ways to Stop the Fleet

The human can stop the fleet through any of these methods — all trigger the same graceful shutdown:

1. **Talk to the Team Leader** (preferred): Type "stop for today" or "let's wrap up" or "shut down" directly in the Team Leader's interactive session. The Team Leader orchestrates the shutdown internally.
2. **CLI command**: Run `./forge stop` from any terminal. This writes to `shared/.human/override.md` and also calls `scripts/stop.sh` directly.
3. **Override file**: Write to `shared/.human/override.md` with `type: abort` (useful for programmatic triggers or when tmux is inaccessible).

#### One Way to Resume

The human runs `./forge start` from their terminal. If a snapshot exists, it prompts to resume. The Team Leader's interactive session starts, it greets the human with a status summary, and the human can continue giving instructions naturally. See the Team Leader's "How Resume Works" section (Section 2) for the full UX flow.

#### Fleet State Snapshot

When `stop.sh` runs, it captures a comprehensive snapshot of the entire fleet state. This is the single source of truth for resumption.

##### Snapshot File: `shared/.snapshots/snapshot-{unix-timestamp}.json`

```json
{
  "snapshot_id": "snapshot-1705312200",
  "timestamp": "2025-01-15T18:30:00Z",
  "project": {
    "name": "my-project",
    "mode": "production-ready",
    "strategy": "co-pilot",
    "project_dir": "/home/user/projects/my-project",
    "config_path": "config/team-config.yaml"
  },
  "iteration": {
    "current": 3,
    "phase": "EXECUTE",
    "last_verified_tag": "iteration-2-verified",
    "summary": "Iteration 3 in progress. Backend auth complete, frontend login in progress."
  },
  "agents": [
    {
      "name": "team-leader",
      "type": "team-leader",
      "instance_id": "1",
      "status": "working",
      "current_task": "Coordinating iteration 3",
      "memory_file": "shared/.memory/team-leader-memory.md",
      "last_updated": "2025-01-15T18:29:00Z",
      "unprocessed_messages": 0,
      "file_locks_held": []
    },
    {
      "name": "backend-developer-1",
      "type": "backend-developer",
      "instance_id": "1",
      "status": "working",
      "current_task": "Implementing payment service endpoints",
      "memory_file": "shared/.memory/backend-developer-1-memory.md",
      "last_updated": "2025-01-15T18:28:00Z",
      "unprocessed_messages": 1,
      "file_locks_held": ["src/services/payment/handler.ts"]
    }
  ],
  "git": {
    "current_branch": "main",
    "active_branches": [
      "agent/backend-developer-1/TASK-012-payment-endpoints",
      "agent/frontend-developer/TASK-008-login-component"
    ],
    "uncommitted_changes": false,
    "last_tag": "iteration-2-verified"
  },
  "costs": {
    "total_development_cost_usd": 12.50,
    "cost_cap_usd": 50,
    "per_agent_costs": {
      "team-leader": 3.20,
      "backend-developer-1": 4.10,
      "frontend-developer": 2.80,
      "architect": 1.40,
      "critic": 1.00
    }
  },
  "pending_decisions": [],
  "human_overrides_pending": false
}
```

#### Graceful Shutdown Sequence (`stop.sh`)

```
Human runs `./forge stop` (or Team Leader calls scripts/stop.sh internally)
        │
        ▼
┌──────────────────────────┐
│ 1. PREPARE_SHUTDOWN      │  Broadcast to all agents: "Finalize working memory,
│    (60 second grace)     │  commit in-progress work, update status files."
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 2. CAPTURE SNAPSHOT      │  Read all status files, memory files, git state,
│                          │  cost data, inbox states → write snapshot JSON.
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 3. SHUTDOWN              │  Broadcast SHUTDOWN. Wait 30s for graceful exit.
│                          │  Force-kill stragglers. Release all file locks.
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 4. CLEANUP               │  Kill watchdog & log-aggregator. Destroy tmux session.
│                          │  Print resume command.
└──────────────────────────┘
```

Output example:
```
[Forge] Fleet stopped at 2025-01-15T18:30:00Z
[Forge] Snapshot saved: shared/.snapshots/snapshot-1705312200.json
[Forge] Agents stopped: 5 (team-leader, backend-developer-1, frontend-developer, architect, critic)
[Forge] Current iteration: 3 (phase: EXECUTE)
[Forge] Last verified: iteration-2-verified
[Forge] Total cost so far: $12.50 / $50.00 cap
[Forge]
[Forge] To resume: ./forge start
[Forge] To resume from specific snapshot: ./forge start --snapshot shared/.snapshots/snapshot-1705312200.json
```

#### Resume Sequence (`resume.sh`)

```
Human runs `./forge start` (auto-detects snapshot, prompts to resume)
        │
        ▼
┌──────────────────────────┐
│ 1. LOAD SNAPSHOT         │  Read latest (or specified) snapshot JSON.
│                          │  Validate project dir and shared/ state exist.
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 2. START INFRASTRUCTURE  │  Create tmux session. Start watchdog and
│                          │  log-aggregator daemons.
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 3. SPAWN TEAM LEADER     │  Launch Team Leader with --resume flag.
│                          │  Pass snapshot summary + working memory.
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 4. TEAM LEADER RESTORES  │  Team Leader reads its memory + snapshot.
│    FLEET                 │  Spawns each agent from snapshot with --resume.
│                          │  Sends "SESSION_RESUMED" to all agents.
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 5. AGENTS RESUME         │  Each agent reads its working memory,
│                          │  catches up on inbox, resumes "Next Steps".
│                          │  Reports status to Team Leader.
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 6. VERIFICATION          │  Team Leader verifies all agents are operational.
│                          │  Writes resume summary to iteration log.
│                          │  Continues from where the fleet left off.
└──────────────────────────┘
```

#### Agent Responsibilities During Shutdown

When any agent receives a `PREPARE_SHUTDOWN` message, it must:

1. **Immediately stop starting new subtasks.** Finish only the current atomic operation (e.g., finish writing a file, complete a git commit).
2. **Update working memory** with a complete snapshot of current state, including:
   - Exactly what was in progress and how far it got.
   - Any uncommitted changes (describe them in memory even if not committed).
   - What the immediate next steps would be upon resumption.
3. **Commit any safe-to-commit work** on their feature branch with a commit message: `[{agent-name}] chore: WIP checkpoint before session stop`.
4. **Release all file locks.**
5. **Update status file** to `suspended`.
6. **Write acknowledgment** to `shared/.queue/team-leader-inbox/` confirming readiness for shutdown.

#### Working Memory Resume Section

Each agent's working memory file (Section 13) must include a resume-specific section that is updated during `PREPARE_SHUTDOWN`:

```markdown
## Resume Context (Updated During Shutdown)
- **Shutdown timestamp**: {ISO 8601}
- **Work in progress**: {Exactly what was being done at time of shutdown}
- **Uncommitted changes**: {List of modified files not yet committed, or "None"}
- **WIP commit hash**: {Hash of the checkpoint commit, if any}
- **Immediate resume action**: {The very first thing this agent should do when it wakes up}
- **Estimated work remaining for current task**: {time estimate}
```

#### Snapshot Retention
- By default, keep the last 5 snapshots. Older ones are deleted by `stop.sh`.
- The human can configure retention in `team-config.yaml`:
  ```yaml
  session:
    snapshot_retention: 5  # Number of snapshots to keep
    auto_stop_after_hours: 0  # Auto-stop fleet after N hours (0 = disabled)
  ```

#### Auto-Stop (Optional)
If `auto_stop_after_hours` is configured, the watchdog triggers `stop.sh` automatically after the fleet has been running for the specified duration. This is a safety net for Auto Pilot mode to prevent runaway costs overnight.

#### Edge Cases
- **Resume after code changes outside Forge**: If the human made manual git commits while the fleet was stopped, the Team Leader detects this on resume (compares `git log` against snapshot's last known state) and notifies all agents of external changes before they resume work.
- **Resume with different mode/strategy**: The human can edit `team-config.yaml` while the fleet is stopped. On resume, `resume.sh` detects config changes, includes them in the Team Leader's resume context, and the Team Leader handles the mode/strategy switch as part of the resume process.
- **Partial resume**: The human can edit the snapshot file to exclude certain agents from resuming (set their entry to `"skip": true`). Useful if an agent was causing problems.
- **Stale snapshot**: If `shared/` state has been manually modified since the snapshot was taken, `resume.sh` warns the human and asks for confirmation before proceeding.

---

### 23. CLAUDE.md Hierarchy & Convention Inheritance

Claude Code natively uses `CLAUDE.md` files for project-specific conventions (coding standards, style preferences, architectural patterns, tool preferences). Forge must respect these when generating agent instruction files, since the human's existing conventions should carry forward — especially in brownfield projects where a `CLAUDE.md` already defines the codebase's rules.

#### CLAUDE.md Sources

| Source | Location | When It Exists |
|--------|----------|---------------|
| **Global** | `~/.claude/CLAUDE.md` | User's personal coding preferences across all projects (e.g., "always use TypeScript strict mode", "prefer functional patterns", "use 2-space indentation") |
| **Project** | `{project_root}/CLAUDE.md` | Project-specific conventions. For brownfield projects, this already exists and may contain team agreements, architecture decisions, and tool configurations. For greenfield, the Team Leader creates this as the first action. |

#### Configuration Options (`claude_md` in `team-config.yaml`)

| `source` Value | Behavior |
|----------------|----------|
| `"project"` | Use only the project's CLAUDE.md. Best for brownfield projects where the project has established conventions. Falls back to global if no project CLAUDE.md exists. |
| `"global"` | Use only the global `~/.claude/CLAUDE.md`. Best for users with strong personal preferences starting a new project. Falls back to none if no global exists. |
| `"both"` | Merge both sources. `priority` setting controls conflict resolution. **Recommended default** — the user gets their personal preferences AND project-specific rules. |
| `"none"` | Don't incorporate any external CLAUDE.md. Agents use only their own instruction files. Best for clean, reproducible setups or when sharing the Forge config across different users' machines. |

#### Merge Strategy (When `source: "both"`)

When both global and project CLAUDE.md files exist, they are merged by `init-project.sh`:

1. Parse both files into sections (using markdown headers as boundaries).
2. For sections that exist in both files (e.g., both have a "## Code Style" section), the file specified by `priority` wins. The other file's version is discarded for that section.
3. For sections that exist in only one file, they are included as-is.
4. The merged result is prepended to each generated agent instruction file as a `## Project-Wide Conventions (from CLAUDE.md)` section.

**Example merge with `priority: "project-first"`:**

```
Global CLAUDE.md:
  ## Code Style
  - Use 2-space indentation
  - Prefer arrow functions
  ## Testing
  - Always use vitest

Project CLAUDE.md:
  ## Code Style
  - Use 4-space indentation        ← WINS (project-first)
  - Use semicolons
  ## Deployment
  - Always deploy to us-east-1

Merged result:
  ## Code Style                     ← From project (overrides global)
  - Use 4-space indentation
  - Use semicolons
  ## Testing                        ← From global (not in project)
  - Always use vitest
  ## Deployment                     ← From project (not in global)
  - Always deploy to us-east-1
```

#### How CLAUDE.md Guidelines Reach Agents

The inheritance chain is:

```
Global CLAUDE.md  ─┐
                   ├──► init-project.sh ──► Merged Conventions ──► Prepended to each agent MD file
Project CLAUDE.md ─┘                                                       │
                                                                           ▼
                                                              spawn-agent.sh loads the
                                                              generated agent MD file
                                                              (conventions already baked in)
                                                                           │
                                                                           ▼
                                                              Agent's Claude Code session
                                                              also runs in project dir where
                                                              CLAUDE.md is natively loaded
```

This means agents get CLAUDE.md conventions **twice**: once baked into their instruction file (for explicit reference) and once via Claude Code's native CLAUDE.md handling (because they run `cd ${PROJECT_DIR}`). This is intentional redundancy — it ensures conventions are respected even if Claude Code's native handling has quirks.

#### Brownfield Project Special Handling

For `project.type: "existing"`, the project's CLAUDE.md is particularly important:

1. `init-project.sh` reads the existing project's CLAUDE.md FIRST, before generating any agent files.
2. Agent instructions are tailored to respect existing conventions — e.g., if the CLAUDE.md says "use Prisma ORM", the Backend Developer's generated instructions will reference Prisma specifically rather than leaving ORM choice open.
3. The Team Leader's instructions include a directive: "This is a brownfield project. The existing CLAUDE.md defines established conventions. Do NOT override them unless the human explicitly requests a convention change."
4. If the project has nested CLAUDE.md files (e.g., `frontend/CLAUDE.md`, `backend/CLAUDE.md`), `init-project.sh` detects these and includes them in the relevant agent's instructions only (frontend conventions → Frontend Engineer only, backend conventions → Backend Developer only).

#### Updating CLAUDE.md During Development

As the team builds the project, the Documentation Specialist (or Team Leader in lean mode) should update the project's CLAUDE.md with new conventions established during development. This ensures:
- Future sessions (after stop/resume) inherit the latest conventions.
- New agents spawned mid-session get up-to-date instructions.
- The CLAUDE.md remains a living document of the project's standards.

---

### 24. Secret Management

Agents need credentials (database passwords, API keys, cloud tokens, third-party service secrets) to build, test, and deploy the project. Without a structured protocol, agents will accidentally log secrets, commit `.env` files, include credentials in inter-agent messages, or expose them in working memory files.

#### Secret Storage

```
shared/.secrets/
├── .gitignore            # Contains "*" — nothing in this directory is ever committed
├── vault.env             # Encrypted secrets file (decrypted at runtime by agents)
├── vault.env.example     # Placeholder file showing required secret names without values
└── agent-access.yaml     # Which agents can access which secret categories
```

#### `shared/.secrets/agent-access.yaml`
```yaml
# Defines least-privilege access: each agent only gets the secrets it needs.
access:
  backend-developer:
    - database
    - api-keys
    - llm-gateway
  frontend-engineer:
    - api-keys-public    # Only public/client-side keys
  devops-specialist:
    - cloud
    - docker-registry
    - database
    - monitoring
  qa-engineer:
    - database-test      # Test database only, not production
    - api-keys
    - llm-gateway
  security-tester:
    - all                # Security tester needs full access to audit
```

#### Secret Access Protocol

1. **Setup**: During `./forge setup`, the human populates `shared/.secrets/vault.env` with actual values (guided by `vault.env.example`). The file is encrypted at rest using a passphrase or machine key.
2. **At runtime**: `start.sh` decrypts `vault.env` into environment variables for the tmux session. Each agent's `spawn-agent.sh` filters the environment to only include secrets the agent is authorized to access (per `agent-access.yaml`).
3. **In code**: Agents use environment variables (`process.env.DB_PASSWORD`, `os.environ["API_KEY"]`), NEVER hardcoded values. The project's code must always read secrets from environment variables or a secret manager abstraction.

#### Secret Safety Rules (embedded in every agent's instructions)

1. **NEVER log secrets** — not in structured logs, not in working memory, not in console output. If an agent needs to reference a secret in a log, use the secret name only: `"Connected to DB using DB_PASSWORD"`, never the value.
2. **NEVER include secrets in inter-agent messages** — if an agent needs to tell another agent about a credential, reference it by environment variable name.
3. **NEVER commit secrets** — `.env` files must be in `.gitignore`. Only `.env.example` with placeholders is committed.
4. **NEVER put secrets in working memory files** — these are plain text in `shared/.memory/` and could be read by any agent or persisted across sessions.
5. **Use `.env.example` pattern** — every project must have a `.env.example` file listing all required environment variables with placeholder values and comments explaining each one.
6. **Security Tester audits** — the Security Tester must verify no secrets are leaked in code, logs, configs, or git history as part of every security review.

---

### 25. Code Review Protocol Between Agents

When agents review each other's work (Architect reviewing Backend Developer's code for architectural compliance, Security Tester reviewing for vulnerabilities, QA Engineer reviewing test coverage), there must be a structured protocol. Without it, reviews become vague messages like "looks fine" or "needs improvement" with no actionable specifics.

#### Review Request Format

```markdown
File: shared/.queue/{reviewer}-inbox/msg-{timestamp}-{requester}.md
---
type: review-request
from: backend-developer-1
to: architect
priority: normal
review_scope: "architectural-compliance"  # architectural-compliance | security | performance | code-quality | test-coverage
---

## Review Request: User Authentication Service

### What to Review
- `src/services/auth/` — new authentication service implementation
- `src/middleware/auth-middleware.ts` — JWT validation middleware

### Context
Implements the auth flow from API spec `docs/api/auth.yaml` (artifact v2).
Uses repository pattern with abstract DB interface per architectural guidelines.

### Specific Concerns
- Is the token refresh flow architecturally sound?
- Does the middleware placement follow the middleware chain pattern?

### Branch
`agent/backend-developer-1/TASK-005-user-auth`
```

#### Review Findings Format

```markdown
File: shared/.queue/{requester}-inbox/msg-{timestamp}-{reviewer}.md
---
type: review-response
from: architect
to: backend-developer-1
priority: high
verdict: "changes-requested"  # approved | approved-with-notes | changes-requested | blocked
---

## Review: User Authentication Service

### Verdict: CHANGES REQUESTED

### Findings

#### BLOCKER — Architectural Violation
- **Location**: `src/services/auth/token-service.ts:45`
- **Issue**: Direct import of `jsonwebtoken` library without abstraction. Violates vendor-agnostic principle.
- **Required Fix**: Create `src/interfaces/token-provider.ts` with `ITokenProvider` interface. Implement `JWTTokenProvider` as the concrete implementation. Inject via constructor.

#### WARNING — Pattern Deviation
- **Location**: `src/middleware/auth-middleware.ts:20`
- **Issue**: Error handling catches all exceptions and returns 500. Should differentiate between auth errors (401) and server errors (500).
- **Suggested Fix**: Catch `TokenExpiredError` → 401, `TokenInvalidError` → 401, other → 500.

#### NOTE — Suggestion (Non-Blocking)
- **Location**: `src/services/auth/auth-service.ts:78`
- **Issue**: Password hashing rounds hardcoded to 10. Consider making configurable via environment variable.
- **Suggested Fix**: Add `BCRYPT_ROUNDS` env var with default of 12.

### Summary
2 issues must be fixed before approval. 1 non-blocking suggestion.
```

#### Review Severity Levels

| Level | Meaning | Action Required |
|-------|---------|----------------|
| **BLOCKER** | Violates a non-negotiable principle, breaks architecture, or introduces a security vulnerability | Must be fixed. Reviewer will re-review after fix. |
| **WARNING** | Deviates from best practices, could cause issues at scale, or misses an edge case | Should be fixed in the current iteration. Team Leader decides if it blocks progress. |
| **NOTE** | Suggestion for improvement, non-blocking, optional | Author decides whether to address. Log for future iteration. |

#### Review Resolution Protocol

1. **Author receives findings** → fixes all BLOCKERs, addresses WARNINGs (or justifies skip to Team Leader), optionally addresses NOTEs.
2. **Author requests re-review** for BLOCKERs only (reviewer doesn't need to re-review NOTEs).
3. **Dispute resolution**: If the author disagrees with a finding, they escalate to Team Leader with their reasoning. Team Leader mediates (may consult Architect for technical disputes).
4. **Maximum 2 review rounds** per deliverable. If not resolved after 2 rounds, Team Leader decides.

---

### 26. Parallel Work Streams

Strictly sequential iterations are inefficient for large projects. Independent features (e.g., auth and payment service) have no dependencies on each other and can be built simultaneously. The Team Leader must support parallel work streams that converge at integration points.

#### Work Stream Definition

A work stream is an independent track of work with its own mini-iteration cycle. Each stream has:
- A **stream ID** (e.g., `stream-auth`, `stream-payments`)
- **Assigned agents** (one or more developers, shared QA/Architect)
- **Feature scope** (which requirements/stories it covers)
- **Dependencies** on other streams (if any)
- **Integration points** (when streams must merge and be tested together)

#### Team Leader Orchestration

```
Iteration N
├── Stream A: User Auth          (Backend Dev 1 + Frontend Engineer)
│   ├── PLAN → EXECUTE → TEST (stream-level)
│   └── Produces: auth API, login UI, auth tests
├── Stream B: Payment Service    (Backend Dev 2)
│   ├── PLAN → EXECUTE → TEST (stream-level)
│   └── Produces: payment API, webhook handlers
├── Stream C: Admin Dashboard    (Frontend Engineer — after Stream A UI is done)
│   ├── Depends on: Stream A (auth)
│   └── PLAN → EXECUTE → TEST (stream-level)
│
├── INTEGRATION CHECKPOINT       (All streams converge)
│   ├── Integration testing (QA Engineer)
│   ├── Architecture review (Architect)
│   └── Cross-stream dependency verification
│
├── REVIEW (Architect, Security)
├── CRITIQUE (Critic scores full iteration)
└── DECISION (proceed / rework / rollback)
```

#### Rules

1. **Stream independence**: Streams MUST NOT modify the same files. If they need to, they share a dependency via the artifact registry and coordinate through Team Leader.
2. **Shared agents**: The Architect, QA Engineer, Critic, and Security Tester are shared across all streams. They review each stream independently but test integration collectively.
3. **Stream-level testing**: Each stream runs its own tests before the integration checkpoint. Only streams that pass their own tests proceed to integration.
4. **Integration checkpoint**: All streams merge to main, integration tests run, and the full system is verified. This is where cross-stream bugs surface.
5. **Dependency ordering**: If Stream C depends on Stream A, the Team Leader schedules them accordingly — Stream C starts after Stream A's artifacts are ready (or starts with mock data and integrates later).
6. **File locks across streams**: Each stream's developers must respect the global file locking protocol. The lock system prevents cross-stream file conflicts.

#### When to Use Parallel Streams

- **MVP mode**: Usually sequential is fine (small scope, few agents).
- **Production Ready**: Parallel streams for independent service boundaries.
- **No Compromise**: Aggressive parallelization with multiple backend developer instances across streams.

The Team Leader decides the stream topology during the PLAN phase based on requirement dependencies and available agents.

---

### 27. Integration Testing Protocol

When multiple agents build separate components (Backend Developer builds the API, Frontend Engineer builds the UI), there must be a structured protocol for verifying they work together. Without this, both sides report "done" but the system fails when connected.

#### Contract Testing (Pre-Integration)

Before components are integrated, they must pass contract tests:

1. **API Contract**: The Architect produces API specs (OpenAPI/Swagger) as artifacts. Both the Backend Developer and Frontend Engineer build against this spec.
2. **Contract verification**: Before integration checkpoint:
   - Backend Developer runs a contract verification tool (e.g., Pact provider verification, OpenAPI spec validation) that confirms the API conforms to the spec.
   - Frontend Engineer runs contract tests that confirm the frontend's API client conforms to the spec.
   - If either side deviates from the spec, it's caught before integration — not after.
3. **Schema validation**: Database schema changes must be verified against the ORM models (Backend Developer) and API response shapes (Frontend Engineer).

#### Integration Checkpoint Protocol

The integration checkpoint occurs after all parallel streams pass their stream-level tests:

```
Stream-level tests pass
        │
        ▼
┌──────────────────────────────┐
│ 1. MERGE TO INTEGRATION      │  All streams merge their branches to an
│    BRANCH                    │  `integration/{iteration-N}` branch.
│                              │  Team Leader resolves any merge conflicts.
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 2. SMOKE TEST                │  QA Engineer runs the full application.
│                              │  Can it start? Do core flows work end-to-end?
│                              │  If not → back to streams for fixes.
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 3. INTEGRATION TESTS         │  QA Engineer runs cross-component tests:
│                              │  API ↔ Frontend, Service ↔ Service,
│                              │  Database ↔ API, Auth ↔ Everything.
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 4. CONTRACT VALIDATION       │  Verify all API contracts hold.
│                              │  Verify all event schemas are compatible.
│                              │  Verify DB migrations are consistent.
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ 5. MERGE TO MAIN             │  If all pass → Team Leader merges integration
│                              │  branch to main. If not → route failures
│                              │  back to the responsible stream's agents.
└──────────────────────────────┘
```

#### API Mismatch Detection

The most common integration failure is API mismatches. To detect these early:

- **Architect maintains the API spec as a versioned artifact.** When it changes, all dependent agents are notified via the artifact registry.
- **Backend Developer must validate their implementation against the spec** (automated OpenAPI validation in CI or as part of their test suite).
- **Frontend Engineer must build against the spec**, not against assumptions. Their API client should be generated or validated from the spec.
- **QA Engineer writes specific API mismatch tests**: call each endpoint from the frontend's perspective and verify the response shapes match frontend expectations.

---

### 28. Environment Configuration Strategy

Production-grade projects must work across multiple environments (local dev, CI, staging, production). Without a clear strategy, agents build something that works locally but fails in CI or production.

#### Environment Matrix

The DevOps Specialist produces an environment matrix as an artifact during the first iteration:

```markdown
# Environment Matrix

| Aspect | Local Dev | CI | Staging | Production |
|--------|-----------|-----|---------|------------|
| Database | Docker PostgreSQL | Docker PostgreSQL | Cloud RDS | Cloud RDS (HA) |
| Cache | Docker Redis | Docker Redis | Cloud ElastiCache | Cloud ElastiCache (cluster) |
| LLM Calls | llm-gateway local-claude | llm-gateway mock | llm-gateway staging | llm-gateway production |
| Auth | Local JWT | Local JWT | Auth0 sandbox | Auth0 production |
| Storage | Local filesystem | Docker volume | Cloud S3 (dev bucket) | Cloud S3 (prod bucket) |
| Secrets | .env file | CI secrets | Secret Manager | Secret Manager |
| URL | localhost:3000 | N/A | staging.app.com | app.com |
| Debug | Enabled | Enabled | Enabled | Disabled |
| Log Level | debug | debug | info | warn |
```

#### Rules for All Agents

1. **Environment variables for all config**: No hardcoded URLs, ports, credentials, or feature flags. Everything must come from environment variables or a config file that varies per environment.
2. **Environment detection**: The codebase must detect which environment it's in (via `NODE_ENV`, `APP_ENV`, or equivalent) and adjust behavior accordingly.
3. **Docker Compose for local**: Local development must be a single `docker-compose up` that spins up all dependencies. No requiring agents or developers to install PostgreSQL, Redis, etc. locally.
4. **CI must be self-contained**: CI pipelines must not depend on external services. Use Docker services, mocks, and `llm-gateway` in mock mode.
5. **Infrastructure-as-code for staging/prod**: In Production Ready and No Compromise modes, staging and production infrastructure must be defined in Terraform/Pulumi (managed by DevOps Specialist).
6. **Config validation**: At application startup, validate that all required environment variables are set. Fail fast with a clear error message listing missing variables.

#### Mode-Specific Requirements

- **MVP**: Local dev and basic CI only. No staging/production.
- **Production Ready**: Full environment matrix. CI pipeline covers all environments. Staging deployment as part of CI.
- **No Compromise**: All of the above plus production deployment scripts, environment parity verification, and infrastructure drift detection.

---

### 29. Agent Confidence Signaling

Agents should communicate their certainty about their work so the Team Leader can make better orchestration decisions. Without confidence signals, the Team Leader treats all output equally — a backend developer's confident implementation of a well-understood CRUD endpoint gets the same review treatment as a risky, novel algorithm they're unsure about.

#### Confidence Levels

| Level | Meaning | Team Leader Action |
|-------|---------|-------------------|
| **HIGH** | Agent is confident in the approach, has done similar work before, tests pass, patterns are well-established | Standard review. Proceed normally. |
| **MEDIUM** | Agent believes the approach is correct but has some uncertainty — unfamiliar pattern, edge cases not fully explored, or alternative approaches exist | Team Leader requests Architect or relevant specialist review before proceeding. |
| **LOW** | Agent is unsure about the approach — first time with this technology, conflicting best practices, or the requirements are ambiguous | Team Leader MUST route for review. In Co-Pilot/Micro-Manage: escalate to human. In Auto Pilot: request Architect + Critic review. |

#### Where Confidence Appears

1. **Deliverable messages**: Every deliverable or status-update message to the Team Leader includes a `confidence: high | medium | low` field in the header.
2. **Working memory**: The agent's "Important Context" section includes confidence notes about the current approach.
3. **Decision log**: When agents make technical decisions, the confidence level is recorded alongside the rationale.

#### Message Format Addition

```markdown
---
from: backend-developer-1
to: team-leader
type: deliverable
confidence: medium
confidence_note: "Payment webhook handling works for Stripe but I'm unsure about idempotency guarantees under concurrent webhook delivery."
---
```

#### Team Leader Routing Rules

- `confidence: high` from any agent → standard iteration flow.
- `confidence: medium` from a developer → route to Architect for pattern review.
- `confidence: medium` from Architect → route to Research & Strategy Lead for validation.
- `confidence: low` from any agent → mandatory review by at least 2 other agents before proceeding. Log in decision log why the low-confidence approach was chosen.
- Multiple `confidence: low` signals in the same iteration → Team Leader considers pausing to reassess the strategy with the human (in any mode).

---

### 30. Post-Project Retrospective

After the project is complete (all iterations pass, Critic approves, human accepts), the Team Leader generates a comprehensive retrospective. This is valuable both for the human (understanding what was built and how) and for improving Forge itself.

#### Retrospective Output: `{project-root}/RETROSPECTIVE.md`

The Team Leader produces this document by synthesizing data from decision logs, iteration summaries, Critic reports, cost tracker, and agent working memories.

```markdown
# Project Retrospective: {project-name}

## Executive Summary
{2-3 paragraph overview: what was built, how long it took, total cost, quality verdict}

## What Was Built
### Feature Inventory
{Table: feature name | status | implementing agent | iterations to complete | tests}

### Architecture Summary
{High-level architecture with key design decisions and their rationale}

### Technology Choices
{Table: category | choice | rationale | alternatives considered}

## Project Timeline
### Iteration History
{Table: iteration # | duration | features completed | Critic score | rework needed}

### Blockers & Resolutions
{Table: blocker | duration blocked | resolution | impact}

### Agent Limit Events
{Table: agent | limit events | total downtime | recovery method}

## Quality Report
### Final Critic Score: {X}%
{Breakdown of acceptance criteria: passed, failed, waived}

### Test Coverage
{Coverage metrics: unit, integration, E2E}

### Security Findings
{Summary of security review: findings, remediation status}

### Performance Benchmarks
{If Performance Engineer was active: load test results, key metrics}

## Cost Analysis
### Development Costs
{Table: agent | estimated tokens | estimated cost USD | % of total}
{Total development cost}

### Projected Runtime Costs
{Infrastructure cost estimates at projected traffic levels}

## Lessons Learned
### What Went Well
{Patterns, decisions, or approaches that worked effectively}

### What Caused Rework
{Decisions or approaches that needed iteration, with analysis of why}

### Recommendations
{Suggestions for the human: what to monitor, what to improve, what to address next}

## How to Continue
{If the project is ongoing: suggested next features, technical debt to address, scaling considerations}
```

#### Retrospective Triggers

- **Automatic**: Generated when the Critic approves the final iteration in any mode.
- **On request**: Human can ask the Team Leader "generate a retrospective" at any point to get a progress snapshot.
- **On abort**: If the project is abandoned, the Team Leader generates a partial retrospective documenting what was done, what remains, and why it was stopped.

---

### 31. Memory Compaction for Long Projects

For projects that run across multiple days and many iterations, agent working memories accumulate stale information. After 5 iterations, the Backend Developer doesn't need detailed memory of iteration 1's design discussion — but it still consumes context window space. Without compaction, agents gradually lose the ability to absorb new information because their context is full of old details.

#### Compaction Strategy

After each successful iteration (tagged `iteration-{N}-verified`), the Team Leader triggers a memory compaction cycle for all agents.

##### What Gets Compacted

| Content Type | Compaction Rule |
|-------------|----------------|
| Completed tasks from 2+ iterations ago | Collapse to one-line summary: `"{task}: completed in iteration {N}, produced {artifact}"` |
| Decisions from 2+ iterations ago | Keep only if still affecting current work. Otherwise: `"Decision {X}: {one-line summary}. See shared/.decisions/{file}."` |
| Dependencies that were resolved | Remove entirely |
| Bug reports that were fixed | Remove. The test that verifies the fix is the record. |
| Context/discoveries from early iterations | Summarize to 1-2 sentences. Detailed context stays in `shared/.decisions/` and `shared/.iterations/` files (on disk, not in memory). |
| Current iteration details | Keep in full |
| Previous iteration details | Keep in moderate detail (may be needed for rework) |

##### What NEVER Gets Compacted

- Current assignment and next steps
- Active dependencies (still waiting on something)
- Decisions that constrain current work (even if made 5 iterations ago)
- File lock state
- Resume context / limit save context
- Non-negotiable principles and project-wide conventions

#### Compaction Process

```
Iteration N verified
        │
        ▼
Team Leader sends COMPACT_MEMORY to all agents
        │
        ▼
Each agent:
  1. Reads current working memory
  2. Identifies content older than 2 iterations
  3. Applies compaction rules
  4. Ensures compacted memory is still self-sufficient for resume
  5. Writes compacted memory back to shared/.memory/{agent}-memory.md
  6. Reports new memory size to Team Leader
        │
        ▼
Team Leader verifies all agents compacted successfully
```

#### Memory Size Monitoring

The Team Leader and watchdog monitor working memory file sizes:

| Size | Status | Action |
|------|--------|--------|
| < 5 KB | Healthy | None |
| 5-15 KB | Normal | None |
| 15-30 KB | Growing | Team Leader suggests compaction if not recently done |
| > 30 KB | Large | Team Leader triggers mandatory compaction. If still >30KB after compaction, the agent may need to offload detail to `shared/.decisions/` reference files. |

#### Reference Files Pattern

When compaction removes detailed content from working memory, the detail is preserved on disk in reference files:

```markdown
## Key Decisions Made
- AUTH-001: "Use JWT with rotating refresh tokens" (iteration 1). Details: shared/.decisions/AUTH-001-jwt-refresh.md
- PAY-003: "Stripe webhooks with idempotency keys" (iteration 2). Details: shared/.decisions/PAY-003-stripe-webhooks.md

## Completed Work (Summary)
- Iteration 1: User auth service (API + DB + tests). Artifacts: src/services/auth/
- Iteration 2: Payment service (Stripe integration + webhooks). Artifacts: src/services/payment/
- Iteration 3 (current): Admin dashboard. In progress.
```

The agent can read reference files on disk when it needs the full context for a specific decision, without keeping it all in memory.

---

### 32. Quality Checklist (Verify Before Done)

- [ ] Every agent MD file has all 12 required sections (Identity, Responsibilities, Skills, Inputs, Outputs, Communication, Collaboration, Quality, Iteration, Mode-Specific, Memory, Artifact Registration).
- [ ] `_base-agent.md` is referenced by every agent file and includes all shared protocols (communication, memory, logging, locking, artifacts, human override).
- [ ] `team-leader.md` covers startup, orchestration, all three modes, all three strategies, mode switching, cost tracking, agent lifecycle, health monitoring, rollback protocol, working memory management, **and natural language command handling**.
- [ ] `team-leader.md` includes explicit handling for all natural language command categories: session control (stop/pause/status/cost), mode/strategy changes, agent management (spawn/kill/status), work direction (reprioritize/correct/sync), and feedback/review.
- [ ] Team Leader runs in an **interactive** tmux window where the human can type directly — not a headless background process.
- [ ] `critic.md` includes scored acceptance criteria generation across THREE categories (Functional, Technical, User-Quality), per-category pass rate enforcement, and mode-specific thresholds (70%/90%/100% applied to each category independently).
- [ ] `critic.md` includes user-facing quality evaluation: result quality, data freshness, actionable outputs, edge case UX, realistic scenario testing, and example quality table showing PASS vs FAIL for common feature types.
- [ ] `team-config.yaml` template has all fields with clear comments and the example file is fully filled in.
- [ ] `project-requirements.md` template exists with clear instructions.
- [ ] All scripts are executable (`chmod +x`), have proper error handling, include usage help (`--help`), and handle edge cases.
- [ ] `spawn-agent.sh` correctly creates tmux windows, passes the right context to Claude Code using the invocation spec (Section 12), and supports `--resume` flag.
- [ ] `watchdog.sh` detects dead/stale agents and notifies Team Leader.
- [ ] `log-aggregator.sh` produces combined chronological logs and handles rotation.
- [ ] Inter-agent communication protocol uses atomic writes (`mv` from temp) and per-message files (not append to single file).
- [ ] File locking system is documented and consistently referenced in developer agent files.
- [ ] Artifact registry format is defined and all producer/consumer agents reference it.
- [ ] Git workflow is fully specified: branch naming, commit format, merge protocol, conflict resolution, iteration tagging.
- [ ] Iteration lifecycle (Plan → Execute → Test → Integrate → Review → Critique → Decision) is documented and referenced by all agents.
- [ ] Working memory format is defined and every agent file includes memory management instructions.
- [ ] Human override channel is documented and monitored in all modes (including Auto Pilot).
- [ ] Structured logging format is defined and every agent file references it.
- [ ] `templates/` directory is organized into categories (backend, frontend, fullstack, ai-ml, event-driven, platform, data, infrastructure) with at least 2 templates per category that has entries in the manifest.
- [ ] Every template has `README.md`, `PATTERNS.md` (explaining WHY patterns were chosen), `scaffold/`, and `template-config.yaml`.
- [ ] AI/ML templates (langchain-agent, temporal-ai-workflow, rag-pipeline, crewai-multi-agent) all route LLM calls through `llm-gateway`, not through the framework's native LLM providers.
- [ ] `_template-manifest.yaml` has rich metadata for all templates: category, languages, frameworks, tags, suitable_for, patterns, min_mode.
- [ ] Template usage rules are documented: templates are reference (not mandate), adapt don't copy, vendor-agnostic principle overrides templates, brownfield projects use templates as pattern reference only.
- [ ] Multi-template composition works: Architect can select and combine templates from different categories for complex projects.
- [ ] Non-negotiable principles (all 9) appear in every relevant agent file.
- [ ] README.md is comprehensive enough for a first-time user to set up and run Forge.
- [ ] All file paths and cross-references between documents are correct.
- [ ] The `shared/` directory structure is created by scripts, not committed to git (add to `.gitignore`).
- [ ] `.gitignore` includes `shared/`, any generated project-specific agent files, and temporary files.
- [ ] The `llm-gateway` plugin integration is documented with setup instructions.
- [ ] Cost tracking mechanism is documented and functional.
- [ ] The framework handles both new and existing project types.
- [ ] Session recovery has been tested: kill an agent's tmux window, verify watchdog detects it, verify Team Leader restarts it with memory, verify the agent resumes correctly.
- [ ] `stop.sh` gracefully shuts down all agents, captures a fleet state snapshot, and prints the resume command.
- [ ] `resume.sh` restores a fleet from a snapshot: spawns Team Leader with --resume, Team Leader restores all agents, all agents resume from working memory.
- [ ] Fleet stop/resume has been tested end-to-end: start fleet, let agents work, run `stop.sh`, verify snapshot, run `resume.sh`, verify all agents resume correctly and continue from where they left off.
- [ ] Every agent file includes instructions for handling `PREPARE_SHUTDOWN` messages (finalize memory, checkpoint commit, release locks, update status to `suspended`).
- [ ] Working memory format includes the "Resume Context" section that gets populated during shutdown.
- [ ] Snapshot retention and `auto_stop_after_hours` config options are documented and functional.
- [ ] Edge cases are handled: manual code changes between sessions, config changes between sessions, partial resume, stale snapshots.
- [ ] `forge` CLI script exists at repo root and supports all commands: `setup`, `init`, `start`, `stop`, `status`, `cost`, `tell`, `attach`, `logs`.
- [ ] `./forge init` runs an interactive wizard that generates `config/team-config.yaml` and `config/project-requirements.md` from user prompts.
- [ ] `./forge start` auto-detects existing snapshots and prompts the human to resume, start fresh, or exit.
- [ ] `./forge tell "<message>"` writes to `shared/.human/override.md` so the human can send commands without attaching to tmux.
- [ ] The human can type "stop for today" (or similar) directly in the Team Leader's interactive session and the Team Leader calls `scripts/stop.sh` internally, orchestrating the shutdown and being the last agent to exit.
- [ ] On resume, the Team Leader greets the human with a status summary of where things left off and asks if they want to continue or adjust anything.
- [ ] **Team Profiles**: Both lean (8 agents) and full (12 agents) team rosters are defined. `team_profile: "auto"` correctly selects lean for MVP and full for production-ready+.
- [ ] **Merged agents**: `research-strategist.md`, `frontend-engineer.md`, and `qa-engineer.md` each combine their constituent roles' responsibilities into coherent single-agent instruction files.
- [ ] **Standalone agents**: `researcher.md`, `strategist.md`, `frontend-designer.md`, and `frontend-developer.md` exist as standalone files for full team mode.
- [ ] **QA Engineer is always merged**: No separate `manual-tester.md` or `automation-tester.md` — the QA Engineer handles both in all profiles.
- [ ] **Performance Engineer**: `performance-engineer.md` exists with load testing, profiling, query optimization, and capacity planning responsibilities.
- [ ] `init-project.sh` correctly resolves team profile and only generates agent files for agents in the active roster.
- [ ] **CLAUDE.md config**: `claude_md` section in `team-config.yaml` supports all four source options (`project`, `global`, `both`, `none`) and priority settings.
- [ ] `init-project.sh` correctly resolves CLAUDE.md: loads global and/or project sources per config, merges with correct priority, prepends to generated agent files.
- [ ] For brownfield projects: existing project CLAUDE.md is detected and incorporated. Nested CLAUDE.md files (e.g., `frontend/CLAUDE.md`) are routed to relevant agents only.
- [ ] Generated agent files are stored in `{project_root}/.forge/agents/` and `spawn-agent.sh` uses these over templates when available.
- [ ] `claude_md.source: "none"` produces agent files with no external convention injection (clean, reproducible setup).
- [ ] **Usage limit protocol**: Every agent file includes instructions for detecting limit signals (429 errors, CLI warnings, latency spikes) and executing the `LIMIT_SAVE` protocol immediately.
- [ ] `LIMIT_SAVE` sequence is documented: stop work → save memory (with Limit Save Context section) → checkpoint commit → update status to `rate-limited` → release locks → notify Team Leader. Takes <30 seconds.
- [ ] Working memory format includes the "Limit Save Context" section with: trigger, in-flight operation, files being modified, checkpoint commit hash, uncommitted changes, and step-by-step resume instructions.
- [ ] Watchdog detects rate-limited agents (via status files and log patterns) and monitors for limit refresh to trigger auto-resume.
- [ ] Team Leader handles fleet-wide limit risk: can proactively trigger `LIMIT_SAVE` on agents running for extended periods, reduce active agent count, or execute full fleet stop when `fleet_limit_threshold` is reached.
- [ ] `usage_limits` config section exists in `team-config.yaml` with `proactive_save_interval_hours`, `estimated_refresh_window_hours`, `auto_resume_after_limit`, `fleet_limit_threshold`, and `scheduled_resume_time`.
- [ ] Memory update rule of "at least every 10 minutes" is emphasized in all agent files as the safety net for abrupt session kills.
- [ ] **Secret Management**: `shared/.secrets/` directory structure is defined. `agent-access.yaml` enforces least-privilege access. All 6 secret safety rules are embedded in every agent's instructions. `.env.example` pattern is mandatory.
- [ ] **Code Review Protocol**: Review request and review findings formats are defined with severity levels (BLOCKER/WARNING/NOTE). Dispute resolution protocol exists. Maximum 2 review rounds before Team Leader decides.
- [ ] **Parallel Work Streams**: Team Leader can define and orchestrate parallel streams with independent mini-iteration cycles. Integration checkpoint protocol is defined. File locks prevent cross-stream conflicts.
- [ ] **Integration Testing Protocol**: Contract testing (pre-integration) is defined. Integration checkpoint sequence (merge → smoke test → integration tests → contract validation → merge to main) is documented. API mismatch detection strategy exists.
- [ ] **Environment Configuration Strategy**: Environment matrix template is defined (local/CI/staging/prod). All agents follow the rule: no hardcoded environment-specific values. Docker Compose for local dev is mandatory. Mode-specific environment requirements are documented.
- [ ] **Agent Confidence Signaling**: Every deliverable message includes `confidence: high | medium | low` field. Team Leader routing rules exist for each confidence level. Low-confidence outputs trigger mandatory multi-agent review.
- [ ] **Post-Project Retrospective**: Team Leader generates `RETROSPECTIVE.md` on project completion, covering: feature inventory, timeline, cost analysis, quality report, lessons learned. Also generated on abort (partial) and on-demand.
- [ ] **Memory Compaction**: Compaction rules are defined (what gets compressed, what never gets compressed). Team Leader triggers compaction after each verified iteration. Memory size monitoring thresholds are defined. Reference files pattern preserves detail on disk while keeping memory lean.
