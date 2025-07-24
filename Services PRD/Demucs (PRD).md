
---

# **Service 7: Demucs — Complete Sub-Flow Breakdown (PRD)**

## **Demucs Service: Functional Flows & Requirements**

### **A. Job Reception & Validation**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|DEMUCS-001|Receive staged job from Splitter-Stager, validated against Demucs requirements|As a system, I want Demucs jobs to be ready-to-run, with correct config and traceability.|Only jobs with valid input, Demucs config/model, job_uuid, user_id, and required metadata are accepted.|
|DEMUCS-002|Validate input format, model compatibility, and resource availability|As a developer, I want Demucs to pre-check all jobs for correctness and system readiness.|Jobs with missing files, model mismatch, or unavailable resources are rejected/marked error and returned to Queue with reason.|

### **B. Engine Processing & Resource Management**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|DEMUCS-003|Run Demucs engine for user/system-selected stem configuration|As a user, I want to select my stem configuration (e.g., 2/4/6 stems) and have Demucs process accordingly.|Demucs executes with selected config; output matches user/system request (e.g., all vocal/instrumental/drums, etc.).|
|DEMUCS-004|Support chunked/batched processing for large/complex files|As a user, I want reliable stem separation even for long or high-bitrate files.|Large files are automatically split and processed in chunks/batches; final outputs are reassembled and validated.|
|DEMUCS-005|Enforce per-job resource quotas (CPU, RAM, disk, time)|As an operator, I want Demucs jobs to respect configured resource limits.|Jobs are scheduled with system/user limits; any job exceeding limits is paused/throttled, retried, or failed with error logged.|
|DEMUCS-006|Autoscale worker pool based on queue load and system metrics|As an ops engineer, I want Demucs throughput to scale with demand, without overcommitting resources.|Demucs workers autoscale up/down based on in-queue jobs, host resource utilization, and max/min limits set in config.|

### **C. Health, Dependency, and Failure Handling**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|DEMUCS-007|Health check for engine, model files, and dependencies|As an operator, I want to verify that Demucs and all dependencies are present and working.|`/health` and metrics endpoints show live status for engine, model files, and dependencies (e.g., torch, CUDA, etc.).|
|DEMUCS-008|Surface all errors (model loading, runtime error, input corrupt) to Queue/UI|As a user/operator, I want actionable feedback if Demucs fails.|All errors have explicit code, job context, and reason; surfaced to UI, logs, and Queue.|
|DEMUCS-009|Retry policy for transient/infra failures (OOM, disk, model reload)|As an operator, I want Demucs to auto-retry jobs that fail for non-permanent reasons.|Jobs with eligible errors (OOM, temp disk, model load) are retried with exponential backoff; persistent issues are surfaced as hard failure.|

### **D. Output Handling, Atomicity, and Traceability**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|DEMUCS-010|Output stems are written atomically, tagged, and verified|As a user, I want complete, non-corrupt output files for each Demucs job.|Outputs are written/moved atomically, tagged with job_uuid/user_id, and verified for completeness before handoff.|
|DEMUCS-011|Reassemble chunked outputs into single deliverable set|As a user, I want outputs to match my original file (single set of separated stems).|Chunked outputs are reassembled in the correct order, validated, and surfaced as a single logical set.|
|DEMUCS-012|Handoff all results (stems, logs, error state) to Audio-Recon or next stage|As a system, I want to pass all outputs, metadata, and status to downstream reliably.|All outputs and logs (success or error) are sent with complete job/context info for further processing.|

### **E. Observability, Metrics, and Alerts**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|DEMUCS-013|Structured logging for all actions (start, progress, error, resource use)|As an operator, I want traceable logs for every Demucs job and action.|Logs include job_uuid, user_id, config, timings, error codes, and resource metrics.|
|DEMUCS-014|`/metrics` endpoint exposes job counts, failures, resource usage, chunking stats|As an ops engineer, I want Prometheus metrics for Demucs performance and health.|Metrics include jobs in/out, error rates, latency, average resource use, chunking count, OOMs, etc.|
|DEMUCS-015|Alert on high failure rate, excessive resource use, or repeated job aborts|As an ops engineer, I want real-time notification if Demucs is failing or overused.|Alerts are triggered and surfaced for excessive error rates, high latency, or repeated infra failures.|

### **F. Security, Compliance, and Quotas**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|DEMUCS-016|Enforce per-user/job quotas and RBAC on processing|As an admin, I want no user/job to overconsume Demucs resources.|Per-user/job and system-wide quotas are checked and enforced; jobs over quota are throttled or rejected.|
|DEMUCS-017|Tag outputs for GDPR, retention, and audit|As a user/admin, I want traceability and compliance for all my output files.|Every output file/log is tagged with compliance markers; data retention and right-to-delete enforced throughout.|

---

## **Demucs Service — Complete Flow Diagram (Text)**

1. **Receives job** from Splitter-Stager, validates file, config, and system readiness.
    
2. Checks Demucs model compatibility, config, and available resources.
    
3. Runs Demucs stem separation as configured, chunking large files as needed, autoscaling workers by demand and system health.
    
4. Handles runtime errors, OOM, model errors with intelligent retries and backoff; logs all outcomes and error codes.
    
5. Writes outputs atomically and tags with job/user/config/compliance data; reassembles chunked files for downstream use.
    
6. Handoffs all outputs, logs, and status to Audio-Recon; updates job state in Queue.
    
7. Exposes `/health` and `/metrics` endpoints for live monitoring, surfacing errors and resource stats.
    
8. Alerts on high error/latency/resource conditions; all logs are structured and traceable.
    
9. Enforces per-user quotas, GDPR/retention, and all compliance requirements on data.
    

---