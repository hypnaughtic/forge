# Temporal Workflow Patterns

> These patterns describe architectural decisions for the Temporal workflow template. No implementation is provided in this stub.

## 1. Saga Pattern with Compensating Transactions

**WHY:** Distributed transactions across multiple services cannot use traditional ACID semantics. The saga pattern executes a sequence of local transactions, and if any step fails, runs compensating actions in reverse order to undo previous steps. Temporal makes this reliable because the compensation logic survives worker crashes and restarts.

## 2. Deterministic Workflow Code

**WHY:** Temporal replays workflow history to rebuild state after worker restarts. If workflow code uses non-deterministic operations (random numbers, current time, external calls), replay produces different results and the workflow breaks. Isolating all non-deterministic operations in activities ensures workflows replay correctly every time.

## 3. Activity Retry with Non-Retryable Error Classification

**WHY:** Not all errors should be retried. A network timeout should be retried, but a validation error will fail forever. Classifying errors as retryable or non-retryable prevents wasted compute on impossible retries while ensuring transient failures are automatically resolved. Temporal's retry policy respects these classifications out of the box.

## 4. Signal-Based External Event Handling

**WHY:** Long-running workflows often need to react to external events (payment received, approval granted, webhook callback). Temporal signals deliver these events to the workflow without polling, and the workflow can wait for multiple signals with timeouts. This is far more efficient and reliable than polling databases or external APIs.

## 5. Workflow Versioning for Safe Deploys

**WHY:** Changing workflow code while instances are running can break replay. Temporal's versioning API allows new code paths to be introduced alongside old ones, routing existing workflow instances through their original code path and new instances through the updated path. This enables zero-downtime deployments of workflow logic.
