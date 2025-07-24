
---

# **Service 10: UI Backend (FastAPI) — Complete Sub-Flow Breakdown (PRD)**

## **UI Backend Service: Functional Flows & Requirements**

### **A. API Endpoints: Job Submission, Control & Status**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIB-001|Secure job submission API (upload, config, engine selection)|As a user, I want to submit jobs with custom config and file(s), securely and reliably.|API accepts authenticated, RBAC-checked submissions with all required fields, files, and options validated.|
|UIB-002|Job status/query API (per job, per user)|As a user, I want to check the status and progress of all my jobs in real time.|API returns live status, progress, error/retry info, and traceability for all jobs by job_uuid or user_id.|
|UIB-003|Job control API (retry, replay, cancel, delete)|As a user, I want to control my jobs (e.g., retry a failure, delete, cancel running) from the UI.|API allows users to retry/replay, cancel, or delete jobs, with appropriate permissions and state checks.|
|UIB-004|System/admin APIs (pause/resume pipeline, prune, migration, diagnostics)|As an operator/admin, I want to safely manage and maintain the pipeline.|API exposes admin endpoints for pipeline pause/resume, prune, migration/upgrade, and diagnostics download, all RBAC-enforced.|

### **B. Authentication, Authorization, and Security**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIB-005|Closed-by-default API endpoints, RBAC on all actions|As a security admin, I want only authorized users to access each endpoint.|All endpoints require authentication (JWT, OAuth, signed token, or equivalent); RBAC enforced on every API call.|
|UIB-006|Signed, scope-limited API tokens for public/external use|As an integrator, I want to use signed tokens with the minimal scope needed.|API supports token issuance, revocation, and scope-limiting (read-only, upload-only, admin, etc.).|
|UIB-007|Per-user/session tagging and traceability|As an admin, I want every API action traceable to user/session/job.|All actions log user_id, session, and trace_id for audit and debugging.|
|UIB-008|Rate limiting, abuse protection, and brute-force defense|As an operator, I want to protect the API from overuse or attack.|API enforces per-user/session rate limits, IP throttling, and brute-force protection, with error codes and logs.|

### **C. Validation, Compliance, and AV Flows**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIB-009|File type, size, and path whitelist validation|As a user, I want clear and early rejection of invalid/unsafe uploads.|API checks all uploads against allowed types, size, and safe paths before job is queued.|
|UIB-010|AV/virus scan hook on upload|As a security admin, I want all uploads scanned for viruses/malware before processing.|API integrates AV scan (e.g., ClamAV); jobs with positive hits are rejected, logged, and surfaced in UI.|
|UIB-011|EULA/ToS acceptance flow for uploads|As a compliance officer, I want all uploaders to explicitly accept terms before submission.|API requires and logs EULA/ToS acceptance per upload; compliance is auditable and enforced.|

### **D. Documentation, OpenAPI, and Developer Experience**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIB-012|Auto-generated OpenAPI/Swagger docs for all endpoints|As a developer, I want always-current, testable API docs.|Docs are generated and served automatically, validated in CI, and exposed at `/docs` or `/openapi`.|
|UIB-013|Block merge/CI if docs drift from code|As a developer, I want to ensure the API docs always match the codebase.|CI pipeline checks and blocks merge if OpenAPI/docs are out of sync; docs are auto-updated and versioned.|
|UIB-014|Provide example requests, responses, and error codes in docs|As an integrator, I want to see and test all typical/edge API calls.|API docs include example payloads, error codes, and links to diagnostics for faster developer onboarding.|

### **E. Health, Metrics, and Observability**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIB-015|`/health` and `/metrics` endpoints for all API status and usage|As an ops engineer, I want to monitor API health and usage in real time.|Endpoints expose live liveness/readiness, error counts, auth/abuse events, and traffic stats for Prometheus/Grafana.|
|UIB-016|Structured, centralized logging for every API request/response|As an operator, I want traceability and audit for every API action.|Logs include all input, output, status, error codes, user/session/job ids, and full trace_id.|
|UIB-017|Alert on high error rate, abuse attempts, or downtime|As an ops engineer, I want immediate notification of API issues or attacks.|Configurable alerts trigger on high errors, auth failures, or abuse; surfaced to UI and external incident response.|

### **F. Accessibility, Internationalization, and Self-Service**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|UIB-018|API and docs structured for a11y and i18n (future-proof)|As a user or integrator, I want the API to be accessible and localizable.|API and docs follow best practices for accessibility and are organized for future localization.|
|UIB-019|Serve self-service diagnostic bundle download (for failed jobs)|As a user, I want to easily download diagnostic info for my jobs.|API endpoint provides diagnostic bundles/logs for failed jobs, accessible via authenticated request.|

---

## **UI Backend Service — Complete Flow Diagram (Text)**

1. **Receives user or system API request:** authenticates, checks RBAC/scope, tags user/session/trace.
    
2. Validates input: checks file types/sizes, EULA/ToS, and runs AV scan before queuing job.
    
3. Accepts job submissions with full config, returns job_uuid and status; exposes API for job control and diagnostics.
    
4. Allows live query of job status, progress, errors, and full trace by job/user.
    
5. Provides admin endpoints for pause/resume, migration, diagnostics, and resource management (RBAC enforced).
    
6. Auto-generates and serves OpenAPI/Swagger docs, blocking merges if docs are out of sync with codebase.
    
7. Logs all requests, responses, errors, and security/compliance events with traceability.
    
8. Exposes `/health` and `/metrics` endpoints for live API health and usage stats; triggers alerts on anomalies.
    
9. Enforces rate limits, quota, and brute-force protection for all endpoints.
    
10. Supports self-service downloads of diagnostics for failed jobs, with authenticated access.
    
11. Follows accessibility and i18n best practices for API and docs organization.
    

---