# Kafka Microservice Patterns

> These patterns describe architectural decisions for the Kafka microservice template. No implementation is provided in this stub.

## 1. Schema Registry for Contract Evolution

**WHY:** When producers and consumers are developed by different teams, message format changes can silently break consumers. Schema Registry enforces compatibility rules (backward, forward, full) at the broker level, rejecting messages that violate the contract. This shifts breaking changes from runtime failures to deployment-time rejections.

## 2. Dead Letter Queue for Poison Messages

**WHY:** A malformed or unprocessable message can block an entire consumer group partition if the consumer crashes on retry. Routing failed messages to a dead letter topic after exhausting retries allows the consumer to continue processing while preserving the failed message for investigation and manual reprocessing.

## 3. Idempotent Consumer Processing

**WHY:** Kafka guarantees at-least-once delivery, meaning consumers may receive the same message multiple times during rebalances or retries. Designing consumer handlers to be idempotent (using message ID deduplication or upsert operations) prevents duplicate side effects like double-charging or duplicate notifications.

## 4. Partition-Aware Processing

**WHY:** Kafka parallelism is bounded by partition count. Choosing partition keys that align with processing requirements (e.g., customer ID for ordered per-customer processing) ensures related events are processed sequentially within a partition while maximizing parallelism across partitions.

## 5. Transactional Outbox Pattern

**WHY:** Producing a Kafka message and committing a database transaction are two separate operations that can partially fail. The outbox pattern writes events to a database table within the same transaction, and a separate process publishes them to Kafka, ensuring exactly-once semantics between the database and the message broker.
