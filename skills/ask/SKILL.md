---
name: ask
description: "Send a message or question to the Team Leader"
argument-hint: "<message>"
---

# /forge:ask — Message Team Leader

Send a natural language message to the Team Leader for processing.

## Smart Classification

Before queuing as async, first check if the message contains INSTANT intents:

```bash
bash "$FORGE_DIR/scripts/nl-router.sh" "$ARGUMENTS"
```

If the router returns INSTANT intents (STATUS, COST, TEAM, MODE, STRATEGY, SNAPSHOT), execute those directly — **intent always wins over invocation path**.

Only if the router returns `ASK` (no instant match) should this be queued as an async directive.

## Async Queueing

Write the message to `shared/.human/override.md`:

```yaml
---
timestamp: <ISO 8601>
type: directive
---

## Directive

<user message>
```

Confirm the message was queued and the Team Leader will process it at the next check cycle.

$ARGUMENTS
