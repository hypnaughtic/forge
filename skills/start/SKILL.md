---
name: start
description: "Spawn the agent team and begin iteration 1"
argument-hint: "[focus area]"
---

# /forge:start — Begin Building

Read the project requirements from `config/project-requirements.md` and the team configuration from `config/team-config.yaml`.

## Startup Sequence

1. **Read config** — Load mode, strategy, team profile, tech stack, cost cap
2. **Initialize shared state** — Ensure all `shared/` directories exist
3. **Spawn agents** — Based on team profile (lean/full/custom), spawn the appropriate agents
4. **Decompose iteration 1** — Break requirements into tasks, assign to agents
5. **Begin orchestration** — Start the PLAN phase of iteration 1

If `$ARGUMENTS` contains a focus area, prioritize that in the iteration plan.

$ARGUMENTS
