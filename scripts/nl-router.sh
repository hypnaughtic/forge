#!/usr/bin/env bash
# ==============================================================================
# Forge — Natural Language Intent Router
# ==============================================================================
# Classifies natural language input into one or more intents using
# keyword-based pattern matching (fast path, no AI needed).
#
# Input:  Natural language string (positional arg or stdin)
# Output: Comma-separated intents to stdout
#
# Intents: STATUS, COST, TEAM, MODE, STRATEGY, SNAPSHOT, START, STOP, GUIDE, ASK
#
# Usage: scripts/nl-router.sh "what is the status and cost?"
#        echo "what is the status" | scripts/nl-router.sh
set -euo pipefail

# Read input from argument or stdin
INPUT="${1:-}"
if [[ -z "$INPUT" && ! -t 0 ]]; then
    read -r -t 1 INPUT || true
fi

if [[ -z "$INPUT" ]]; then
    echo "ASK"
    exit 0
fi

# Lowercase for case-insensitive matching
INPUT_LOWER=$(echo "$INPUT" | tr '[:upper:]' '[:lower:]')

# Matched intent flags (bash 3 compatible — no associative arrays)
HAS_STATUS=0
HAS_COST=0
HAS_TEAM=0
HAS_SNAPSHOT=0
HAS_MODE=0
HAS_STRATEGY=0
HAS_START=0
HAS_STOP=0
HAS_GUIDE=0

# Known agent names for GUIDE detection
AGENT_NAMES="team-leader|architect|backend-developer|frontend-engineer|frontend-designer|frontend-developer|qa-engineer|devops-specialist|critic|research-strategist|researcher|strategist|security-tester|performance-engineer|documentation-specialist"

# Split on " and " / " & " to handle multi-intent requests
# Also handle comma-separated clauses
IFS=$'\n' read -d '' -ra SEGMENTS < <(echo "$INPUT_LOWER" | sed -E 's/ (and|&) /\n/g; s/, /\n/g' || true) || true

for segment in "${SEGMENTS[@]}"; do
    [[ -z "$segment" ]] && continue

    # SNAPSHOT patterns (check before STATUS to avoid "save progress" → STATUS)
    if [[ "$segment" =~ (snapshot|save.*(state|progress|current)|checkpoint|preserve|backup) ]]; then
        HAS_SNAPSHOT=1
    fi

    # STOP patterns (check before TEAM to avoid "shut down agents" → TEAM)
    if [[ "$segment" =~ (stop|shut.*down|pause.*work|pause.*all|end.*session|halt|terminate|quit) ]]; then
        HAS_STOP=1
    fi

    # START patterns (check before STATUS to avoid "kick off iteration" → STATUS)
    if [[ "$segment" =~ (start.*build|begin|kick.*off|launch|commence|start.*iteration|start.*project) ]]; then
        HAS_START=1
    fi

    # STATUS patterns — skip if already matched as SNAPSHOT or START context
    if [[ $HAS_SNAPSHOT -eq 0 && $HAS_START -eq 0 ]]; then
        if [[ "$segment" =~ (status|progress|how.*(going|doing)|what.*(happening|state)|iteration|blockers) ]]; then
            HAS_STATUS=1
        fi
    fi

    # COST patterns — include colloquial money references
    if [[ "$segment" =~ (cost|budget|spent|spending|expensive|price|billing|token.?usage|token.?count|how.*tokens|money|burned|burn.?rate) ]]; then
        HAS_COST=1
    fi

    # TEAM patterns — skip if already matched as STOP context (e.g., "shut down all agents")
    if [[ $HAS_STOP -eq 0 ]]; then
        if [[ "$segment" =~ (team[[:space:]]|agents[[:space:]]|members|who.*(working|assigned|active)|roster|crew|team$|agents$) ]]; then
            HAS_TEAM=1
        fi
    fi

    # MODE patterns — require word boundary: avoid "modern" matching "mode"
    if [[ "$segment" =~ (^mode[[:space:]]|[[:space:]]mode[[:space:]]|[[:space:]]mode$|switch.*mode|change.*mode|set.*mode|mvp|production.?ready|no.?compromise) ]]; then
        HAS_MODE=1
    fi

    # STRATEGY patterns
    if [[ "$segment" =~ (^strategy|switch.*strategy|change.*strategy|set.*strategy|auto.?pilot|co.?pilot|micro.?manage) ]]; then
        HAS_STRATEGY=1
    fi

    # GUIDE patterns (mentions a specific agent name with a directive)
    if echo "$segment" | grep -qE "(guide|tell|redirect|instruct|direct).*(${AGENT_NAMES})"; then
        HAS_GUIDE=1
    elif echo "$segment" | grep -qE "(${AGENT_NAMES}).*(should|must|need|use|switch|try|focus)"; then
        HAS_GUIDE=1
    fi
done

# Build result string (ordered by priority)
RESULT=""
append_intent() {
    if [[ -n "$RESULT" ]]; then
        RESULT="${RESULT},$1"
    else
        RESULT="$1"
    fi
}

[[ $HAS_STATUS -eq 1 ]]   && append_intent "STATUS"
[[ $HAS_COST -eq 1 ]]     && append_intent "COST"
[[ $HAS_TEAM -eq 1 ]]     && append_intent "TEAM"
[[ $HAS_MODE -eq 1 ]]     && append_intent "MODE"
[[ $HAS_STRATEGY -eq 1 ]] && append_intent "STRATEGY"
[[ $HAS_SNAPSHOT -eq 1 ]] && append_intent "SNAPSHOT"
[[ $HAS_START -eq 1 ]]    && append_intent "START"
[[ $HAS_STOP -eq 1 ]]     && append_intent "STOP"
[[ $HAS_GUIDE -eq 1 ]]    && append_intent "GUIDE"

# If no patterns matched, default to ASK
if [[ -z "$RESULT" ]]; then
    echo "ASK"
else
    echo "$RESULT"
fi
