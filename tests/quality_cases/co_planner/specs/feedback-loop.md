# Feedback Loop Specification

## Overview

The feedback loop captures user accept/reject/modify signals on AI suggestions and uses them to improve future suggestions in two ways:
1. **Confidence adjustment**: Blend model confidence with historical acceptance rates
2. **Corpus growth**: Accepted patterns are ingested into the RAG corpus

## Components

### FeedbackCollector
Batches feedback events and writes them to the `suggestion_feedback` table.

**Batching**: Events are queued and flushed either every 5 seconds or when 10 events accumulate, whichever comes first. This reduces DB write pressure.

**Event Flow**:
1. Client sends `suggestion_feedback` WebSocket message (accept/reject/modify)
2. WS handler calls `FeedbackCollector.record()` → enqueues event
3. Background task flushes batch to `suggestion_feedback` table
4. On accept: additionally ingests the accepted subpath into RAG corpus

### FeedbackScorer
Adjusts suggestion confidence based on historical feedback.

**Formula**: `final_confidence = 0.7 * model_confidence + 0.3 * historical_acceptance_rate`

**Cold Start**: When no historical data exists for an anchor context, confidence is passed through unchanged. The system improves organically as users interact.

**Grouping**: Historical rates are computed per (anchor_node_label, anchor_node_type) pair. This groups similar suggestion contexts.

## WebSocket Message

### Client → Server: `suggestion_feedback`

```json
{
  "type": "suggestion_feedback",
  "anchor_node_id": "node-123",
  "anchor_node_label": "Validate Input",
  "anchor_node_type": "process",
  "suggestion_label": "Input Valid?",
  "suggestion_node_type": "decision",
  "action": "accepted",
  "modified_label": null
}
```

**Actions**:
- `accepted`: User accepted the suggestion as-is
- `rejected`: User dismissed the suggestion
- `modified`: User accepted but changed the label (original in `suggestion_label`, new in `modified_label`)

## Database Schema

```sql
CREATE TABLE suggestion_feedback (
    id UUID PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    anchor_node_label VARCHAR(255) NOT NULL,
    anchor_node_type VARCHAR(50) NOT NULL,
    suggestion_label VARCHAR(255) NOT NULL,
    suggestion_node_type VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,           -- 'accepted', 'rejected', 'modified'
    modified_label VARCHAR(255),
    graph_fingerprint VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## Graceful Degradation

- **No DB**: Feedback signals are silently dropped. Suggestions still work without historical data.
- **No embedding client**: Accepted patterns are stored in feedback table but not ingested into RAG corpus.
- **Cold start**: All suggestions use pure model confidence until sufficient feedback accumulates.
