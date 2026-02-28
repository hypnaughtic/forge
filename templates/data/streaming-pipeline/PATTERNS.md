# Streaming Pipeline Patterns

> These patterns describe architectural decisions for the streaming pipeline template. No implementation is provided in this stub.

## 1. Event Time Processing with Watermarks

**WHY:** Processing events by arrival time (processing time) produces incorrect results when events arrive out of order -- which is common in distributed systems. Event time processing with watermarks uses the event's actual timestamp, and watermarks signal when it is safe to emit results. This ensures correct aggregations even when network delays cause events to arrive late.

## 2. Exactly-Once via Checkpointing and Idempotent Sinks

**WHY:** Stream processing failures require reprocessing from the last consistent state. Periodic checkpoints snapshot operator state and Kafka offsets atomically. Combined with idempotent sinks (upsert to database, keyed writes), this achieves exactly-once end-to-end semantics without the performance cost of distributed transactions.

## 3. Windowed Aggregation with Late Data Policy

**WHY:** Real-time dashboards and alerts need aggregated metrics (counts, sums, averages) over time windows. Defining explicit late data policies (allow events up to N minutes late, update aggregation, then discard) balances accuracy with resource consumption. Without this, late events either break aggregations or accumulate state indefinitely.

## 4. Schema Registry for Stream Contracts

**WHY:** Producers and consumers of streaming data evolve independently. A schema registry enforces backward/forward compatibility at the serialization level, preventing a producer upgrade from breaking all downstream consumers. This is especially critical in streaming where reprocessing after a schema break can take hours.

## 5. Backpressure Propagation

**WHY:** When a sink is slower than the source, unbounded buffering leads to out-of-memory crashes. Flink and Spark propagate backpressure upstream, slowing the source to match the sink's capacity. Understanding and monitoring backpressure prevents the silent data loss and OOM failures that plague naive streaming implementations.
