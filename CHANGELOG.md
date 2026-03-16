# Changelog

All notable changes to the Forge project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Features

- **Context rot reduction** — Hierarchical checkpoints (`{type}/{name}.json`),
  event inbox for concurrent agent writes, and token counting via llm-gateway.
  Agents get exact context budget reporting at generation time via
  `.forge/token-report.json`.
- **Compaction configuration** — New `compaction` config section with
  `compaction_threshold_tokens`, `enable_context_anchors`, and
  `anchor_interval_minutes` for controlling context compaction behavior.
- **Token counting & reporting** — `forge generate` now produces a token report
  showing per-agent context budgets at startup (agent file, CLAUDE.md, system
  overhead). Uses llm-gateway for exact provider-aware token counts.
- **Event inbox** — Atomic file-based event system (`.forge/events/`) for
  concurrent agent registration, lifecycle tracking, and compaction signaling.
  Events are archived to `.forge/events-archive.jsonl` on materialization.
- **Session materialization** — `forge stop` and `forge resume` now materialize
  session state from base session + pending events, enabling crash recovery.
- **Checkpoint/resume system** — `forge start`, `forge stop`, and `forge resume`
  commands for multi-agent session management. Agents checkpoint state to
  `.forge/checkpoints/{type}/{name}.json` with full context for resume.
- **Eval framework** — `forge eval` runs 350+ deterministic and LLM-judged
  quality assertions against generated files. Supports `--no-llm` for free
  deterministic-only checks and `--optimize-descriptions` for skill triggers.
- **Hook scripts** — Auto-generated `.forge/hooks/*.sh` for checkpoint
  enforcement, activity tracking, compaction detection, and stop signals.
  Identity resolution via `.forge/scripts/resolve_identity.py`.
- **Compaction e2e test scenarios** — 12 new end-to-end scenarios (12–23)
  covering cooperative compaction, multi-level hierarchy, simultaneous agents,
  mid-task compaction, repeated cycles, and edge cases.
- **Per-file-type scoring profiles** — Refinement scoring now uses file-type
  aware criteria weights for more accurate quality assessment.
- **Git credentials management** — Optional `git.ssh_key_path` config enables
  SSH-based git authentication, avoiding macOS Keychain prompts. Generated files
  include Phase 0 setup (core.sshCommand), agent auth guidance, and GH_TOKEN
  in .env.example for GitHub CLI operations.

## [1.0.0] — 2026-03-08

### Features

- **Config-driven CLI** — Single command `forge --config PATH` reads a
  `forge-config.yaml` and generates all agent instruction files
- **Seven CLI commands** — `forge init`, `forge generate`, `forge refine`,
  `forge eval`, `forge start`, `forge stop`, `forge resume` forming a complete
  project lifecycle
- **Three modes** — `mvp`, `production-ready`, `no-compromise` with escalating
  quality standards
- **Three strategies** — `auto-pilot`, `co-pilot`, `micro-manage` controlling
  agent autonomy level
- **Team profiles** — `lean` (8 agents), `full` (12 agents), `auto` (mode-based),
  `custom` (explicit agent list)
- **Agent file generation** — Role-specific `.md` instruction files for each agent
  in `.claude/agents/`
- **CLAUDE.md generation** — Team Leader context document with project details,
  tech stack, and coordination rules
- **team-init-plan.md** — Bootstrap document for first Claude Code session
- **Skill generation** — Reusable skills in `.claude/skills/` (PR creation, release,
  arch review, smoke test, screenshot review, iteration review, team status,
  checkpoint)
- **Session management (`forge start/stop/resume`)** — Launch Claude sessions with
  team init, gracefully stop with agent checkpointing, and resume from checkpoints
  with instruction file change detection. Supports tmux for split-pane monitoring.
- **Eval framework (`forge eval`)** — 350+ quality assertions (deterministic +
  LLM-judged) with applicability predicates, benchmark comparison, and skill
  description optimization
- **Atlassian integration** — Optional Jira/Confluence integration with scrum-master
  agent, sprint boards, and ceremony automation
- **Agent naming** — Optional creative/functional/codename naming for agents
- **LLM Gateway integration** — Optional `llm-gateway` mandate in generated files
  for vendor-agnostic LLM access
- **Non-negotiables** — Absolute requirements injected into all generated files with
  role-appropriate framing (enforcement/evaluation/compliance)
- **LLM-powered refinement** — Optional post-generation step that scores and
  iteratively improves each file against weighted quality criteria (completeness,
  config fidelity, specificity, clarity, consistency). All files refined in parallel.
  Enable with `--refine` or `refinement.enabled: true` in config.
- **Validate-only mode** — `--validate-only` flag prints config summary without
  generating files
- **Sub-agent spawning** — Optional `spawn-agent.md` skill when
  `allow_sub_agent_spawning` is enabled
- **Strategy-enforced permissions** — `auto-pilot` and `co-pilot` generate
  `.claude/settings.json` allowing all tools (Bash, Edit, Write, Read, WebFetch,
  WebSearch, Agent, MCP). Both grant full tool autonomy — the difference is
  behavioral: `co-pilot` agents ask human only for architecture/scope/domain
  decisions. `micro-manage` skips settings generation, relying on Claude Code
  defaults that prompt for every tool.
- **MCP configuration** — Generated `.claude/mcp.json` with Playwright and optional
  Atlassian MCP servers
- **Custom agent instructions** — Per-agent instruction overrides via
  `agents.custom_instructions`
- **Example configuration** — Comprehensive annotated `examples/forge-config.yaml`
  documenting every option with inline comments
- **Interactive setup (`forge init`)** — 8-step interactive wizard that walks users
  through every configuration option, shows a summary for confirmation, saves the
  config file, and optionally runs generation immediately. No YAML editing required.
