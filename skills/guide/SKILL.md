---
name: guide
description: "Direct a specific agent via the Team Leader"
argument-hint: "<agent-name> <message>"
---

# /forge:guide — Direct an Agent

Send a prioritized directive to a specific agent through the Team Leader.

## Usage

`/forge:guide <agent-name> "<message>"`

Example: `/forge:guide backend-developer "use PostgreSQL instead of SQLite"`

## Execution

1. Parse `$ARGUMENTS` to extract the agent name (first word) and message (rest)
2. Write to `shared/.human/override.md` with agent-directive metadata:

```yaml
---
timestamp: <ISO 8601>
type: agent-directive
target_agent: <agent-name>
---

## Agent Directive

**Target:** <agent-name>

<message>
```

1. The Team Leader reads this and relays the directive to the specific agent as a prioritized task. This keeps TL aware of all context changes.

Confirm the directive was queued, targeting which agent.

$ARGUMENTS
