# Forge Inter-Agent Communication Protocol

## Overview

Forge agents communicate through a **file-based protocol**. All agents share the same filesystem. There are no databases, no network sockets, no HTTP APIs — just files written with atomic operations. Every coordination primitive (message queues, status signals, locks, decisions) is a file or directory under `shared/`.

## Message Queue System

Each agent owns an inbox: `shared/.queue/{agent-name}-inbox/`. Message files are named `msg-{unix-timestamp}-{sender}.md` and contain YAML frontmatter plus a Markdown body.

**Frontmatter fields:** `id` (string, same as filename), `from`, `to`, `priority` (`normal`|`high`|`critical`), `timestamp` (ISO-8601 UTC), `type` (`status-update`|`request`|`response`|`blocker`|`deliverable`|`review-request`|`review-response`|`dependency-change`), `confidence` (`high`|`medium`|`low`).

```markdown
---
id: msg-1716000000-orchestrator
from: orchestrator
to: backend
priority: high
timestamp: 2026-02-28T14:00:00Z
type: request
confidence: high
---
## Body
Implement the `/api/v1/users` endpoint per the OpenAPI spec in `shared/specs/api.yaml`.
## Artifacts
- Input: `shared/specs/api.yaml`
- Expected output: `src/routes/users.ts`, `src/repos/userRepo.ts`
## Needs From
- **database**: Migration file for the `users` table.
```

## Atomic Write Protocol

All file writes **must** be atomic to prevent readers from seeing partial content.

```bash
# --- WRITING ---
TMPFILE=$(mktemp "${TMPDIR:-/tmp}/forge-msg-XXXXXXXX")
cat > "$TMPFILE" << 'MSGEOF'
---
id: msg-1716000000-orchestrator
from: orchestrator
to: backend
priority: normal
timestamp: 2026-02-28T14:00:00Z
type: request
confidence: high
---
## Body
Please generate database seeds for testing.
MSGEOF
mv "$TMPFILE" shared/.queue/backend-inbox/msg-1716000000-orchestrator.md

# --- READING ---
for msg in $(ls shared/.queue/myagent-inbox/ | sort); do
  process_message "shared/.queue/myagent-inbox/$msg"
  rm "shared/.queue/myagent-inbox/$msg"
done
```

## Status File System

Location: `shared/.status/{agent-name}.json`

```json
{
  "agent": "backend", "status": "working",
  "current_task": "Implementing /api/v1/users endpoint",
  "blockers": [], "iteration": 4,
  "last_updated": "2026-02-28T14:12:00Z",
  "session_start": "2026-02-28T13:00:00Z",
  "artifacts_produced": ["src/routes/users.ts", "src/repos/userRepo.ts"],
  "estimated_completion": "2026-02-28T15:00:00Z",
  "messages_processed": 12,
  "usage_limits": { "max_tokens_per_session": 200000, "tokens_used": 84200, "max_cost_usd": 5.00, "cost_used_usd": 2.10 },
  "cost_estimate_usd": 2.10
}
```

| Status | Description | | Status | Description |
|---|---|---|---|---|
| `idle` | Running, no assigned task | | `done` | Task complete, awaiting next |
| `working` | Actively executing a task | | `suspended` | Paused by orchestrator/human |
| `blocked` | Waiting on another agent | | `rate-limited` | Paused due to API/token limits |
| `review` | Awaiting artifact review | | `error` | Unrecoverable error, needs help |
| | | | `terminated` | Session ended |

## Working Memory Files

Location: `shared/.memory/{agent-name}-memory.md`. Update **every 10 minutes minimum** and **immediately** before any status transition.

Required sections: **Current Objective** (what the agent is doing), **Progress** (checklist), **Key Decisions**, **Open Questions**, **Resume Context** (instructions for a fresh session: read this file, check status JSON, pick up from first unchecked item), **Limit Save Context** (when approaching token/cost limits, record: current file, line ranges, partial work location, next immediate step).

## Decision Log

Location: `shared/.decisions/decision-log.md` — append-only, never modified or deleted.

```markdown
### 2026-02-28T14:05:00Z — backend
**Decision:** Use repository pattern instead of inline SQL.
**Rationale:** Aligns with existing codebase conventions and improves testability.
**Confidence:** high
```

