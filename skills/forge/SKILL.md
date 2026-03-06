---
name: forge
description: "Initialize a project with Claude Code agent team configuration"
argument-hint: "[project-description]"
---

# /forge — Project Initialization

You are the Forge project initializer. When the user invokes `/forge`, help them set up their Claude Code agent team.

## What Forge Does

Forge generates agent instruction files for Claude Code CLI agent teams. It creates:
- `.claude/agents/*.md` — Agent instruction files for each team member
- `CLAUDE.md` — Team Leader context and project configuration
- `.claude/skills/*.md` — Reusable skills for the team
- `team-init-plan.md` — Bootstrap plan for the first Claude session
- `.claude/mcp.json` — MCP server configuration (if Atlassian enabled)
- `forge-config.yaml` — Project configuration

## How to Use

Run the forge CLI to start the interactive wizard:

```bash
forge init
```

Or if forge is installed as a Python package:

```bash
forge init --project-dir /path/to/project
```

## After Initialization

Once files are generated:
1. Navigate to the project directory
2. Run `claude` to start a Claude Code session
3. Tell Claude: "Read team-init-plan.md and initialize the team"
4. The Team Leader agent will spawn the team and begin Iteration 1

$ARGUMENTS
