# /forge-guide — Direct a Specific Agent

Parse `$ARGUMENTS` to extract the agent name (first word) and message (rest).

Write to `shared/.human/override.md` with agent-directive metadata:

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

The Team Leader reads this and relays the directive to the specific agent as a prioritized task.

Confirm which agent was targeted and what directive was sent.

Usage: `/forge-guide backend-developer "use PostgreSQL"`

$ARGUMENTS
