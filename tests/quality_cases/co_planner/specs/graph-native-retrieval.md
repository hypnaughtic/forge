# Graph-Native Retrieval Specification

> Structural pattern retrieval using graph algorithms. Replaces text-embedding RAG (ADR-007). No external API calls needed.

## Overview

The `GraphNativeRetriever` finds similar flowchart patterns in the corpus using purely structural methods. It eliminates the OpenAI embedding dependency and provides faster, more topologically-accurate retrieval.

**File**: `app/services/graph_native_retriever.py`

## Architecture

```
GraphNativeRetriever.retrieve(analysis, selected_node)
  │
  ├── Build query graph (neighborhood → NetworkX)
  │
  ├── Tier 1: WL Hash Lookup
  │     Compute wl_hash(query_graph)
  │     SELECT WHERE wl_hash = ? (O(1) indexed)
  │     Score: 1.0 (exact structural match)
  │
  ├── Tier 2: VF2 Isomorphism
  │     Load candidate patterns from DB
  │     vf2_match(query_graph, pattern_graph)
  │     Score: 0.9 (subgraph isomorphism with node_type matching)
  │
  ├── Tier 3: Graph Edit Distance
  │     For remaining candidates (≤20 nodes)
  │     graph_edit_distance_similarity(query_graph, pattern_graph)
  │     Score: normalized similarity (threshold ≥ 0.5)
  │
  └── Tier 4: Keyword Overlap
        SQL: node_labels && ARRAY[...query_labels...]
        Score: Jaccard overlap * 0.5 (weighted down)
```

## Retrieval Tiers

### Tier 1: Weisfeiler-Leman Hash (WL Hash)

- **Algorithm**: 3-iteration WL hash over node types and edge structure
- **Lookup**: O(1) via indexed `wl_hash` column in `pattern_embeddings`
- **Score**: 1.0 (exact structural fingerprint match)
- **Behavior**: If a WL hash match is found, it's guaranteed to have the same topology (modulo hash collisions, which are rare with 3 iterations)

**Implementation**:
```python
def wl_hash(graph: nx.DiGraph, iterations: int = 3) -> str:
    # Initialize labels from node_type attribute
    # For each iteration: aggregate neighbor labels, sort, hash
    # Produce final graph-level hash from sorted node hashes
```

### Tier 2: VF2 Subgraph Isomorphism

- **Algorithm**: VF2 algorithm via `networkx.algorithms.isomorphism`
- **Matching**: `node_type` must match between query and pattern nodes
- **Score**: 0.9
- **Use case**: When the query graph is a subgraph of a larger corpus pattern

### Tier 3: Graph Edit Distance (GED)

- **Algorithm**: Optimized GED via `networkx.graph_edit_distance` with upper bound
- **Score**: `1.0 - (ged / max_possible_edits)`, clamped to [0.0, 1.0]
- **Threshold**: Only returned if similarity >= 0.5
- **Guard**: Skipped for graphs > 20 nodes (O(n³) complexity)
- **Use case**: Fuzzy structural similarity for graphs that aren't exact matches

### Tier 4: Keyword Overlap

- **Algorithm**: SQL array overlap (`&&` operator) on `node_labels` column
- **Score**: Jaccard-like overlap * 0.5 (weighted down to prefer structural methods)
- **Use case**: Fallback when structural methods find no matches

## Pure Functions

The module exports reusable pure functions used by both retrieval and caching:

| Function | Purpose | Used By |
|---|---|---|
| `wl_hash(nx_graph)` | Compute WL fingerprint | Retriever Tier 1, SuggestionCache Tier 2, PatternCorpus |
| `vf2_match(g1, g2)` | Check subgraph isomorphism | Retriever Tier 2 |
| `graph_edit_distance_similarity(g1, g2)` | Fuzzy structural similarity | Retriever Tier 3 |
| `neighborhood_to_nx(neighborhood)` | Convert GraphAnalysis neighborhood to NetworkX | Retriever, Cache |
| `subpath_to_nx(subpath)` | Convert subpath list to NetworkX | PatternCorpus |

## Corpus Storage

Patterns are stored in `pattern_embeddings` with:
- `pattern_graph_json` (JSONB): NetworkX node-link format graph
- `wl_hash` (VARCHAR, indexed): Precomputed WL hash for O(1) lookup
- `node_labels` (TEXT[]): For keyword search fallback
- `embedding` (vector(1536)): Optional, for legacy text-embedding search

## Comparison with Text-Embedding RAG (Superseded)

| Aspect | Text Embedding (old) | Graph-Native (current) |
|---|---|---|
| Topology awareness | Low (text loses structure) | High (preserves graph structure) |
| API dependency | OpenAI embeddings required | None (all local computation) |
| Latency | 50-200ms (API call) | 10-100ms (local algorithms) |
| Cost | ~$0.0001 per query | $0.00 |
| Fan-out vs chain | Cannot distinguish | Correctly differentiates |

## Integration

The `SuggestionEngine` calls `retriever.retrieve()` after a cache miss. Retrieved patterns are formatted and injected into the LLM prompt under "## Similar Patterns from Corpus".

The retriever returns `list[RetrievedPattern]` with:
- `subgraph_text`: Human-readable pattern description
- `similarity_score`: 0.0-1.0
- `source`: "wl_hash" | "vf2" | "ged" | "keyword"
