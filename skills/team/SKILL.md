---
name: team
description: "Detailed per-agent view (name, status, task, decisions, cost)"
argument-hint: "[agent-name]"
---

# /forge:team — Team View

Show detailed information about agents.

## Usage

- `/forge:team` — All agents overview
- `/forge:team <agent-name>` — Deep dive on one agent

## Execution

Run the team view script:

```bash
bash "$FORGE_DIR/scripts/team-view.sh" $ARGUMENTS
```

This reads:

- `shared/.status/*.json` for agent statuses
- `shared/.memory/*-memory.md` for agent working memory
- Cost data from status files

### All-Agent View

Shows a table with: agent name, status (color-coded), current task, recent decisions, estimated cost.

### Single-Agent Deep Dive

Shows full detail for one agent: status, current task, complete working memory, decision history, artifacts produced, cost breakdown.

$ARGUMENTS
