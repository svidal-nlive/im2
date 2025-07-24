
---

# **Service 11: UI Frontend (Next.js) — Complete Sub-Flow Breakdown (PRD)**

## **UI Frontend Service: Functional Flows & Requirements**

### **A. File Upload & Job Submission**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIF-001|Multi-file and folder upload with drag-and-drop and progress feedback|As a user, I want to easily upload one or more files/folders, and see upload progress.|UI supports drag-and-drop, folder and multi-file upload, and shows real-time upload progress, file size, and success/failure for each.|
|UIF-002|Real-time validation of file type, size, EULA/ToS acceptance before upload|As a user, I want instant feedback if a file is invalid, or if I need to accept terms.|UI checks file type/size and prompts for EULA/ToS acceptance before job submission; invalid files are rejected with clear reason.|
|UIF-003|Engine selection, job configuration, and metadata overrides in submission flow|As a user, I want to choose the stem engine, configure job options, and edit tags/art before processing.|UI allows users to select Spleeter/Demucs, choose stem config, and edit/add metadata/artwork before submitting a job.|

### **B. Job Monitoring & Status**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIF-004|Real-time job progress/status display for all active and past jobs|As a user, I want to monitor every job’s status, progress, step, and ETA as it runs.|UI polls or receives live updates for each job’s status, displaying step-by-step progress, current action, and estimated completion.|
|UIF-005|Historical job view, with filter, search, and sort|As a user, I want to view, filter, and search all my past jobs and results.|Users can view a list/history of jobs, filter by date/status/engine, and search by file name or tag.|
|UIF-006|Surface all errors/warnings, with actionable details and links|As a user, I want immediate and clear feedback for any job error, including what happened and how to fix it.|Errors and warnings are shown inline with actionable messages, job_uuid, and links to diagnostic bundles or support resources.|

### **C. Job Control: Retry, Replay, Cancel, Delete**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIF-007|Self-service retry/replay for failed jobs, with safe confirmation|As a user, I want to retry or replay failed jobs from the UI with a single click, and confirmation.|Retry/replay buttons are available for failed/incomplete jobs, requiring confirmation and providing status during replay.|
|UIF-008|Cancel or delete jobs from any state (with state check and confirmation)|As a user, I want to cancel running jobs or delete any job (with confirmation and compliance).|Cancel/delete actions are always available (with appropriate warnings), honoring legal/compliance requirements and updating job state in real time.|
|UIF-009|Download original input, processed output, and diagnostic bundles|As a user, I want to download my original uploads, outputs, and all logs/diagnostics for any job.|UI provides download links for all relevant files, only for jobs the user owns and in allowed states.|

### **D. Accessibility (a11y) & Internationalization (i18n)**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIF-010|Full accessibility (a11y) compliance for all flows|As a user with disabilities, I want to use the platform via keyboard, screen reader, or assistive device.|UI meets WCAG 2.1 AA standards; all elements are navigable by keyboard, labeled for screen readers, and usable for all users.|
|UIF-011|UI structured for easy future localization/internationalization|As a non-English user, I want the UI ready for translation and local conventions.|All strings and UI elements are externalized and structured for i18n, with RTL support and locale-aware formatting.|

### **E. Notifications & User Guidance**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIF-012|In-app and email/push notifications for job status, errors, or completion|As a user, I want instant notification when a job completes, fails, or requires action.|UI surfaces notifications in-app and (optionally) via email/push, rate-limited and user-configurable.|
|UIF-013|“Why did my job fail?” user guidance with links to logs, docs, and support|As a user, I want actionable help and next steps if my job fails.|UI provides a clear reason, links to logs/diagnostic bundle, and links to support or documentation for common issues.|

### **F. Security, Compliance, and Quota Feedback**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIF-014|UI feedback for quota, rate limiting, and compliance events|As a user, I want to know if I hit a limit, what it means, and what to do next.|All quota/rate/compliance limits are surfaced with clear UI feedback, error messages, and suggested next steps.|
|UIF-015|Require and track EULA/ToS acceptance for every upload session|As a compliance officer, I want explicit acceptance for legal coverage, and user records for every session.|UI enforces acceptance before upload, stores record of acceptance with session/job, and shows acceptance status.|

### **G. Observability, Metrics, and Diagnostics**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIF-016|Client-side telemetry for UI errors, performance, and usage|As a developer/operator, I want to monitor and debug UI health and bottlenecks.|UI emits anonymized telemetry for errors, performance events, and usage (respecting user privacy and opt-out).|
|UIF-017|Downloadable UI diagnostic bundle for support/triage|As a user or support, I want to send my UI logs and state for faster troubleshooting.|User can download anonymized UI log/state bundle for helpdesk or triage.|

---

## **UI Frontend Service — Complete Flow Diagram (Text)**

1. **User uploads files/folders**: UI validates, requires EULA/ToS, and configures job before submission.
    
2. **Job submitted via API**: UI shows progress, status, and any early errors.
    
3. **Jobs monitored in real time**: live status, step, and ETA displayed; all jobs (active/history) searchable and filterable.
    
4. **Errors, retries, and replays**: All failures have actionable messages, links to replay/cancel/download outputs/diagnostics.
    
5. **Notifications**: in-app and optional email/push for job complete, error, or quota event.
    
6. **Accessibility & i18n**: full keyboard, screen reader, and locale-aware formatting.
    
7. **Quota/compliance surfaced**: UI shows quota/rate/compliance events as needed, with help.
    
8. **Diagnostics**: users can download bundles for support, and UI emits anonymized telemetry for internal monitoring.
    

---