---
name: stop
description: "Save state and gracefully shut down all agents"
argument-hint: ""
---

# /forge:stop — Graceful Shutdown

Save current state and shut down all agents gracefully.

```bash
bash "$FORGE_DIR/scripts/stop.sh"
```

This will:

1. Broadcast `PREPARE_SHUTDOWN` to all agents
2. Wait for agents to save their state
3. Capture a full snapshot (memory, status, decisions, iteration)
4. Terminate all agent processes

Report the snapshot location so the user can resume later.

$ARGUMENTS
