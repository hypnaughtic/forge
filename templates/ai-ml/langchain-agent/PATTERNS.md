# LangChain Agent — Architectural Patterns

This document explains the patterns used in this template and **why** each
one was chosen. The most critical pattern is the llm-gateway routing — read
that section carefully.

---

## 1. llm-gateway Routing (CRITICAL)

**What:** All LLM calls are routed through llm-gateway, NOT through
LangChain's native provider classes (`ChatOpenAI`, `ChatAnthropic`, etc.).
The `GatewayLLM` class implements LangChain's `BaseChatModel` interface
and translates calls into llm-gateway HTTP requests.

**Why this pattern:**

- **Centralized control** — llm-gateway provides a single point for rate
  limiting, cost tracking, API key rotation, and model routing. Using
  LangChain's native providers bypasses all of this.
- **Audit trail** — Every LLM call flows through a gateway that logs
  request/response metadata, enabling cost attribution and compliance.
- **Model abstraction** — The gateway can route requests to different
  models based on load, cost, or capability without changing agent code.
- **Security** — API keys for LLM providers live in the gateway, not in
  application environment variables. Developers never see production keys.

**How it works:**

```python
# WRONG — bypasses llm-gateway:
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4")

# CORRECT — routes through llm-gateway:
from agent.gateway_llm import GatewayLLM
llm = GatewayLLM(model="gpt-4")  # Calls llm-gateway, not OpenAI directly
```

The `GatewayLLM` class:
1. Accepts LangChain message types (`HumanMessage`, `SystemMessage`, etc.)
2. Converts them to the llm-gateway request format
3. Sends the request to the gateway HTTP endpoint
4. Converts the gateway response back to LangChain's `AIMessage`

This makes the gateway invisible to the rest of the LangChain pipeline.

---

## 2. Agent-Tool Pattern (LangGraph)

**What:** The agent is a LangGraph state machine that decides which tools
to call, executes them, observes results, and decides next steps.

**Why this pattern:**

- **Controllability** — LangGraph gives explicit control over the agent
  loop. You define states, transitions, and termination conditions rather
  than relying on opaque ReAct loops.
- **Debuggability** — Each state transition is observable and loggable.
  You can trace exactly why the agent called a specific tool.
- **Error recovery** — States can include retry logic, fallbacks, and
  human-in-the-loop breakpoints that are hard to implement in simple
  chain-based agents.
- **Composability** — Sub-agents can be nodes in a larger graph, enabling
  multi-agent architectures without framework gymnastics.

---

## 3. LangGraph State Machines

**What:** Agent behavior is defined as a graph of states with typed state
objects and conditional edges.

**Why this pattern:**

- **Explicit flow** — The graph definition serves as documentation of
  the agent's decision logic. New developers can read the graph and
  understand the agent without tracing through runtime logs.
- **Type safety** — State objects are typed dataclasses/TypedDicts.
  Invalid state transitions are caught at definition time.
- **Persistence** — LangGraph supports checkpointing state to storage,
  enabling long-running agents that survive process restarts.

---

## 4. Memory Management

**What:** Conversation history is managed through LangGraph's state,
with configurable window sizes and summarization strategies.

**Why this pattern:**

- **Token budget control** — LLM context windows are finite. Unbounded
  history causes failures and high costs. Windowed memory keeps costs
  predictable.
- **Relevance** — Recent messages are more relevant than old ones.
  Summarization compresses old context without losing key information.
- **Separation from agent logic** — Memory management is a concern of
  the state graph, not individual tools or prompts.

---

## 5. Tool Design Principles

**What:** Tools are pure functions with clear docstrings, typed inputs,
and no side effects on agent state.

**Why this pattern:**

- **LLM comprehension** — The LLM reads tool docstrings and parameter
  descriptions to decide when and how to use each tool. Clear descriptions
  lead to better tool selection.
- **Testability** — Pure functions with typed inputs are trivially testable
  without mocking the agent or LLM.
- **Safety** — Tools that do not modify agent state cannot corrupt the
  agent loop. Side effects are managed by the graph, not by tools.
