# Changelog

All notable changes to the Forge project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-03-08

### Features

- **Config-driven CLI** — Single command `forge --config PATH` reads a
  `forge-config.yaml` and generates all agent instruction files
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
  arch review, smoke test, screenshot review, iteration review, team status)
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
