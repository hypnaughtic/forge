---
name: mode
description: "Switch project quality mode (mvp / production-ready / no-compromise)"
argument-hint: "<mvp|production-ready|no-compromise>"
---

# /forge:mode — Switch Project Mode

Change the project quality mode. This affects quality thresholds, testing requirements, CI/CD expectations, documentation depth, and team composition.

## Usage

`/forge:mode <value>` where value is one of:

- `mvp` — Fast iteration, 70% critic pass, happy-path tests, lean team
- `production-ready` — 90% critic pass, >90% coverage, full CI/CD, full team
- `no-compromise` — 100% critic pass, exhaustive tests, full pipeline, full team

## Execution

Run the mode change script:

```bash
bash "$FORGE_DIR/scripts/change-mode.sh" "$ARGUMENTS"
```

Report: old mode → new mode, what changed (quality thresholds, team composition, testing requirements).

**Note:** This command changes the project quality mode only. To change the execution strategy (auto-pilot/co-pilot/micro-manage), use `/forge:strategy`.

$ARGUMENTS
