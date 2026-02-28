# Data API Patterns

> These patterns describe architectural decisions for the data API template. No implementation is provided in this stub.

## 1. dbt Mart Models as API Contract

**WHY:** Exposing raw warehouse tables through an API couples consumers to internal schema details that change frequently. Using dbt mart (gold layer) models as the API data source provides a stable, documented interface. dbt's model contracts enforce output schemas, so API consumers are protected from upstream schema drift.

## 2. Query Result Caching with Freshness Metadata

**WHY:** Data warehouse queries are expensive and analytics data does not need real-time freshness. Caching query results in Redis with TTLs aligned to the dbt refresh schedule eliminates redundant warehouse load. Including a `data_freshness` timestamp in API responses lets consumers decide if the data is fresh enough for their use case.

## 3. API Key Scoping with Column-Level Access

**WHY:** Different API consumers need different data access levels. A marketing partner should not see financial data even if it is in the same mart model. Scoping API keys to specific models and columns prevents unauthorized data access at the API layer, independent of warehouse-level permissions.

## 4. Async Query Execution for Large Results

**WHY:** Some analytical queries return millions of rows and take minutes to execute. Blocking HTTP requests for these queries causes timeouts. An async pattern (submit query, receive job ID, poll for results, download from object storage) handles large results gracefully while keeping the API responsive for small queries.

## 5. Warehouse Connection Pooling with Circuit Breaker

**WHY:** Data warehouses have limited concurrent query slots. Without connection pooling, a traffic spike can exhaust connections and cause cascading failures. A connection pool with a circuit breaker pauses new queries when the warehouse is overloaded, returning fast errors instead of slow timeouts.
