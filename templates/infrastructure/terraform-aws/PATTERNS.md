# Terraform AWS Patterns

> These patterns describe architectural decisions for the Terraform AWS template. No implementation is provided in this stub.

## 1. Composable Module Architecture

**WHY:** Monolithic Terraform configurations become unmaintainable as infrastructure grows. Breaking infrastructure into small, independently versioned modules (networking, compute, database, monitoring) allows teams to modify one component without risking changes to others. Module composition through outputs and inputs creates a clear dependency graph.

## 2. Remote State with Locking

**WHY:** Local Terraform state files cannot be shared across a team and have no concurrency protection. Remote state in S3 with DynamoDB locking ensures the entire team works from the same infrastructure truth and prevents two engineers from applying conflicting changes simultaneously, which could corrupt infrastructure.

## 3. Environment Parity with Variable Separation

**WHY:** Infrastructure differences between environments are the top cause of "works in staging, breaks in production" incidents. Using identical module code across environments with only variable files (instance sizes, replica counts, feature flags) differing ensures structural parity while allowing appropriate resource scaling per environment.

## 4. Least-Privilege IAM with Policy Boundaries

**WHY:** Over-permissioned IAM roles are the most common AWS security vulnerability. Defining granular IAM policies per service (each Lambda, ECS task, etc.) with permission boundaries prevents lateral movement if a single component is compromised. This is tedious upfront but prevents catastrophic security incidents.

## 5. Plan-on-PR, Apply-on-Merge Workflow

**WHY:** Applying infrastructure changes without review risks production outages. Running `terraform plan` on pull requests shows exactly what will change, enabling code review of infrastructure changes. Applying only after merge to main ensures all changes are reviewed, approved, and tracked in version control.
