# Suggestion Cache Specification

> 3-tier in-memory cache for suggestion responses. No external services required.

## Overview

The `SuggestionCache` provides fast response caching at three levels of specificity. All tiers are in-memory with optional PostgreSQL persistence for the semantic tier.

**File**: `app/services/suggestion_cache.py`

## Cache Tiers

```
SuggestionCache.get(analysis, selected_node)
  │
  ├── Tier 1: Exact Match (fingerprint)
  │     Key: SHA-256(serialized neighborhood + node identity)
  │     TTL: 1 hour | Max: 500 entries | Storage: LRU OrderedDict
  │
  ├── Tier 2: WL Hash Match (structural + domain)
  │     Key: "{wl_hash}:{label_norm}:{node_type}"
  │     TTL: 2 hours | Max: 1000 entries | Storage: LRU OrderedDict
  │
  └── Tier 3: Pattern Match (label + type + motifs)
        Key: "{label_normalized}:{type}:{sorted_motifs}"
        TTL: 1 hour | Max: unbounded | Storage: plain dict
```

## Tier Details

### Tier 1: Exact Fingerprint Match

- **Key**: `fingerprint(analysis, selected_node)` — SHA-256 hash of the graph's serialized neighborhood combined with selected node identity
- **Hit condition**: Identical graph structure + identical selected node
- **Use case**: Repeated queries on the same graph (e.g., user deselects and reselects a node)
- **Source label**: `cache:exact`

### Tier 2: WL Hash Structural Match

- **Key**: `{wl_hash}:{label_norm}:{node_type}` — composite of Weisfeiler-Leman hash, normalized selected node label, and node type
- **Hit condition**: Same graph topology AND same selected node label+type (different node IDs are OK)
- **Use case**: User builds a graph with the same structure and same key node as a previously-seen graph
- **Source label**: `cache:wl_hash`

**Domain-awareness** (ADR-009): The composite key includes the selected node's label and type to prevent cross-domain cache pollution. Without this, structurally identical graphs from different domains (e.g., a 3-node auth flow and a 3-node travel flow) would share cache entries, returning wrong-domain suggestions.

### Tier 3: Pattern-Level Match

- **Key**: `{label_normalized}:{type}:{motif1,motif2,...}` — selected node identity combined with detected graph motifs
- **Hit condition**: Same node label + type + same structural motifs
- **Use case**: Different graphs that share the same node label and similar structural patterns
- **Source label**: `cache:pattern`

## Put Behavior

`SuggestionCache.put()` stores responses in **all applicable tiers** simultaneously:
1. Always stores in Tier 1 (exact)
2. Stores in Tier 2 if neighborhood exists (can compute WL hash)
3. Always stores in Tier 3 (pattern)
4. Optionally persists to PostgreSQL `semantic_cache` table (for cross-restart survival)

Empty responses (no suggestions) are **not cached**.

## LRU Eviction

Tiers 1 and 2 use `OrderedDict` with LRU eviction:
- On access: entry moved to end (`move_to_end`)
- On overflow: oldest entry popped from front (`popitem(last=False)`)
- Tier 1 max: 500 entries
- Tier 2 max: 1000 entries

## TTL Expiration

Entries are lazily expired on access (no background cleanup):
- If an entry is found but expired, it is deleted and treated as a miss
- TTL is checked via `time.monotonic()` difference from `cached_at`

## DB Persistence (Optional)

When a `session_factory` is provided, `put()` also upserts to the `semantic_cache` table:
- Fingerprint as the unique key
- Response serialized as JSON
- Expiry set to `now() + 4 hours`
- DB failures are logged and silently ignored (cache is best-effort)

## Integration

The `SuggestionEngine` calls `cache.get()` after `GraphAnalyzer` (because analysis is needed for cache keys) but before the LLM call. On cache hit, the response is returned immediately with zero cost.

After computing a response (LLM or pattern+LLM merge), the engine calls `cache.put()` to populate all tiers for future queries.

## Constants

```python
_EXACT_CACHE_MAX = 500
_WL_CACHE_MAX = 1000
_EXACT_TTL_SECONDS = 3600     # 1 hour
_WL_TTL_SECONDS = 7200        # 2 hours
_SEMANTIC_TTL_SECONDS = 14400  # 4 hours (DB persistence only)
```
