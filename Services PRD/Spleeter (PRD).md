
---

# **Service 6: Spleeter — Complete Sub-Flow Breakdown (PRD)**

## **Spleeter Service: Functional Flows & Requirements**

### **A. Job Reception & Validation**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLEET-001|Receive staged job from Splitter-Stager with validated inputs|As a system, I want to process only fully prepared, contract-valid jobs.|Service only accepts jobs with valid input file, config, tags/art, job_uuid, user_id, and engine config.|
|SPLEET-002|Validate input format, model config, and resource availability|As a developer, I want to ensure Spleeter can run on all received jobs before starting processing.|If validation fails (e.g., missing model, bad config), job is rejected with error and moved to orphan/ or retried.|

### **B. Engine Processing & Resource Management**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLEET-003|Run Spleeter engine for configured stem separation|As a user, I want my file separated into the chosen stems (2/4/5 stems as configured).|Spleeter runs with user/system-selected config; outputs correct number/type of stems per job.|
|SPLEET-004|Support chunked/batched processing for large files|As a user, I want large files processed efficiently without OOM or timeouts.|Files exceeding threshold are split and processed in batches/chunks; outputs are reassembled if needed.|
|SPLEET-005|Dynamically enforce per-job resource (CPU, RAM, disk) limits|As an operator, I want to prevent Spleeter jobs from overusing system resources.|Spleeter respects configured resource quotas; jobs that exceed are throttled or failed gracefully with error surfaced.|
|SPLEET-006|Autoscale worker pool based on job queue and system resources|As an ops engineer, I want throughput to match demand, scaling up/down safely.|Spleeter workers autoscale based on in-queue job count, system CPU/RAM, and configured max/min limits.|

### **C. Health, Dependency, and Failure Handling**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLEET-007|Health check of engine, dependencies, and models|As an operator, I want to verify Spleeter and all dependencies/models are available and healthy.|`/health` endpoint and metrics show engine, model, and dependency status; failures/latency surfaced in logs/UI.|
|SPLEET-008|Surface all engine errors (model missing, runtime error, corrupt input) to Queue/UI|As a user/operator, I want actionable error messages if stem separation fails.|All errors are logged and propagated with explicit code, stage, and human-readable reason; UI shows failure and suggested remedy.|
|SPLEET-009|Retry policy for transient/infra errors (e.g., OOM, temp disk full)|As an operator, I want jobs retried for transient, non-permanent failures.|Retries are attempted with backoff for eligible failures (e.g., OOM, disk temp); persistent errors are marked as failed and surfaced.|

### **D. Output Handling, Atomicity, and Traceability**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLEET-010|Output stems written atomically and tagged with job_uuid, user_id|As a user, I want my output files never to be partial or lost on crash.|All output files are written/moved atomically, tagged, and checked for completeness before handoff.|
|SPLEET-011|Reassemble chunked output if batch/chunk processing used|As a user, I want my output as a single set of stems regardless of chunking.|Chunked outputs are reassembled seamlessly, preserving quality and timing; errors in reassembly are surfaced.|
|SPLEET-012|Handoff all output (stems, logs, status) to Audio-Recon or next stage|As a system, I want all downstream services to receive full context and trace of Spleeter results.|All output files, logs, config, and error state are passed on with job_uuid, engine version, and all trace tags.|

### **E. Observability, Metrics, and Alerts**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLEET-013|Structured logging for all actions (start, success, error, resource use)|As an operator, I want to trace every job, step, and error in Spleeter processing.|All actions/events are logged with full trace info and resource metrics (duration, CPU/RAM/disk used).|
|SPLEET-014|`/metrics` endpoint exposes throughput, failures, queue, and resource stats|As an ops engineer, I want detailed Prometheus metrics for Spleeter service.|Metrics include job counts, error rates, average latency, chunking events, OOMs, per-job resource use, etc.|
|SPLEET-015|Alert on repeated failures, high latency, or resource exhaustion|As an ops engineer, I want real-time alerts for Spleeter problems.|Configurable thresholds trigger alerts for high failure rates, job latency, or repeated OOM/resource errors.|

### **F. Security, Compliance, and Quotas**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|SPLEET-016|Enforce per-user/job quotas (CPU, RAM, concurrent jobs)|As an admin, I want no user/job to monopolize Spleeter processing resources.|Per-user/job quotas are checked before job start; over-quota jobs are queued, throttled, or failed.|
|SPLEET-017|Tag all outputs for GDPR, retention, and compliance|As a user, I want my outputs handled per legal/privacy policies.|All output files/logs are tagged; compliance/retention rules are enforced for later pruning/deletion.|

---

## **Spleeter Service — Complete Flow Diagram (Text)**

1. **Receives staged job** with validated inputs from Splitter-Stager.
    
2. Validates file, config, and resource availability; rejects invalid jobs to orphan/ with error.
    
3. Runs Spleeter with configured stem model (2/4/5 stems, etc.), using chunked/batch mode for large files.
    
4. Dynamically allocates resources, autoscaling workers as needed.
    
5. Handles OOMs, model errors, or infra issues with retries/backoff; logs all errors and actions.
    
6. Writes all outputs atomically, reassembling if chunked, with job_uuid/user_id and engine version tags.
    
7. Handoffs output to Audio-Recon (or next stage), logs success, and updates job state in Queue.
    
8. Exposes `/health` and `/metrics` for all status, resource, and queue stats.
    
9. Surfaces alerts/notifications on high failure, resource use, or repeated errors.
    
10. Fully enforces per-user quotas, GDPR, and compliance on all outputs.
    

---