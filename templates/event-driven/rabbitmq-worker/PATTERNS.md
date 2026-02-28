# RabbitMQ Worker Patterns

> These patterns describe architectural decisions for the RabbitMQ worker template. No implementation is provided in this stub.

## 1. Explicit Acknowledgment with Prefetch Control

**WHY:** Auto-acknowledgment removes messages from the queue before processing completes, risking data loss on worker crashes. Manual acknowledgment (ack after processing) combined with prefetch limits (one message at a time per worker) ensures no message is lost and prevents fast producers from overwhelming slow consumers.

## 2. Exchange-Based Routing Topology

**WHY:** Directly publishing to queues tightly couples producers to consumers. Using exchanges with routing keys decouples message producers from the number and identity of consumers. Adding a new consumer for the same event type requires only a new queue binding, not a producer code change.

## 3. Task Idempotency with Deduplication

**WHY:** RabbitMQ's at-least-once delivery means tasks may execute more than once during network partitions or worker restarts. Assigning a unique task ID and checking for prior completion before processing ensures duplicate deliveries do not cause duplicate side effects like sending the same email twice.

## 4. Priority Queue Segregation

**WHY:** Mixing high-priority tasks (password reset emails) with low-priority tasks (analytics updates) in the same queue means urgent tasks wait behind a backlog. Separate queues with dedicated workers for each priority level ensure time-sensitive tasks are processed immediately regardless of overall system load.

## 5. Circuit Breaker for Downstream Dependencies

**WHY:** When a worker's downstream dependency (database, API) is down, retrying every message wastes resources and floods the dependency with failing requests. A circuit breaker pauses consumption when failures exceed a threshold, allowing the dependency to recover before resuming, and routes messages to a retry queue with delay.
