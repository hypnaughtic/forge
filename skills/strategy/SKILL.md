---
name: strategy
description: "Switch execution strategy (auto-pilot / co-pilot / micro-manage)"
argument-hint: "<auto-pilot|co-pilot|micro-manage>"
---

# /forge:strategy — Switch Execution Strategy

Change the execution strategy. This affects how much human approval is required for agent decisions.

## Usage

`/forge:strategy <value>` where value is one of:

- `auto-pilot` — Fully autonomous, agents make all decisions
- `co-pilot` — Agents handle routine work, seek approval for architecture/tech choices
- `micro-manage` — Every significant decision requires human approval

## Execution

Run the strategy change script:

```bash
bash "$FORGE_DIR/scripts/change-strategy.sh" "$ARGUMENTS"
```

Report: old strategy → new strategy, what changed (approval behavior, permission flags).

**Note:** This command changes the execution strategy only. To change the project quality mode (mvp/production-ready/no-compromise), use `/forge:mode`.

$ARGUMENTS
