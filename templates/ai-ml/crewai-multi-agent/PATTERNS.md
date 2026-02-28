# CrewAI Multi-Agent Patterns

> These patterns describe architectural decisions for the CrewAI multi-agent template. No implementation is provided in this stub.

## 1. LLM-Gateway as Exclusive Model Interface

**WHY:** CrewAI agents make many LLM calls during reasoning. Routing all calls through llm-gateway provides centralized rate limiting, cost tracking, and model switching. If an agent's reasoning loop becomes expensive, the gateway can enforce per-agent budgets. This also enables swapping models (e.g., using a cheaper model for simple agents) without code changes.

## 2. Role-Based Agent Specialization

**WHY:** General-purpose agents produce mediocre results across all tasks. Defining agents with narrow roles (Researcher, Analyst, Writer) and specific goals focuses each agent's reasoning on what it does best. Specialized system prompts and tool access per role improve output quality and reduce token waste from irrelevant reasoning.

## 3. Hierarchical Task Delegation

**WHY:** Complex tasks benefit from a manager agent that decomposes work and delegates to specialist agents, similar to how human teams operate. This pattern prevents individual agents from becoming overwhelmed with context and allows the manager to route subtasks to the most appropriate specialist based on the work required.

## 4. Structured Output Contracts

**WHY:** Agents passing free-form text between each other leads to information loss and parsing failures. Defining Pydantic models as output contracts for each task ensures downstream agents receive structured, validated data. This makes multi-agent pipelines reliable and debuggable, since each handoff point has a clear schema.

## 5. Configuration-Driven Agent Composition

**WHY:** Hardcoding agent configurations in Python makes experimentation slow. Defining agents, tasks, and crews in YAML configuration files allows non-developers to tune agent behavior, swap roles, and adjust task ordering without code changes. This separates the orchestration logic from the agent engineering.
