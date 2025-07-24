
---

# **Service 5: Splitter-Stager — Complete Sub-Flow Breakdown (PRD)**

## **Splitter-Stager Service: Functional Flows & Requirements**

### **A. Input Reception & Validation**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLIT-001|Receive job from Queue with enriched metadata|As a system, I want each job’s file and all required metadata/artwork ready for engine staging.|Service receives file path, job_uuid, user_id, engine config, and normalized tags/art from previous stages.|
|SPLIT-002|Validate input file, metadata, and engine selection|As a developer, I want to ensure all required fields/configs are present and valid before staging.|Job is only staged if input, metadata, and selected engine(s) pass strict validation; errors surfaced to Queue/UI.|

### **B. Engine-Agnostic Staging & Plugin Interface**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLIT-003|Support multiple engines (Spleeter, Demucs, plugins)|As a user/admin, I want to select my preferred separation engine for each job.|Stager supports Spleeter, Demucs, and future plugin engines, configurable per job/user/system.|
|SPLIT-004|Plugin interface for new/third-party separation engines|As an integrator, I want to add new separation engines with minimal code changes.|Plugins implement a documented interface; contract tests enforce compliance and proper staging.|
|SPLIT-005|Per-job/per-user engine selection logic|As a user, I want my jobs to always use my selected or default separation engine.|Each job’s config is honored for engine selection; stager falls back to system default if none specified.|

### **C. Idempotency, Partial/Orphan Handling & Recovery**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLIT-006|Idempotent staging (safe to retry/replay after failure/crash)|As an operator, I want staging to be repeatable without risk of duplicate work or data loss.|Staging process is idempotent; repeated requests for the same job never create duplicate or partial work.|
|SPLIT-007|Scan for and cleanup partial/orphan staging artifacts|As an operator, I want abandoned/incomplete stages detected and cleaned up on schedule.|Partial/orphan files from interrupted jobs are detected and pruned regularly, with logs/audit.|
|SPLIT-008|Resume/retry from partial or interrupted state|As a system, I want to resume staging if a crash/interruption occurs, not restart from scratch.|Upon restart or retry, staging resumes from last good checkpoint; no duplicate or skipped files.|

### **D. Chunking & Resource Management**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLIT-009|Support chunked staging for large files|As a user, I want large audio files handled efficiently without memory/execution errors.|Large files are split and staged in chunks for downstream engine processing.|
|SPLIT-010|Enforce resource limits per staging job (CPU, RAM, disk)|As an operator, I want to ensure no staging job overwhelms system resources.|Each job’s resource use is monitored and enforced; jobs exceeding limits are throttled, split, or failed with clear error.|

### **E. Contract, Versioning & Compliance**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLIT-011|Versioned contract for all staged job artifacts|As a developer, I want downstream engines to receive predictable, versioned input every time.|All artifacts (files, configs, metadata) are versioned; downstream services validate contract/version before proceeding.|
|SPLIT-012|Tag staged artifacts with job_uuid, user_id, engine, and version|As an admin, I want full traceability for every staged file and config.|Every staged item carries full trace info; logs and audit trail are complete and accessible.|

### **F. Handoff to Engine (Spleeter/Demucs/Plugin) & Atomicity**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLIT-013|Atomic handoff to selected engine’s input directory/queue|As a system, I want only fully prepared, valid jobs sent to the splitter engine.|Handoff occurs only after all staging checks pass; atomic move/queue-insert prevents partial/incomplete jobs downstream.|
|SPLIT-014|Confirm handoff and update job state in Queue|As a developer, I want positive confirmation that jobs have transitioned to the next stage.|Stager records and logs each successful handoff; job state updated and surfaced to monitoring.|
|SPLIT-015|Remove or quarantine staged artifacts for failed jobs|As an operator, I want to prevent “dead” staged files from building up.|Failed or abandoned jobs have staged artifacts moved to orphan/ with error codes and traceability for later cleanup.|

### **G. Error Handling, Observability & Health**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLIT-016|Surface all staging and handoff errors to Queue/UI with reason|As a user, I want clear feedback if staging fails (e.g., missing engine, bad file).|Errors are logged, surfaced in UI, and attached to job state with code and actionable reason.|
|SPLIT-017|Structured, centralized logging for all actions|As an operator, I want traceable logs for all staging steps and errors.|All events/actions logged with job_uuid, user_id, engine, and contract version.|
|SPLIT-018|`/health` and `/metrics` endpoints for monitoring|As an operator, I want to monitor staging queue, chunking, resource use, and error rates.|Endpoints show in-progress jobs, throughput, error types, orphan count, etc.|
|SPLIT-019|Alert/notification on repeated staging failures or resource limits|As an ops engineer, I want to be notified about repeated errors or jobs exceeding limits.|Configurable thresholds trigger alerts; notifications include job context and error type.|

### **H. Security & Compliance**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLIT-020|Enforce AV scan and path whitelist on staged files|As a security admin, I want only safe, validated files staged for processing.|All files are AV-scanned and path-checked before staging; failures quarantined and logged.|
|SPLIT-021|Respect per-user/job quotas during staging|As an admin, I want to prevent users from over-consuming staging resources.|Staging enforces per-user/job limits; violations rejected with clear error.|

---

## **Splitter-Stager Service — Complete Flow Diagram (Text)**

1. **Receives job** from Queue with file path, metadata, engine config.
    
2. Validates all input fields, AV/path checks, and user/engine config.
    
3. Prepares staging: copies/symlinks file, writes config, normalizes tags/art, applies engine plugin if needed.
    
4. Supports chunking for large files; enforces per-job resource limits.
    
5. Handles Spleeter, Demucs, or plugin engine—using contract-validated interfaces for each.
    
6. Ensures staging is idempotent; retries are safe, orphans from failed runs detected and cleaned up.
    
7. On successful staging, atomically hands off to selected engine’s input (directory or queue).
    
8. On error or failure, surfaces clear error and moves all staged files to orphan/ with traceability.
    
9. Updates job state in Queue, logs all actions/events.
    
10. Exposes `/health` and `/metrics` endpoints for full monitoring.
    
11. Alerts on repeated failures, resource exhaustion, or contract violations.
    
12. Fully enforces compliance, AV, and per-user resource quotas.
    

---