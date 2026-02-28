# ML Model Serving Patterns

> These patterns describe architectural decisions for the ML model serving template. No implementation is provided in this stub.

## 1. Shadow Deployment for A/B Testing

**WHY:** Deploying a new model version to 100% of traffic is risky -- subtle accuracy regressions may only appear at scale. Shadow deployment routes a configurable percentage of traffic to the challenger model while the champion serves all responses. This collects real-world performance data for the new model without impacting users until confidence is established.

## 2. Model Hot-Swap with Health Gating

**WHY:** Restarting the inference server to load a new model causes downtime. Loading the new model in a background thread and atomically swapping the reference only after validation passes ensures zero-downtime deployments. The health endpoint reflects readiness state so load balancers do not route traffic during the transition.

## 3. Request Queuing with Backpressure

**WHY:** GPU inference is a bounded resource. Accepting unlimited concurrent requests leads to OOM errors or degraded latency for all requests. A bounded request queue with configurable concurrency limits ensures predictable latency and returns fast 503 responses when capacity is exceeded, letting the load balancer route to another instance.

## 4. Preprocessing Pipeline as Middleware

**WHY:** Model inputs often require normalization, tokenization, or feature engineering that should not live inside the model itself. Implementing preprocessing as composable middleware steps makes the pipeline testable, allows preprocessing to be shared across model versions, and keeps the model artifact focused on inference.

## 5. Prediction Logging for Drift Detection

**WHY:** Model accuracy degrades over time as real-world data distribution shifts. Logging every prediction (input features, output, confidence) to a data store enables offline drift detection, retraining triggers, and audit trails -- which are required for regulated industries and essential for maintaining model quality.

## 6. LLM Inference via llm-gateway

**WHY:** When serving LLM-based models (text generation, embeddings, chat), all inference calls must route through the project's `llm-gateway` plugin rather than calling vendor SDKs directly. This ensures vendor-agnostic model access, centralized cost tracking, rate limit handling, and the ability to switch providers without changing serving code. Traditional ML models (sklearn, PyTorch classification/regression) do not require llm-gateway.