## Artifact Registry

Location: `shared/.artifacts/registry.json`

```json
{
  "artifacts": [{
    "path": "src/routes/users.ts",
    "produced_by": "backend",
    "timestamp": "2026-02-28T14:30:00Z",
    "description": "REST endpoint for user CRUD operations",
    "dependencies": ["src/repos/userRepo.ts", "shared/specs/api.yaml"],
    "consumers": ["frontend", "testing"],
    "checksum": "sha256:ab3f..."
  }]
}
```

**Registration:** After producing an artifact, acquire the registry lock, append an entry, release the lock. **Dependency declaration:** Populate `dependencies` with every file the artifact relies on. **Change notification:** When an artifact is modified, send a `dependency-change` message to every agent in `consumers`.

## File Locking

Lock location: `shared/.locks/{md5-hash-of-filepath}.lock`

```json
{
  "locked_by": "backend",
  "file_path": "shared/.artifacts/registry.json",
  "locked_at": "2026-02-28T14:30:00Z",
  "reason": "Registering new artifact",
  "expected_duration_minutes": 2
}
```

**Protocol:** (1) Check — if lock exists and is not stale, wait and retry. (2) Acquire — write lock atomically (temp file + `mv`). (3) Edit — perform the file operation. (4) Commit — ensure edited file is fully written via atomic move. (5) Release — delete the lock file.

**Stale lock handling:** A lock is stale if `locked_at` is older than `expected_duration_minutes * 3`. Any agent may delete a stale lock, re-acquire it, and log a warning to the decision log.

## Human Override Channel

Location: `shared/.human/override.md`

```markdown
---
timestamp: 2026-02-28T15:00:00Z
type: directive
---
Stop all work on the payments module. Pivot to fixing the auth bug in issue #42.
```

| Type | Effect |
|---|---|
| `directive` | New instructions overriding current tasks |
| `pause` | All agents stop and enter `suspended` status |
| `resume` | All agents resume from last known state |
| `mode-switch` | Change operational mode (e.g., cautious, fast) |
| `strategy-switch` | Change high-level approach or architecture |
| `abort` | Terminate all agents immediately |

**Monitoring:** Every agent must check this file at the start of each iteration and before any status transition. If `timestamp` is newer than the agent's last check, parse and obey before continuing.

## Structured Logging

Location: `shared/.logs/{agent-name}.log` — JSONL format, one entry per line.

```json
{"ts":"2026-02-28T14:05:00Z","agent":"backend","level":"info","category":"task","message":"Started implementing /api/v1/users","meta":{"file":"src/routes/users.ts"}}
```

**Fields:** `ts` (ISO-8601), `agent`, `level` (`debug`|`info`|`warn`|`error`), `category`, `message`, `meta` (optional object).

**Categories:** `task` (start/progress/completion), `artifact` (file create/modify/delete), `communication` (messages sent/received), `decision` (key choices), `cost` (token usage, budget warnings), `error` (failures, exceptions), `recovery` (session resumption, stale lock breaks, retries).

## Priority Levels

| Priority | When to Use |
|---|---|
| `normal` | Routine updates, non-blocking requests, status reports, informational messages |
| `high` | Blockers preventing progress, critical-path review requests, dependency changes |
| `critical` | Production-breaking issues, human override relays, security vulnerabilities, abort signals |

Process `critical` immediately, `high` before starting new work, `normal` in FIFO order.

## Message Types Reference

| Type | Description | Typical Sender | Typical Receiver |
|---|---|---|---|
| `status-update` | Progress or state changes | Any agent | Orchestrator |
| `request` | Ask another agent to perform work | Orchestrator | Worker agent |
| `response` | Reply to a previous request | Worker agent | Orchestrator |
| `blocker` | Signal that progress is blocked | Any agent | Orchestrator |
| `deliverable` | Notify that an artifact is ready | Worker agent | Dependent agents |
| `review-request` | Ask for review of produced work | Worker agent | Reviewer agent |
| `review-response` | Return review feedback | Reviewer agent | Original author |
| `dependency-change` | A depended-upon artifact changed | Producing agent | Consumer agents |
