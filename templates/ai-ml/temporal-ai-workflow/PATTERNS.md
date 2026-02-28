# Temporal AI Workflow Patterns

> These patterns describe architectural decisions for the Temporal AI workflow template. No implementation is provided in this stub.

## 1. Activities as LLM-Gateway Wrappers (Never Direct LLM Calls in Workflows)

**WHY:** Temporal workflows must be deterministic -- they replay from history on recovery. LLM calls are inherently non-deterministic (different responses each time). By isolating all LLM interactions in activities that call llm-gateway, the workflow remains replayable while activities handle the non-deterministic external calls with proper retry semantics.

## 2. Pipeline Stage Decomposition

**WHY:** Breaking an AI pipeline into discrete Temporal activities (retrieve, augment, generate, validate, post-process) allows each stage to have independent retry policies, timeouts, and scaling characteristics. A slow embedding call does not block a fast classification step, and failures in one stage can trigger targeted recovery without re-running the entire pipeline.

## 3. LLM-Gateway as Single Model Interface

**WHY:** Routing all model calls through llm-gateway provides a centralized point for rate limiting, cost tracking, model switching, and API key management. When a model provider has an outage, traffic can be rerouted at the gateway without modifying any workflow code. This also enables A/B testing between models transparently.

## 4. Human-in-the-Loop via Temporal Signals

**WHY:** AI pipelines often need human review before taking consequential actions (approving generated content, confirming financial decisions). Temporal signals allow workflows to pause indefinitely waiting for human input without consuming resources, and the workflow resumes exactly where it left off -- even if the approval takes days.

## 5. Cost-Aware Execution with Activity Heartbeats

**WHY:** LLM calls are expensive. Activity heartbeats allow long-running model calls to report progress and be cancelled early if the workflow is abandoned. Combined with llm-gateway cost tracking, this prevents runaway spending from forgotten or stuck pipelines.
