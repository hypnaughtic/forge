# Backend Architecture

> Reference document for the co-planner backend. Covers all components, data flow, and integration points.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15 + React Flow + Zustand)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                  │
│  │  Canvas   │  │  Cmd+K   │  │ Event Emitter│                  │
│  │ FlowCanvas│  │ Palette  │  │ (Zustand→WS) │                  │
│  └─────┬─────┘  └─────┬────┘  └──────┬───────┘                  │
│        │              │              │                           │
│   HTTP REST      WS / SSE       WebSocket                       │
└────────┼──────────────┼──────────────┼──────────────────────────┘
         │              │              │
┌────────▼──────────────▼──────────────▼──────────────────────────┐
│  Backend (FastAPI + llm-gateway)                                 │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ /api/suggest  │  │ /api/command │  │ /ws (WebSocket)      │   │
│  │ /api/command  │  │ /stream (SSE)│  │  ├─ ConnectionMgr    │   │
│  └──────┬───────┘  └──────┬───────┘  │  ├─ ShadowGraph      │   │
│         │                 │          │  └─ ProactiveEngine   │   │
│         └────────┬────────┘          └──────────┬────────────┘   │
│                  │                              │                │
│                  ▼                              ▼                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              SuggestionEngine (orchestrator)              │   │
│  │                                                           │   │
│  │  1. PatternLibrary ──── Tier 1: regex (0ms)               │   │
│  │  2. GraphAnalyzer ───── Tier 2: structural (1ms)          │   │
│  │  3. TemplateMatcher ─── Tier 3: JSON templates (1ms)      │   │
│  │  4. SuggestionCache ─── 3-tier check (0-1ms)              │   │
│  │  5. GraphNativeRetriever RAG (10-100ms)                   │   │
│  │  6. LLM (llm-gateway) ─ Claude Sonnet (500-2000ms)       │   │
│  │  7. FeedbackScorer ──── confidence adjust (5ms)           │   │
│  │  8. PathGenerator ───── multi-step paths (500-2000ms)     │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │  PostgreSQL + pgvector                                    │   │
│  │  ├─ pattern_embeddings (corpus + WL hash index)           │   │
│  │  ├─ suggestion_feedback (accept/reject signals)           │   │
│  │  ├─ semantic_cache (optional persistence)                 │   │
│  │  └─ diagrams (metadata)                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app + lifespan (init all services)
│   ├── config.py                  # Pydantic Settings (env-driven)
│   ├── errors.py                  # Error hierarchy (AppError → Retryable/Fatal/LLM/Validation)
│   ├── models/
│   │   ├── requests.py            # GraphNode, GraphEdge, GraphContext, SuggestionRequest
│   │   ├── responses.py           # AISuggestion, SuggestionResponse
│   │   └── ws.py                  # WebSocket message types (discriminated union)
│   ├── prediction/
│   │   ├── suggestion_engine.py   # Orchestrator: pattern → cache → RAG → LLM → feedback
│   │   ├── pattern_library.py     # Tier 1: 14 regex rules + decision branch logic
│   │   ├── graph_analyzer.py      # Tier 2: motifs, density, cycles, neighborhoods
│   │   ├── template_matcher.py    # Tier 3: 10 JSON templates, keyword overlap
│   │   ├── system_prompt.py       # LLM system prompt with structural awareness
│   │   ├── command_prompt.py      # Free-text command prompt (Cmd+K)
│   │   ├── path_prompt.py         # Multi-step path generation prompt
│   │   ├── path_generator.py      # 3-5 node sub-flow generation
│   │   ├── graph_serializer.py    # Deterministic subgraph serialization
│   │   ├── graph_fingerprint.py   # SHA-256 fingerprinting for cache keys
│   │   └── context_builder.py     # Graph context extraction
│   ├── services/
│   │   ├── graph_native_retriever.py  # WL hash → VF2 → GED → keyword retrieval
│   │   ├── suggestion_cache.py        # 3-tier: exact → WL hash → pattern
│   │   ├── hybrid_retriever.py        # Legacy text-embedding RAG (kept as fallback)
│   │   ├── embedding_client.py        # EmbeddingClient Protocol + OpenAI impl
│   │   ├── feedback_collector.py      # Batched feedback persistence
│   │   ├── feedback_scorer.py         # Confidence adjustment from signals
│   │   └── pattern_corpus.py          # Corpus ingestion with NetworkX + WL hash
│   ├── routes/
│   │   ├── suggest.py             # POST /api/suggest
│   │   └── command.py             # POST /api/command, POST /api/command/stream
│   ├── ws/
│   │   ├── handler.py             # WebSocket endpoint + message dispatch
│   │   ├── connection_manager.py  # Session tracking + shadow graphs
│   │   ├── shadow_graph.py        # Per-session in-memory graph replica
│   │   └── proactive_engine.py    # Debounced proactive AI push
│   └── db/
│       ├── engine.py              # Async SQLAlchemy engine + session factory
│       ├── models.py              # ORM: PatternEmbedding, SuggestionFeedback, etc.
│       └── repositories.py        # Data access: PatternEmbeddingRepo, FeedbackRepo, CacheRepo
├── tests/
│   ├── conftest.py                # Shared fixtures (make_node, make_edge, graph factories)
│   ├── unit/                      # 55 tests — mock all I/O
│   ├── integration/               # 11 tests — real DB, mock LLM
│   ├── e2e/                       # 21 tests — full pipeline
│   ├── visualize_predictions.py   # Visual review with FakeLLM
│   └── visualize_predictions_live.py  # Visual review with local-claude
├── alembic/                       # Database migrations
├── pyproject.toml                 # Dependencies + pytest config
└── output/                        # Visualization output files
```

## Suggestion Pipeline

See [docs/specs/suggestion-pipeline.md](specs/suggestion-pipeline.md) for the full spec.

### Pipeline Flow

```
Request ──▶ PatternLibrary ──[conf >= 0.85]──▶ Return (fast path, 0ms)
               │
               ▼ (conf < 0.85)
          GraphAnalyzer ──▶ SuggestionCache.get()
                               │
                    ┌──────────┤
                    │ hit      │ miss
                    ▼          ▼
               Return     TemplateMatcher + GraphNativeRetriever
                               │
                               ▼
                          LLM Call (structured output)
                               │
                               ▼
                    Merge (pattern + LLM, dedup)
                               │
                               ▼
                     FeedbackScorer.adjust()
                               │
                               ▼
                    SuggestionCache.put() ──▶ Return
