# Pattern Library Specification

> Tier 1 of the suggestion pipeline. Deterministic regex-based pattern matching for fast, zero-cost suggestions.

## Overview

The `PatternLibrary` provides instant suggestions based on node type and label patterns without requiring an LLM call. When the top suggestion's confidence is >= 0.85, the engine returns immediately (fast path) without invoking downstream tiers.

**File**: `app/prediction/pattern_library.py`

## Architecture

```
PatternLibrary.match(selected_node, graph)
  │
  ├── Rule 1: Decision node? → _decision_suggestions()
  │     └── Keyword matching → domain-specific Yes/No labels
  │
  ├── Rule 2: Start node? → _start_suggestions()
  │     └── "Initialize" / "Receive Input"
  │
  ├── Rule 3: Label regex match? → _build_rules() patterns
  │     └── 14 regex rules covering common domains
  │
  └── Rule 4: Leaf process node? → _leaf_process_suggestions()
        └── Generic next-step suggestions (lower confidence)
```

## Regex Rules (14 total)

| # | Pattern | Domain | Suggestions |
|---|---------|--------|-------------|
| 1 | `\b(login\|log in\|sign.?in\|auth)\b` | Authentication | Validate Credentials, Check 2FA |
| 2 | `\bvalidat(e\|ion\|ing)\b` | Validation | Input Valid?, Return Error |
| 3 | `\b(error\|exception\|fail\|fault)\b` | Error handling | Log Error, Retry?, Notify User |
| 4 | `\b(send\|email\|notify\|alert)\b` | Notification | Delivery Successful?, Log Notification |
| 5 | `\b(save\|store\|persist\|write\|insert)\b` | Persistence | Save Successful?, Return Confirmation |
| 6 | `\b(load\s+(?:to\|into)\|etl\|ingest\|warehouse\|import\s+data)\b` | ETL/Data pipeline | Load Successful?, Archive Source |
| 7 | `\b(book\|reserv\|flight\|hotel\|travel\|itinerary\|trip)\b` | Travel/Booking | Booking Confirmed?, Compare Alternatives |
| 8 | `\b(budget\|plan\b\|schedul\|allocat\|cost\s+estimate)\b` | Budget/Planning | Within Budget?, Review Plan |
| 9 | `\b(fetch\|load(?!\s+(?:to\|into)\b)\|read\|get\|query\|retrieve)\b` | Data retrieval | Data Found?, Transform Data |
| 10 | `\b(deploy\|release\|publish\|ship)\b` | Deployment | Run Health Check, Rollback on Failure |
| 11 | `\b(pay\|charge\|bill\|transact)\b` | Payment | Payment Successful?, Generate Receipt |
| 12 | `\b(test\|check\|verify\|assert)\b` | Testing | All Checks Pass?, Generate Report |

**Rule ordering matters**: ETL rule (6) must appear before data retrieval rule (9) so that "Load to Warehouse" matches ETL, not generic data retrieval. The read rule uses negative lookahead `load(?!\s+(?:to|into)\b)` to avoid matching ETL patterns.

## Decision Branch Logic

When the selected node is a decision type, `_decision_suggestions()` generates Yes/No branch labels via keyword matching:

| Keywords in Label | Yes Branch | No Branch |
|---|---|---|
| valid | Continue Processing | Show Validation Error |
| exist, found | Load Existing | Create New |
| approv | Apply Changes | Send Rejection |
| success | Confirm Success | Handle Error |
| stock, available | Reserve Items | Notify Unavailable |
| budget, cost, afford, price | Confirm Booking | Adjust Plans |
| 2fa, mfa, two-factor | Grant Access | Deny Access |
| auth, security, permission | Grant Access | Deny Access |
| test, pass | Continue Pipeline | Fix Issues |
| ready, complete, finish | Proceed | Review Again |
| correct, match | Accept | Revise |
| within, limit, threshold | Proceed | Adjust |
| connect, reachable, online | Continue | Retry Connection |

### Generic Fallback

When no keyword matches, `_extract_concept()` extracts the domain concept from the label:
- Strips punctuation and question marks
- Removes filler words (is, are, has, do, can, should, within, check, verify)
- Title-cases the remainder
- Produces: "Handle {Concept}" / "Resolve {Concept}"
- Example: "Within Budget?" → concept="Budget" → "Handle Budget" / "Resolve Budget"

If no concept can be extracted, falls back to "Process Result" / "Handle Failure".

## Confidence Levels

| Source | Confidence | Description |
|---|---|---|
| Decision Yes branch | 0.92 | High confidence for positive branch |
| Decision No branch | 0.91 | Slightly lower for negative branch |
| Auth patterns | 0.90, 0.78 | Well-established patterns |
| Validation patterns | 0.90, 0.75 | Standard validation flow |
| Start suggestions | 0.88, 0.85 | Initialization steps |
| ETL/Travel/Budget | 0.85, 0.72-0.75 | Domain-specific rules |
| Data retrieval | 0.85, 0.72 | Common data patterns |
| Leaf process generic | 0.60, 0.55, 0.45 | Low confidence, easily overridden by LLM |

## Deduplication

Results are deduplicated by label (case-insensitive). When duplicates exist, the highest-confidence suggestion wins. Final results are sorted by confidence descending.

## Integration with Pipeline

The `SuggestionEngine` calls `PatternLibrary.match()` first. If the top result has confidence >= 0.85 (the `_PATTERN_CONFIDENCE_THRESHOLD`), the engine returns immediately without graph analysis, cache lookup, RAG, or LLM call. This fast path handles ~68% of scenarios based on visualization testing.
