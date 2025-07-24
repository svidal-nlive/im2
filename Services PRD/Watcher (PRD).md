
---

# **Service 1: Watcher — Complete Sub-Flow Breakdown (PRD)**

## **Watcher Service: Functional Flows & Requirements**

### **A. File Arrival & Stability Detection**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|WATCH-001|Detect file creation/move into input dir (atomic detection)|As a system, I need to recognize new file arrivals only when writes are fully complete.|File is only considered for processing when write/move is atomic and file size/timestamp is stable for a configured duration.|
|WATCH-002|Support both copy+rename and move (atomicity)|As an admin, I want the watcher to handle both file move-in and copy-then-rename patterns safely.|Watcher does not act on partially written files; only on files moved/renamed atomically or stable after copy.|
|WATCH-003|Handle subfolders for user/job separation|As a developer, I want all user/job subfolders in input/ to be watched recursively.|New files in any user_id/job_uuid subfolder are detected, preserving logical ownership.|
|WATCH-004|Exclude hidden/temp/partial files (file mask/whitelist)|As an operator, I want to avoid processing temp, hidden, or blacklisted files.|Only whitelisted extensions/filenames are watched; dotfiles or temp files (e.g., *.part, ~) are ignored.|

### **B. Concurrency & Crash Recovery**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|WATCH-005|Multiple concurrent file arrivals|As a user, I want to upload multiple files/folders without race conditions.|Watcher processes all eligible files concurrently, with each handled as an isolated event.|
|WATCH-006|Crash/OOM during detection or handoff|As an operator, I want recovery from crashes without losing or duplicating jobs.|On startup, watcher rescans for unprocessed eligible files (based on job markers/state), ignoring files already in pipeline or error.|
|WATCH-007|Idempotency in file re-detection|As a developer, I want files never processed twice if watcher restarts or scans again.|Files are tracked by unique marker/job_uuid; re-detected files already in pipeline are skipped.|

### **C. Job Handoff & Marker Creation**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|WATCH-008|Generate unique job UUID and marker file|As a system, I want every detected file to be assigned a unique, traceable ID.|Each detected file gets a job_uuid and marker (on disk and in logs) before queuing to categorizer.|
|WATCH-009|Atomic handoff to next pipeline stage|As a developer, I want watcher-to-categorizer communication to be atomic, so no jobs are lost or duplicated.|File is handed off (via queue, API, or marker), confirmed receipt before watcher releases lock.|
|WATCH-010|Marker file cleanup after successful handoff|As an operator, I want to avoid marker clutter once jobs are safely in pipeline.|Markers are removed after handoff confirmation, unless retention required for audit/debug.|

### **D. Observability, Health, and Metrics**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|WATCH-011|Structured, centralized logging (with trace_id/job_uuid)|As an operator, I want all watcher activity logged with clear, consistent trace data.|All events, handoffs, errors are logged in JSON with job_uuid, user_id, trace_id.|
|WATCH-012|`/health` endpoint for liveness/readiness|As an ops engineer, I want to probe watcher health automatically.|`/health` endpoint returns status 200 when watcher is live and able to process files.|
|WATCH-013|`/metrics` endpoint (Prometheus-ready)|As an ops engineer, I want pipeline metrics for monitoring/alerting.|Exposes total files detected, in-progress, errored, handoff latency, etc.|

### **E. Error Handling, Edge Cases, and Self-Healing**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|WATCH-014|Handle unreadable/locked/corrupt files gracefully|As a user, I want uploads that fail detection due to file locks or corruption to be retried or surfaced as errors.|Watcher retries eligible files for a configurable period; persistent failures are marked with explicit error and logged/tagged for UI.|
|WATCH-015|Quarantine/unreadable file movement to error/ directory|As an operator, I want failed files to be moved for later analysis, not left in input/.|Files unrecoverable after N retries are atomically moved to error/ with error reason and job marker.|
|WATCH-016|Alert/notification for repeated watcher failures|As an ops engineer, I want alerts if the watcher fails repeatedly or gets stuck.|Repeated handoff or detection failures trigger notifications/alerts; errors are rate-limited and deduplicated.|

### **F. Time Sync and Ordering Guarantees**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|WATCH-017|NTP sync enforcement for all time stamps|As a developer, I want all watcher and job events ordered reliably.|All logs/events use NTP-synced time; watcher refuses to start if time drift exceeds threshold.|
|WATCH-018|File event ordering preserved per user/job|As a user, I want my batch uploads processed in arrival order.|Files within a job/user are queued in the order they are detected stable; marker records preserve arrival order for downstream.|

---

## **Watcher Service — Complete Flow Diagram (Text)**

1. **New file arrives in `input/user_id/job_uuid/`.**
    
2. Watcher ignores until file is stable (no size/timestamp change for N seconds).
    
3. Checks file extension/type, skips if not whitelisted.
    
4. On stability, generates job_uuid (if not already assigned), creates marker file.
    
5. Attempts atomic handoff to Categorizer (via API/queue).
    
6. On confirmation, removes or updates marker.
    
7. Logs all steps with job_uuid, user_id, trace_id.
    
8. On crash/restart, rescans input/ for unprocessed eligible files and resumes.
    
9. Unreadable/corrupt files retried; after N failures, moved to error/ with error reason.
    
10. All metrics/events exposed on `/metrics` and `/health`.
    
11. NTP sync verified at startup; refuses to run if unsynced.
    

---