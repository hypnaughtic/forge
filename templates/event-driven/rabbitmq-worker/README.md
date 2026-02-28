# RabbitMQ Worker Template (STUB)

> **Status:** Stub template -- not yet scaffolded. This document describes what a full implementation would provide.

## Overview

An event-driven worker service using RabbitMQ as the message broker, with Celery for task management in Python or a similar pattern in TypeScript. Supports reliable message processing with acknowledgments, retries, and priority queues.

## What a Full Scaffold Would Provide

- **RabbitMQ consumer** with durable queues and manual acknowledgment
- **Celery integration** (Python) with task routing and priority queues
- **Exchange topologies** (direct, topic, fanout) for message routing
- **Retry logic** with exponential backoff and max retry limits
- **Dead letter exchange** for failed message inspection
- **Task chaining and grouping** for complex workflows
- **Rate limiting** per-task and per-queue
- **Monitoring** with Flower (Celery) and RabbitMQ Management UI
- **Graceful shutdown** with in-flight task completion
- **Health checks** based on broker connection and queue depth
- **Docker Compose** with RabbitMQ, workers, and monitoring
- **Testing** with mocked broker and task assertions

## Key Technologies

| Component       | Python             | TypeScript         |
|----------------|--------------------|--------------------|
| Broker          | RabbitMQ           | RabbitMQ           |
| Task Framework  | Celery             | amqplib/bullmq     |
| Monitoring      | Flower             | RabbitMQ Mgmt      |
