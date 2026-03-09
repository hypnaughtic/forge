# Prediction Quality Specification

> Documents the 8 quality issues found via visualization and the fixes applied (Phase 4.1).

## Background

After implementing the graph-native retrieval pipeline (Phase 4), a visualization of 19 prediction scenarios revealed 8 quality problems. This spec documents the issues, root causes, fixes, and verification results.

## Issues Identified

### Issue 1-2: WL Cache Domain-Blindness (Scenarios 12, 17)

**Symptom**: Structurally identical graphs from different domains (e.g., a 3-node auth flow and a 3-node travel flow) shared WL hash cache keys. The second query returned suggestions from the first query's domain.

**Root cause**: `_compute_wl_key()` used only the WL hash of the neighborhood graph, which is purely structural. Two graphs with the same topology (e.g., `startEnd→process→process`) produce the same WL hash regardless of domain.

**Fix (Fix A)**: Changed `_compute_wl_key()` to produce a composite key:
```
Before: wl_hash(nx_graph)
After:  f"{wl_hash(nx_graph)}:{label_norm}:{selected_node.type}"
```

This ensures that "Login" (auth) and "Book Flights" (travel) produce different cache keys even if their surrounding graph structure is identical.

**File**: `app/services/suggestion_cache.py`

### Issue 3-4: Generic Decision Branch Labels (Scenarios 5, 14)

**Symptom**: Decision nodes like "Within Budget?" or "Check 2FA" got generic labels: "Process Result" / "Handle Failure" instead of domain-specific ones.

**Root cause**: `_decision_suggestions()` only had 5 keyword branches (valid, exist, approv, success, stock). Labels like "budget", "2fa", "test" fell through to the generic fallback.

**Fix (Fix B)**: Added 8 new keyword branches before the generic fallback:

| Keywords | Yes Label | No Label |
|---|---|---|
| budget, cost, afford, price | Confirm Booking | Adjust Plans |
| 2fa, mfa, two-factor | Grant Access | Deny Access |
| auth, security, permission | Grant Access | Deny Access |
| test, pass | Continue Pipeline | Fix Issues |
| ready, complete, finish | Proceed | Review Again |
| correct, match | Accept | Revise |
| within, limit, threshold | Proceed | Adjust |
| connect, reachable, online | Continue | Retry Connection |

Also added `_extract_concept()` for smarter generic fallback: "Within Budget?" → concept="Budget" → "Handle Budget" / "Resolve Budget".

**File**: `app/prediction/pattern_library.py`

### Issue 5-6: Pattern Library Regex Gaps (Scenarios 15, 19)

**Symptom**: "Load to Warehouse" matched the READ pattern rule (`fetch|load|read|get|query|retrieve`), producing "Data Found?" + "Transform Data" instead of ETL-appropriate suggestions. No rules existed for travel/booking or ETL domains.

**Root cause**: The `load` keyword in the READ rule was too broad. No travel, booking, or ETL-specific rules existed.

**Fix (Fix C)**: Added 3 new regex rules BEFORE the read rule:

1. **ETL/data pipeline**: `\b(load\s+(?:to|into)|etl|ingest|warehouse|import\s+data)\b`
   → Load Successful? (0.85) + Archive Source (0.75)

2. **Travel/booking**: `\b(book|reserv|flight|hotel|travel|itinerary|trip)\b`
   → Booking Confirmed? (0.85) + Compare Alternatives (0.72)

3. **Budget/planning**: `\b(budget|plan\b|schedul|allocat|cost\s+estimate)\b`
   → Within Budget? (0.85) + Review Plan (0.72)

Modified the read rule with negative lookahead: `load(?!\s+(?:to|into)\b)` prevents "Load to Warehouse" from matching the read rule.

**File**: `app/prediction/pattern_library.py`

### Issue 7-8: Fake LLM Keyword Matching (Scenarios 10, 11, 13)

**Symptom**: In tests and visualization, the FakeLLMProvider's `response_factory` matched keywords against the entire prompt. Broad keywords like "service" (in "Order Service" scenario) triggered the wrong branch (API Gateway/microservice suggestions instead of order-specific ones).

**Root cause**: The response factory scanned the full prompt for keywords. In Scenario 10 (selected: "Order Service"), the prompt contained "Auth Service", "User Service", "API Gateway" — all matching the `service`/`api gateway` branch, overshadowing the actual selected node.

**Fix (Fix D)**: Two changes:
1. **Extract selected node label** from the prompt via regex: `r'selected the node "([^"]+)"'`
2. **Match on selected label first** (high signal), then fall back to full prompt (low signal)
3. **Added missing branches**: database/data → Cache Layer/Backup; ETL → Validate Data Quality/Archive Source; budget → Compare Prices/Within Budget?; order → Order Database/Inventory Check
4. **Reordered elif chain**: specific domains first (ETL, deploy, database), broad last (service)

**Files**: `tests/visualize_predictions.py`, `tests/e2e/test_prediction_quality.py`

## Test Updates

### WL Cache Unit Tests (`tests/unit/test_suggestion_cache.py`)

- `test_wl_hash_hit_for_same_structure` → renamed to `test_wl_hash_hit_for_same_structure_same_label`, graph2's selected node now shares the label with graph1 (required for composite key match)
- Added `test_wl_hash_miss_for_cross_domain_labels` — verifies that same topology with different selected labels does NOT hit WL cache

### WL Cache E2E Test (`tests/e2e/test_prediction_quality.py`)

- `test_wl_cache_hit_for_isomorphic_graph` — graph2's selected node now uses the same label as graph1 ("Prepare Ingredients") to demonstrate legitimate WL cache hit

## Verification Results

**Test suite**: 87 tests pass (55 unit + 11 integration + 21 e2e)

**Live visualization** (19 scenarios with local-claude):

| Scenario | Selected Node | Source | Predictions |
|---|---|---|---|
| 10 | Order Service | hybrid | Payment Service, Inventory Service, Order Database |
| 12 | Set Budget | pattern | Within Budget?, Review Plan |
| 13 | Book Flights | pattern | Booking Confirmed?, Compare Alternatives |
| 14 | Within Budget? | pattern | Confirm Booking, Adjust Plans, Review Plan |
| 15 | Run Tests | hybrid | Tests Pass?, Build Artifact, Notify Failure |
| 19 | Load to Warehouse | pattern | Load Successful?, Archive Source |

All 6 key scenarios now produce domain-relevant predictions. Scenarios 12, 13, 14, 19 are now handled by the pattern fast path (0ms, zero cost). Scenarios 10 and 15 correctly reach the LLM with proper context.

## Source Distribution (19 scenarios)

| Source | Count | Percentage |
|---|---|---|
| Pattern (fast path) | 13 | 68% |
| Hybrid (pattern + LLM) | 5 | 26% |
| LLM only | 1 | 5% |

Average latency: 3.4s per scenario (dominated by LLM calls at ~10s each, pattern fast path at 0ms).
