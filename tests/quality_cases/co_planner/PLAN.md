# Implementation Plan

> Tracks implementation phases, their status, and what was delivered in each.

## Phase Summary

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | Complete | MVP — scaffolding, types, store, nodes, backend, canvas, command palette |
| Phase 2 | Complete | WebSocket — WS infra, commands over WS, shadow graph, proactive AI, edge hover |
| Phase 3 | Complete | Production AI — GraphAnalyzer, DB+pgvector, RAG, cache, feedback, path gen |
| Phase 4 | Complete | Graph-Native — GraphNativeRetriever, WL hash cache, direction-preserving dedup |
| Phase 4.1 | Complete | Prediction Quality — 8 quality fixes across cache, patterns, and tests |

---

## Phase 1: MVP (Complete)

**Goal**: Functional end-to-end flow from canvas to AI suggestions.

**Delivered**:
- Frontend: Next.js 15 + React Flow canvas with custom node types
- Zustand store with undo/redo (zundo)
- Backend: FastAPI with llm-gateway integration
- `POST /api/suggest` endpoint with structured output
- `POST /api/command` endpoint for Cmd+K palette
- FakeLLMProvider fallback for pattern-only mode
- Basic PatternLibrary with 9 regex rules
- shadcn/ui components + Tailwind v4 styling

---

## Phase 2: WebSocket Infrastructure (Complete)

**Goal**: Real-time bidirectional communication for proactive AI.

**Delivered**:
- Native WebSocket at `/ws` with JSON message protocol
- Connection manager with session tracking
- Shadow graph — per-session in-memory graph replica
- Proactive engine — debounced (800ms) ghost suggestion push
- Edge hover suggestions via WS
- Cmd+K over WS with HTTP SSE fallback
- Event emitter — Zustand store subscriber → WS event bridge
- Feedback emission on accept/reject/modify
- Keepalive (ping/pong 30s) with exponential backoff reconnection

---

## Phase 3: Production AI Backend (Complete)

**Goal**: Multi-tier suggestion pipeline with RAG, caching, and feedback.

**Delivered**:
- GraphAnalyzer (Tier 2) — motif detection, density, cycles, 2-hop neighborhoods
- TemplateMatcher (Tier 3) — 10 JSON templates with keyword overlap
- Database schema with Alembic migrations (PatternEmbedding, SuggestionFeedback, SemanticCache)
- HybridRetriever — vector + keyword search via pgvector
- PatternCorpus — seed from templates, extract subpaths, embed and store
- SuggestionCache — in-memory LRU + pgvector semantic cache
- FeedbackCollector — batched persistence (5s or 10 events)
- FeedbackScorer — confidence = 0.7 * model + 0.3 * historical
- PathGenerator — 3-5 node sub-flow generation
- Enhanced system prompt with structural awareness and few-shot examples
- Graceful degradation — all components optional

---

## Phase 4: Graph-Native Retrieval (Complete)

**Goal**: Replace text-embedding RAG with structural graph algorithms. Eliminate OpenAI embedding dependency.

**Delivered**:
- GraphNativeRetriever with 4-tier retrieval:
  1. WL Hash (O(1) indexed lookup, score=1.0)
  2. VF2 Isomorphism (subgraph match, score=0.9)
  3. Graph Edit Distance (fuzzy similarity, threshold>=0.5)
  4. Keyword (SQL array overlap, weighted 0.5x)
- WL hash cache tier replacing pgvector semantic cache
- PatternCorpus updated: stores `pattern_graph_json` (JSONB) + `wl_hash` (indexed)
- Direction-preserving deduplication in corpus
- Pure functions: `wl_hash()`, `vf2_match()`, `graph_edit_distance_similarity()`
- HybridRetriever kept as fallback (no longer wired in)
- Alembic migration for new columns

**ADRs**:
- ADR-007: Graph-native retrieval over text embedding RAG
- ADR-008: WL hash cache tier over semantic embedding cache

---

## Phase 4.1: Prediction Quality Fixes (Complete)

**Goal**: Fix 8 quality problems revealed by visualization of 19 prediction scenarios.

**Problems identified**:
1. WL cache domain-blindness — structurally identical graphs from different domains share cache keys
2. Generic decision branch labels — "Within Budget?" → "Process Result" instead of domain-specific
3. Pattern library regex gaps — no travel/booking/ETL rules, "Load to Warehouse" matches READ
4. Fake LLM keyword matching — broad keywords in entire prompt cause wrong-domain matches

**Fixes delivered**:
- **Fix A**: `_compute_wl_key` now includes `{wl_hash}:{label_norm}:{node_type}` composite key
- **Fix B**: 8 new keyword branches in `_decision_suggestions()` + `_extract_concept()` fallback
- **Fix C**: 3 new regex rules (ETL, travel, budget) + read rule negative lookahead
- **Fix D**: Response factories extract selected node label via regex for high-signal matching

**Files modified**: `suggestion_cache.py`, `pattern_library.py`, `visualize_predictions.py`, `test_prediction_quality.py`, `test_suggestion_cache.py`

**Verification**: All 87 tests pass (55 unit + 11 integration + 21 e2e). Live visualization confirms all 19 scenarios produce domain-relevant predictions.

---

## Future Phases (Planned)

### Phase 5: Collaboration & Multi-User
- Multi-user WebSocket sessions with cursor presence
- Operational transform or CRDT for concurrent edits
- Shared diagram persistence

### Phase 6: Advanced AI
- GraphSAGE embeddings (requires training data from user interactions)
- Multi-turn conversational AI for complex diagram authoring
- Template suggestion based on diagram similarity
- Auto-layout suggestions

### Phase 7: Production Deployment
- Docker multi-stage builds
- CI/CD pipeline (GitHub Actions)
- Monitoring (OpenTelemetry)
- Cost tracking dashboard
- Rate limiting
