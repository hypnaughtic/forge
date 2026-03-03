---
name: status
description: "Show iteration progress, agent statuses, tasks, blockers, and cost brief"
argument-hint: ""
---

# /forge:status — Project Status

Report the current project status. This is an INSTANT command — no AI reasoning needed for data collection.

## Steps

1. Report from your working memory:
   - Iteration number and current phase
   - Task progress (completed / total)
   - Active agents and their current tasks
   - Any blockers or issues

2. Run the status script for live agent data:

   ```bash
   bash "$FORGE_DIR/scripts/status.sh"
   ```

3. Run the cost tracker for a brief cost summary:

   ```bash
   bash "$FORGE_DIR/scripts/cost-tracker.sh" --report
   ```

Keep it brief. The user wants a quick snapshot, not a deep analysis.

$ARGUMENTS
