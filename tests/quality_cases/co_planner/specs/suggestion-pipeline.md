# Suggestion Pipeline Specification

## Overview

The suggestion pipeline generates AI-powered next-node predictions for flowcharts. It combines multiple strategies to balance speed, quality, and cost.

## Architecture

```
SuggestionEngine (orchestrator)
  ├── PatternLibrary           (Tier 1 — 14 regex rules, ~0ms)
  ├── GraphAnalyzer            (Tier 2 — structural analysis, ~1ms)
  ├── TemplateMatcher          (Tier 3 — 10 JSON templates, ~1ms)
  ├── SuggestionCache          (3-tier cache check, ~0-1ms)
  ├── GraphNativeRetriever     (WL hash → VF2 → GED → keyword, ~10-100ms)
  ├── LLM via llm-gateway      (Claude Sonnet, ~500-2000ms)
  ├── FeedbackScorer           (confidence adjustment, ~5ms)
  └── PathGenerator            (multi-step paths, ~500-2000ms)
```

## Pipeline Flow

1. **Pattern Matching** (fast path): If confidence >= 0.85, return immediately. No LLM call needed. Handles ~68% of scenarios.
2. **Graph Analysis**: Compute structural metrics (motifs, density, cycles, 2-hop neighborhood).
3. **Cache Check**: Try exact match → WL hash match → pattern-level match. On hit, return cached response.
4. **Template Matching**: Find relevant domain templates via keyword overlap.
5. **Graph-Native Retrieval**: WL hash → VF2 isomorphism → GED → keyword. No embeddings needed.
6. **LLM Call**: Structured output with enriched prompt (graph context + templates + retrieved patterns).
7. **Merge**: Deduplicate pattern + LLM results. LLM takes priority on label overlap.
8. **Feedback Adjustment**: Blend model confidence with historical acceptance rate (0.7/0.3 split).
9. **Cache Store**: Store response in exact + WL hash + pattern caches.

## Component Specs

| Component | Spec Doc |
|---|---|
| PatternLibrary | [pattern-library.md](pattern-library.md) |
| SuggestionCache | [suggestion-cache.md](suggestion-cache.md) |
| GraphNativeRetriever | [graph-native-retrieval.md](graph-native-retrieval.md) |
| FeedbackScorer | [feedback-loop.md](feedback-loop.md) |
| Prediction Quality | [prediction-quality.md](prediction-quality.md) |

## Graceful Degradation

| Component Missing | Behavior |
|---|---|
| PostgreSQL | No graph-native retrieval, no cache persistence, no feedback. Pattern + LLM still work. |
| OpenAI API key | No impact. Graph-native retrieval is embedding-free. Only affects legacy corpus text storage. |
| LLM API key | Pattern-only mode via FakeLLMProvider. |
| Feedback data | Cold start — no confidence adjustment. Improves over time. |

## Data Flow

### Input
- `SuggestionRequest`: selected_node, graph (nodes + edges), diagram_name, domain

### Output
- `SuggestionResponse`: suggestions (1-3), source ("pattern"/"llm"/"hybrid"/"cache:*"), latency_ms, cost_usd

### Graph Analysis Output
- `GraphAnalysis`: ancestor chain, siblings, leaves, incomplete branches, motifs, density, branching factor, cycles, 2-hop neighborhood

## Cache Tiers

| Tier | Storage | Key | TTL | Max | Hit Condition |
|---|---|---|---|---|---|
| Exact | In-memory LRU | SHA-256 fingerprint | 1 hour | 500 | Fingerprint match |
| WL Hash | In-memory LRU | `{wl_hash}:{label}:{type}` | 2 hours | 1000 | Structure + selected label match |
| Pattern | In-memory dict | `{label}:{type}:{motifs}` | 1 hour | unbounded | Label + type + motif match |

## Source Distribution (from 19-scenario benchmark)

| Source | Scenarios | Avg Latency | Description |
|---|---|---|---|
| Pattern fast path | 68% | <1ms | High-confidence regex match, zero cost |
| Hybrid (pattern + LLM) | 26% | ~10s | Both sources contribute, merged + deduped |
| LLM only | 5% | ~10s | No pattern match, LLM generates all suggestions |
| Cache hit | varies | <1ms | Repeated or structurally similar queries |
