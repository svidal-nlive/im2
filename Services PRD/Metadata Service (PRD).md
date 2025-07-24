
---

# **Service 4: Metadata Service — Complete Sub-Flow Breakdown (PRD)**

## **Metadata Service: Functional Flows & Requirements**

### **A. Input Reception & Validation**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|META-001|Receive job and input file reference from Queue|As a system, I want to get jobs with metadata requirements and file references from the queue reliably.|Metadata service receives job_uuid, user_id, input file path, and required tags from Queue, validated and logged.|
|META-002|Validate file format and readability|As a developer, I want to ensure input files are valid and readable before extraction.|Invalid, unreadable, or corrupt files are rejected and error is reported back to Queue with reason.|

### **B. Tag & Artwork Extraction**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|META-003|Extract embedded tags (artist, album, song, year, genre, track, etc.)|As a user, I want all my audio file’s tags preserved and transferred to outputs.|All supported metadata tags are extracted, validated, and logged per job_uuid.|
|META-004|Extract embedded or associated cover art|As a user, I want my cover artwork preserved and re-used in outputs.|Artwork is extracted, cached, and made available for downstream stages.|
|META-005|Normalize/clean extracted metadata for downstream compatibility|As a developer, I want tags in a consistent, clean format for all following services.|Tags are standardized (trimmed, encoding-normalized, type-checked) before handoff.|

### **C. External Metadata Lookups & Fallbacks**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|META-006|Lookup and enrich metadata via MusicBrainz or other sources|As a user, I want missing or incomplete tags filled in automatically.|If embedded tags are missing/incomplete, service performs MusicBrainz lookup to supplement fields.|
|META-007|Use cover-art-cache and fallback logic for unavailable art|As a user, I want the system to find cover art even if not embedded.|If embedded art missing, cover-art-cache or MusicBrainz art is used as fallback.|
|META-008|Cache lookup results for efficiency and rate-limit resilience|As a developer, I want to avoid repeated external requests and handle rate limits.|All lookups are cached per job/song/artist; cache is used before remote request.|
|META-009|Validate dependency health (MusicBrainz, etc.) and fail gracefully|As an operator, I want to detect and handle metadata dependency outages.|If external lookup fails, service logs dependency error, uses best-available metadata, and flags partial result for UI/alerting.|

### **D. Metadata Contract, Versioning & Compliance**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|META-010|Enforce explicit versioned metadata contract for all handoffs|As a developer, I want robust and predictable metadata structures for all downstream services.|All outputs conform to a versioned contract/schema; breaking changes are gated and versioned.|
|META-011|Tag job with metadata extraction and lookup version|As an operator, I want every job’s metadata provenance clear for debugging.|Each metadata artifact/log is tagged with extraction/lookup version, job_uuid, and trace_id.|

### **E. Error Handling & Self-Healing**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|META-012|Surface and propagate all extraction/lookup errors with code and reason|As a user, I want to know if metadata or artwork could not be extracted/found.|All errors are logged, surfaced in UI, and attached to job state with code and message.|
|META-013|Retry policy for transient lookup failures|As an operator, I want the service to retry temporary errors without failing the job.|Transient lookup/network errors are retried with backoff; only persistent failures are marked as error.|
|META-014|Partial metadata/art is handled gracefully and flagged|As a user, I want my job to proceed with partial tags/art if only some data is available.|Job proceeds even if some fields/artwork are missing; missing data is flagged for downstream and surfaced in UI.|

### **F. Output & Handoff**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|META-015|Handoff enriched metadata/artwork to downstream (Splitter-Stager, Organizer, etc.)|As a pipeline, I want metadata and art available for tagging all derived outputs.|Structured metadata and art are attached to job for all downstream stages; format conforms to contract.|
|META-016|Persist per-job metadata for traceability and audit|As an admin, I want every job’s extracted/derived metadata to be reviewable/auditable.|All metadata/art is stored with job_uuid and trace_id in persistent storage/logs.|

### **G. Observability, Metrics & Health**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|META-017|Structured, centralized logging for all metadata actions|As an operator, I want full traceability for all extraction, lookup, and errors.|All metadata extraction/lookup actions are logged with job_uuid, user_id, trace_id, and contract version.|
|META-018|`/health` and `/metrics` endpoints for service and dependency health|As an operator, I want to monitor metadata service and dependency status in real time.|Endpoints show job throughput, error rates, external lookup status, cache hits/misses, etc.|
|META-019|Alert/notification on dependency outage or high error rates|As an ops engineer, I want to be notified if metadata lookups or extractions are failing at high rates.|Configurable alerts/notifications for lookup failures, cache exhaustion, or service errors.|

### **H. Security & Compliance**

|Req ID|Description|User Story|Expected Behavior/Outcome|
|---|---|---|---|
|META-020|Enforce file path/type whitelist and AV scan before metadata extraction|As a security admin, I want to prevent invalid or malicious files from being processed.|Only whitelisted, AV-checked files are processed for metadata; all others are rejected and quarantined.|
|META-021|Respect data retention and privacy/compliance tags on metadata artifacts|As a user, I want my metadata to be handled per retention/privacy settings.|Metadata/artifacts are retained or purged per per-job/user policies; right-to-delete requests cascade to all stored metadata.|

---

## **Metadata Service — Complete Flow Diagram (Text)**

1. **Receives job** (from Queue) with input file reference and metadata extraction requirements.
    
2. Validates file format/readability and runs AV/path whitelist.
    
3. Extracts all embedded tags/artwork and normalizes.
    
4. Performs external lookup (MusicBrainz) for missing tags/art, with fallback to cover-art-cache and previous results.
    
5. Caches lookup results for future efficiency; detects and handles rate limits/outages.
    
6. Assembles enriched metadata contract, tagged with version/job_uuid/trace_id.
    
7. Handles errors (missing tags, lookup failures) gracefully; retries transients, flags partials.
    
8. Handoffs complete/partial metadata to downstream services for tagging/final output.
    
9. Persists all actions/artifacts for traceability and audit.
    
10. Exposes `/health` and `/metrics` endpoints for monitoring and alerting.
    
11. Enforces compliance, retention, and right-to-delete for all metadata and artifacts.
    

---