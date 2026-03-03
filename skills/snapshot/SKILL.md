---
name: snapshot
description: "Save current state without stopping the session"
argument-hint: ""
---

# /forge:snapshot — Non-Destructive State Save

Save the current session state (memory, status, decisions, iteration progress) without stopping agents.

```bash
bash "$FORGE_DIR/scripts/stop.sh" --snapshot-only
```

Report the snapshot file path and what was saved.

$ARGUMENTS
