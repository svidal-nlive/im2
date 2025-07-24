
---

# **Service 2: Categorizer — Complete Sub-Flow Breakdown (PRD)**

## **Categorizer Service: Functional Flows & Requirements**

### **A. Input Reception & Validation**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CAT-001|Accept atomic job handoff from Watcher (with job marker/metadata)|As a system, I want to receive new jobs only when input files are stable, atomic, and traceable.|Categorizer only processes jobs with valid, complete markers and metadata (job_uuid, user_id, trace_id, file path/type).|
|CAT-002|Validate file type, extension, size against allowed list|As a developer, I want to ensure only supported files enter the pipeline, for security and integrity.|Files not matching allowed extensions/types/sizes are rejected with explicit error code and reason.|
|CAT-003|Validate directory structure and job ownership|As an admin, I want to ensure every job is associated with the correct user/job structure.|Jobs with missing/malformed user_id/job_uuid structure are rejected and surfaced as errors.|

### **B. Classification & Ordering**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CAT-004|Classify file by type, content, and user configuration|As a user, I want my files classified for appropriate downstream processing (audio, unsupported, etc).|Files are categorized as valid audio, unsupported format, or flagged for manual review.|
|CAT-005|Preserve original arrival/order from Watcher|As a user, I want my files processed in the order they were uploaded/detected.|Jobs maintain original order based on marker timestamps or watcher arrival records.|
|CAT-006|Allow configuration of per-user or per-job categorization rules|As an admin, I want to customize file acceptance/ordering logic.|Categorizer supports config overrides for specific users/jobs (e.g., file type whitelist/blacklist).|

### **C. Atomic Queue Insertion**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CAT-007|Insert valid jobs atomically into Queue service|As a developer, I want queue insertion to be atomic, to prevent duplication or race conditions.|Each job is inserted into Queue only once, with explicit transaction/acknowledgement.|
|CAT-008|Return immediate feedback on success/failure|As a system/user, I want to know if a job was successfully queued or rejected, with reason.|Categorizer responds synchronously to watcher or logs outcome for UI.|

### **D. Error Handling & Feedback**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CAT-009|Standardized error codes and typed contract enforcement|As a developer, I want all categorization errors mapped to codes and contract violations tracked.|Errors surfaced in logs, API, and UI; each error includes code, reason, and suggested action.|
|CAT-010|Surface all rejection/failure events to UI and logs|As a user, I want to see why my file was rejected immediately.|Failed categorizations are visible in UI with actionable feedback and trace_id/job_uuid.|
|CAT-011|Quarantine/reject files with security or compliance issues|As a compliance officer, I want to ensure unsafe or restricted files do not enter processing.|Files failing compliance (e.g., AV, blacklist) are quarantined, logged, and reported with reason.|

### **E. Idempotency, Deduplication & Replay**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CAT-012|Detect and ignore duplicate job submissions|As a user, I want to avoid accidental double-processing of the same file.|Duplicate files/job_uuids are recognized; categorizer skips or rejects with duplicate error code.|
|CAT-013|Idempotent re-processing after crash/retry|As an operator, I want categorizer to safely re-process after restart or failure, without duplicate or lost jobs.|Categorizer can replay/restore previous state and ensure each valid file is processed exactly once.|

### **F. Observability, Metrics & Health**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CAT-014|Structured logging with job_uuid/user_id/trace_id|As an operator, I want all actions and errors to be fully traceable.|Every categorizer event is logged in structured JSON with all IDs.|
|CAT-015|`/health` and `/metrics` endpoints|As an operator, I want to monitor service health and job stats.|Health/metrics endpoints expose job throughput, errors, queue insertions, and rejection rates.|
|CAT-016|Surface slow categorization or bottlenecks|As an ops engineer, I want to detect if categorizer is falling behind or overloaded.|Metrics/reporting includes processing time and backlog/waiting jobs.|

### **G. Security, Compliance & Abuse Protection**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|CAT-017|Rate limiting/throttling for per-user submissions|As an admin, I want to limit the rate of jobs categorized per user to prevent abuse.|Categorizer enforces per-user rate limits and returns throttling errors as needed.|
|CAT-018|Tag and enforce privacy/compliance attributes on jobs|As a compliance officer, I want jobs tagged for privacy/legal requirements (GDPR, etc).|Categorizer attaches compliance/privacy tags for downstream enforcement and reporting.|

---

## **Categorizer Service — Complete Flow Diagram (Text)**

1. **Receives job from Watcher** with complete marker/metadata.
    
2. Validates file type, size, extension, and user/job folder structure.
    
3. Runs compliance/security checks (AV, whitelist, blacklist).
    
4. Classifies file for further processing (audio, unsupported, flagged).
    
5. Preserves original arrival/order for queue insertion.
    
6. Atomically inserts valid job into Queue.
    
7. Logs all actions, including reason for any rejection.
    
8. Returns success/failure to Watcher (or logs for UI).
    
9. Exposes health/metrics endpoints for observability.
    
10. Replays/recovers previous jobs on crash or restart, ensuring idempotency.
    
11. Enforces per-user rate limits and compliance tagging.
    

---