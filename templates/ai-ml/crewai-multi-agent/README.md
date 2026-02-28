# CrewAI Multi-Agent Template (STUB)

> **Status:** Stub template -- not yet scaffolded. This document describes what a full implementation would provide.

## Overview

A multi-agent AI system built with CrewAI, using llm-gateway for all model interactions. Agents collaborate on complex tasks through defined roles, goals, and tool access. All LLM calls are routed through llm-gateway for centralized management.

## What a Full Scaffold Would Provide

- **CrewAI agent definitions** with specialized roles and goals
- **Task orchestration** with sequential and hierarchical execution
- **llm-gateway integration** for all model calls (no direct API usage)
- **Custom tools** for agents (web search, code execution, data retrieval)
- **Memory systems** (short-term, long-term, entity memory)
- **Output parsing** with structured Pydantic models
- **Callback handlers** for monitoring agent interactions
- **Configuration-driven** agent and task definitions via YAML
- **Testing** with mocked llm-gateway responses
- **Logging** of agent reasoning chains for debugging
- **Cost tracking** per agent and per task via llm-gateway metrics

## Key Technologies

| Component       | Technology          |
|----------------|---------------------|
| Framework       | CrewAI              |
| LLM Access      | llm-gateway         |
| Language        | Python              |
| Output Parsing  | Pydantic            |
| Configuration   | YAML                |

## Important Constraint

All model calls go through llm-gateway. Agents NEVER call LLM APIs directly.
