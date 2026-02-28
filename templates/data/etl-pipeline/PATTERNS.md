# ETL Pipeline Patterns

> These patterns describe architectural decisions for the ETL pipeline template. No implementation is provided in this stub.

## 1. Medallion Architecture (Bronze/Silver/Gold)

**WHY:** Loading raw data directly into analytics tables makes debugging impossible when transformations produce incorrect results. The medallion pattern stages data in layers: bronze (raw), silver (cleaned/conformed), gold (business-ready). Each layer is independently queryable, making it easy to trace data issues back to the source and re-run only the affected transformation layer.

## 2. Idempotent Incremental Loads

**WHY:** Full table reloads are expensive and slow as data grows. Incremental loads that process only new/changed records based on watermarks (timestamps, sequence IDs) are efficient but must be idempotent -- re-running the same increment should produce the same result. Using MERGE/upsert operations ensures correctness even when a pipeline is restarted mid-load.

## 3. dbt Model Contracts with Tests

**WHY:** SQL transformations can silently produce wrong results (NULL joins, type coercions, duplicate rows). dbt tests (unique, not_null, relationships, accepted_values) run after each model, catching data quality issues before they propagate to downstream dashboards. Model contracts enforce output schemas, preventing breaking changes to consumers.

## 4. Orchestrator-Managed Backfills

**WHY:** When a transformation bug is fixed, all historically affected data must be reprocessed. Orchestrators like Airflow provide backfill commands that re-run DAG runs for specific date ranges with proper dependency ordering, avoiding the manual error-prone process of running individual scripts in the correct sequence.

## 5. Data Lineage for Impact Analysis

**WHY:** When a source system changes a column, teams need to know which downstream tables, dashboards, and reports are affected. Automated lineage tracking (from dbt's ref() graph and orchestrator task dependencies) provides this visibility, turning a multi-day investigation into a quick graph query.
