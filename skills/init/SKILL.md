---
name: init
description: "Run the interactive project configuration wizard"
argument-hint: "[--project-dir <path>]"
---

# /forge:init — Configure Project

Run the Forge interactive wizard to configure your Claude Code agent team.

The wizard walks you through:
1. **Project basics** — description, requirements, type (new/existing)
2. **Mode & Strategy** — MVP/Production/No-Compromise, Auto-Pilot/Co-Pilot/Micro-Manage
3. **Budget** — development cost cap
4. **Tech stack** — preferred languages, frameworks, databases
5. **Team composition** — auto/lean/full/custom agent profiles
6. **Sub-agent spawning** — allow agents to spawn sub-agents for parallel work
7. **Atlassian integration** — Jira/Confluence for project management
8. **Agent naming** — unique identities for traceability
9. **Per-agent customization** — additional instructions per agent

Run with:
```bash
forge init
```

$ARGUMENTS