```

### Tier Details

| Tier | Component | Latency | When Used |
|------|-----------|---------|-----------|
| 1 | PatternLibrary | <1ms | Always (first check) |
| 2 | GraphAnalyzer | ~1ms | When pattern confidence < 0.85 |
| 3 | TemplateMatcher | ~1ms | Before LLM call |
| Cache | SuggestionCache | <1ms | After analysis, before LLM |
| RAG | GraphNativeRetriever | 10-100ms | After cache miss |
| LLM | llm-gateway | 500-2000ms | After cache miss |
| Feedback | FeedbackScorer | ~5ms | After merge |

## Graph-Native Retrieval

See [docs/specs/graph-native-retrieval.md](specs/graph-native-retrieval.md) for the full spec.

Replaced text-embedding RAG (ADR-007). All retrieval is now structural, no external API calls needed.

| Tier | Method | Speed | Score | Description |
|------|--------|-------|-------|-------------|
| 1 | WL Hash | O(1) | 1.0 | Weisfeiler-Leman 3-iteration hash, indexed lookup |
| 2 | VF2 Isomorphism | O(n²) | 0.9 | Subgraph match with node_type matching |
| 3 | Graph Edit Distance | O(n³) | 0.5-1.0 | Normalized similarity, max 20 nodes |
| 4 | Keyword | O(n) | 0.0-0.5 | SQL array overlap on node_labels, weighted 0.5x |

## Suggestion Cache

See [docs/specs/suggestion-cache.md](specs/suggestion-cache.md) for the full spec.

| Tier | Key | Storage | TTL | Max Size |
|------|-----|---------|-----|----------|
| Exact | Graph fingerprint (SHA-256) | In-memory LRU | 1 hour | 500 |
| WL Hash | `{wl_hash}:{label_norm}:{node_type}` | In-memory LRU | 2 hours | 1000 |
| Pattern | `{label}:{type}:{motifs}` | In-memory dict | 1 hour | unbounded |

## Pattern Library

See [docs/specs/pattern-library.md](specs/pattern-library.md) for the full spec.

14 regex rules covering: auth, validation, errors, notifications, persistence, data retrieval, deployment, payment, testing, ETL/data pipeline, travel/booking, budget/planning. Decision nodes get domain-specific branch labels via keyword matching with intelligent fallback.

## WebSocket Architecture

- **Transport**: Native WebSocket at `/ws`, JSON messages with discriminated `type` field
- **Keepalive**: ping/pong every 30s, 10s pong timeout, exponential backoff reconnection
- **Shadow Graph**: Server maintains per-session in-memory graph replica via incremental events
- **Proactive Engine**: Debounced (800ms) — generates and pushes ghost suggestions after graph mutations
- **Edge Hover**: Client sends `suggestion_request` with edge context → server responds
- **Cmd+K**: WS-first with HTTP SSE fallback when disconnected
- **Feedback**: Client sends `suggestion_feedback` on accept/reject/modify

## Database Schema

```
pattern_embeddings
├── id (UUID PK)
├── subgraph_text (TEXT)           # Canonical serialized subgraph
├── embedding (vector(1536))       # Optional OpenAI embedding
├── pattern_graph_json (JSONB)     # NetworkX node-link format
├── wl_hash (VARCHAR, indexed)     # Weisfeiler-Leman hash
├── node_labels (TEXT[])           # For keyword search
├── domain (VARCHAR)
├── source (VARCHAR)               # 'global' or 'user'
├── user_id (VARCHAR)
├── created_at (TIMESTAMPTZ)
└── updated_at (TIMESTAMPTZ)

