
---

# **Service 14: pipelinectl / CLI — Complete Sub-Flow Breakdown (PRD)**

## **pipelinectl / CLI Service: Functional Flows & Requirements**

### **A. Job Management (Submission, Retry, Prune, Restore)**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CLI-001|Submit new job(s) from CLI with config, file(s), and metadata|As a developer/operator, I want to queue jobs for processing directly from the CLI.|Command supports local file path(s), engine selection, metadata/art override, and shows job_uuid/status for each submission.|
|CLI-002|Retry or replay failed jobs, by job_uuid or filter|As a user or admin, I want to easily retry/replay failed or stuck jobs via CLI.|Retry command allows single job or bulk (by filter: user, status, date); provides clear output for each retry attempt.|
|CLI-003|Prune old/orphaned/error files and outputs (with dry-run support)|As an operator, I want to clean up storage safely, previewing all changes.|Prune command lists affected files/jobs (dry-run by default), supports actual delete with confirmation and logs outcome.|
|CLI-004|Restore jobs or data from backup (with checks and confirmation)|As an operator, I want to restore lost jobs/data from backup safely, with audit trail.|Restore command checks available backups, supports preview/confirmation, and logs all changes and restores for audit.|

### **B. Pipeline Control and Health**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CLI-005|Pause and resume the entire pipeline (for upgrades or emergencies)|As an operator, I want to safely pause/resume all job processing.|Commands pause or resume pipeline at queue level, with real-time feedback and confirmation before action.|
|CLI-006|Query status and health of all services (summary and per-service)|As a developer/operator, I want to check the live status and health of all pipeline components.|Status command shows overall health, plus detailed view per service: up/down, last error, queue depth, resource usage, etc.|
|CLI-007|Upgrade and migration commands for schema, config, and services|As an operator, I want to safely upgrade pipeline components and database schema.|CLI supports migrate/rollback (with dry-run), and upgrade commands, all logged and version-checked before action.|
|CLI-008|Canary, test, and dry-run job flows|As a developer, I want to run test jobs or dry-run migrations before affecting production.|CLI supports canary/test job queues and dry-run for upgrades/migrations, showing what will happen before action.|

### **C. Diagnostics, Logs, and Support**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CLI-009|Download full diagnostic bundle for any job (logs, traces, state)|As a user/support, I want all info for troubleshooting or support review.|Diagnostic command fetches logs, job state, and related artifacts for any job_uuid, outputs as single bundle (zip/tar).|
|CLI-010|Search/query logs by job_uuid, user_id, or trace_id (with filters)|As a developer/operator, I want fast, flexible log searches across all pipeline logs.|Search command supports filters, regular expressions, and outputs JSON/summary/table format as needed.|
|CLI-011|View all API docs, schemas, and version info from CLI|As a developer, I want up-to-date docs and schema/version reference locally.|Docs command fetches and displays OpenAPI, schemas, and version info, auto-updating as pipeline upgrades.|

### **D. Authentication, Permissions, and Audit**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CLI-012|Support RBAC, per-user, and API token auth (configurable per command)|As an admin, I want to control CLI access for different users and roles.|CLI commands require API token/auth, enforce RBAC per user/command, and refuse unauthorized actions with clear error.|
|CLI-013|All CLI actions logged/auditable (who, what, when, result)|As an operator, I want every command to be logged for audit/security.|Every command, its options, actor, and result is logged centrally (optionally to SIEM/monitoring).|

### **E. Developer Experience and Help**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CLI-014|One-command dev up: start full pipeline locally for dev/test|As a developer, I want to spin up a local environment easily.|`pipelinectl up` (or similar) spins up all core services locally, with health-check and log tail.|
|CLI-015|Auto-complete, contextual help, and inline documentation for all commands|As a user, I want to discover and learn CLI usage easily.|CLI supports shell autocomplete, `--help` for every command, and inline docs/examples.|
|CLI-016|Output machine-readable (JSON/YAML) or human-readable (table/text) formats|As an integrator, I want to script CLI outputs or view them in the terminal.|All commands support JSON/YAML output flags and default to table/text for interactive use.|

### **F. Accessibility and Internationalization**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CLI-017|CLI text and outputs structured for i18n and a11y|As a user in any locale or with assistive tech, I want to use the CLI with ease.|Output messages and help are externalized and formatted for screen readers and locale conventions.|

---

## **pipelinectl / CLI — Complete Flow Diagram (Text)**

1. **Job Management:** submit jobs, retry/replay failures, prune or restore data (all with dry-run and confirmation).
    
2. **Pipeline Control:** pause/resume processing, upgrade/migrate schema/config, run canary/test/dry-run jobs.
    
3. **Diagnostics & Logs:** fetch diagnostic bundles, search logs by id or filter, view current docs/schemas.
    
4. **Auth & Audit:** enforce RBAC/API token auth per command; all actions centrally logged and auditable.
    
5. **Dev UX:** one-command local up; autocomplete/help/docs; supports machine/human-readable output; all a11y/i18n ready.
    

---