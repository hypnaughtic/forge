# /forge-ask — Message Team Leader

Send a message to the Team Leader with smart NL routing.

First, check if the message contains instant intents by running:

```bash
bash $FORGE_DIR/scripts/nl-router.sh "$ARGUMENTS"
```

If the result contains only INSTANT intents (STATUS, COST, TEAM, MODE, STRATEGY, SNAPSHOT), execute those directly. Intent always wins over invocation path.

If the result is ASK (no instant match), write the message to `shared/.human/override.md`:

```yaml
---
timestamp: <ISO 8601>
type: directive
---

## Directive

<message>
```

Confirm the message was queued.

$ARGUMENTS