suggestion_feedback
├── id (UUID PK)
├── session_id (VARCHAR)
├── anchor_node_label (VARCHAR)
├── anchor_node_type (VARCHAR)
├── suggestion_label (VARCHAR)
├── suggestion_node_type (VARCHAR)
├── action (VARCHAR)               # 'accepted', 'rejected', 'modified'
├── modified_label (VARCHAR)
├── graph_fingerprint (VARCHAR)
└── created_at (TIMESTAMPTZ)

semantic_cache
├── id (UUID PK)
├── fingerprint (VARCHAR, unique)
├── response_json (JSONB)
├── expires_at (TIMESTAMPTZ)
└── created_at (TIMESTAMPTZ)

diagrams
├── id (UUID PK)
├── name (VARCHAR)
├── graph_json (JSONB)
├── created_at (TIMESTAMPTZ)
└── updated_at (TIMESTAMPTZ)
```

## Graceful Degradation

| Component Missing | Impact | Behavior |
|---|---|---|
| PostgreSQL | No retrieval, no cache persistence, no feedback | Pattern + LLM still work |
| OpenAI API key | No legacy text embeddings | No impact (graph-native is embedding-free) |
| LLM API key | No LLM inference | Pattern-only mode (FakeLLMProvider fallback) |
| Feedback data | No confidence adjustment | Cold start, improves over time |

## Configuration

All config via `pydantic-settings` (`app/config.py`), loaded from environment variables or `.env`:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | LLM provider (`anthropic`, `local_claude`, `fake`) |
| `LLM_MODEL` | `claude-sonnet-4-5-20250514` | Model identifier |
| `LLM_TEMPERATURE` | `0.7` | Sampling temperature |
| `LLM_MAX_TOKENS` | `4096` | Max output tokens |
| `ANTHROPIC_API_KEY` | `""` | API key (optional with local_claude) |
| `DATABASE_URL` | `""` | PostgreSQL connection (optional) |
| `OPENAI_API_KEY` | `""` | For legacy text embeddings only (optional) |
| `PROACTIVE_ENABLED` | `true` | Enable proactive AI suggestions |
| `PROACTIVE_DEBOUNCE_MS` | `800` | Debounce interval for proactive engine |

## LLM Integration

Uses `llm-gateway` library with three provider modes:

1. **`anthropic`** — Direct API calls to Claude (requires `ANTHROPIC_API_KEY`)
2. **`local_claude`** — Delegates to local `claude` CLI subprocess (no API key needed, zero cost)
3. **`fake`** — `FakeLLMProvider` for testing with optional `response_factory`

Structured output via `response_model=SuggestionResponse` (Pydantic model). JSON schema embedded in prompt for `local_claude` provider.

## Test Architecture

```
tests/
├── unit/      (55 tests)  — Mock all I/O, run in <1s
├── integration/ (11 tests)  — Real DB via Docker, mock LLM
├── e2e/       (21 tests)  — Full pipeline with FakeLLMProvider
└── visualization tools    — Manual review with real or fake LLM
```

Run commands:
```bash
uv run pytest tests/unit/ -v           # Unit only
uv run pytest tests/integration/ -v    # Integration only
uv run pytest tests/e2e/ -v            # E2E only
uv run pytest --tb=short -q            # All tests

# Visual review
uv run python -m tests.visualize_predictions       # FakeLLM
uv run python -m tests.visualize_predictions_live   # local-claude (real LLM)
```
