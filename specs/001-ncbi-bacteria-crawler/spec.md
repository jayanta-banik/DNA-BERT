# Feature Specification: NCBI Bacteria Crawl and Download

**Feature Branch**: `001-ncbi-bacteria-crawler`  
**Created**: 2026-03-04  
**Status**: Draft  
**Input**: User description: "Implement crawler updates starting from `crawl_ncbi_bacteria.js` to read CSV input, crawl latest assembly versions, download files, and emit JSONL summaries."

## Compliance Notes _(mandatory)_

- **Relevant Constitution Principles**: I. Semantic Integrity and Source-of-Truth Behavior; II. Minimal Diffs; IV. Prefer Existing Patterns; V. Security, Dependency Hygiene, Mandatory Preflight, and Naming Discipline.
- **UI Behavior Standards Applied**: N/A (no UI behavior change in this feature).
- **Cross-Feature Learnings Applied**: No additional memory files found beyond constitution at specification time.
- **Conflicts & Resolution**: Potential conflict between external source naming and repository naming rules is resolved by preserving external fields at ingestion boundaries and using repository naming conventions in persisted outputs.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Build Dataset Snapshot per Bacteria (Priority: P1)

As a researcher, I want the crawler to read the bacteria CSV and download available latest assembly version contents for each bacteria entry so I can build a local, structured dataset snapshot.

**Why this priority**: This is the core data acquisition outcome required before any downstream analysis.

**Independent Test**: Provide a CSV with at least one valid bacteria URL and verify the corresponding bacteria directory is created only when the latest assembly versions location exists, and downloaded files appear under that bacteria directory.

**Acceptance Scenarios**:

1. **Given** a CSV row with a bacteria name and a URL where a latest assembly versions location exists, **When** the crawler runs, **Then** it creates that bacteria folder and downloads the available content while preserving source folder hierarchy.
2. **Given** a CSV row where the latest assembly versions location does not exist, **When** the crawler runs, **Then** it does not create a bacteria folder for that row and records the row outcome as skipped.

---

### User Story 2 - Generate Crawl Summary JSONL (Priority: P2)

As a researcher, I want one JSONL row per input bacteria entry with crawl results and metadata so I can audit coverage and troubleshoot failed or partial data pulls.

**Why this priority**: Reliable provenance and auditability are essential for research data pipelines.

**Independent Test**: Run the crawler against a mixed CSV (existing and non-existing latest assembly versions URLs) and verify one JSON object per input row with required summary fields.

**Acceptance Scenarios**:

1. **Given** a completed crawl run, **When** I inspect the JSONL output, **Then** each input row has a corresponding summary record containing bacteria name, count of discovered versions, and version listing metadata.
2. **Given** a row that failed download operations, **When** I inspect that JSONL record, **Then** it includes status and error details without halting summary generation for other rows.

---

### User Story 3 - Safe Reruns with Deterministic Cleanup (Priority: P3)

As a researcher, I want reruns to clear previous output artifacts first so each run represents a clean and reproducible snapshot.

**Why this priority**: Prevents stale artifacts and mixed-run outputs from contaminating research datasets.

**Independent Test**: Run the crawler twice and verify completion-aware reconciliation: completed rows with consistent output are reused/skipped, while incomplete/inconsistent rows are cleared and re-downloaded.

**Acceptance Scenarios**:

1. **Given** existing output folders and JSONL records from a prior run, **When** a new crawl starts, **Then** rows with `download_completed=false` (or missing/inconsistent local output) are cleared and reprocessed, while rows with `download_completed=true` and valid local output may be reused/skipped.

### Edge Cases

- CSV has missing or empty `bacteria_name` or `url` values for one or more rows.
- CSV includes duplicate bacteria names pointing to different URLs.
- Source index includes `Parent Directory` links that would cause recursive loops if followed.
- Source has deeply nested folders and large file sets for some bacteria entries.
- Network interruption occurs mid-crawl for one bacteria while others are still processable.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST read an input CSV with exactly two columns: `bacteria_name` and `url`. On ingestion, System MUST validate each row: if `bacteria_name` is empty/missing or `url` is empty/missing, or if the row contains non-UTF-8 bytes, System MUST log an error to console with row number and validation failure reason, then halt execution (fail-fast). User must manually correct the CSV data and re-run.
- **FR-002**: System MUST perform rerun reconciliation using current CSV rows matched against prior JSONL records (if JSONL exists) by `bacteria_name` and `source_url`. If a matched prior record has `download_completed=true` and expected local output exists, System MAY skip re-download for that row. If `download_completed=false` (or output is missing/inconsistent), System MUST clear that row's prior output folder entry and prior JSONL record, then process it again in the current run. This keeps reruns resumable while preventing stale/incomplete artifacts.
- **FR-003**: System MUST evaluate each CSV row independently and append exactly one summary JSONL record per input row for the current run, including rows skipped due to reconciliation (`download_completed=true` with consistent local output).
- **FR-004**: System MUST check whether each row's `latest_assembly_versions/` location exists before creating a local bacteria folder.
- **FR-005**: System MUST create a local bacteria folder only when the corresponding latest assembly versions location exists.
- **FR-006**: System MUST crawl only the source listing links needed for the target latest assembly versions content and MUST ignore `Parent Directory` entries.
- **FR-007**: System MUST download discovered files while preserving the remote directory structure beneath each bacteria folder.
- **FR-008**: System MUST place latest assembly version data directly under each bacteria folder (no extra `latest_assembly_versions` folder layer locally).
- **FR-009**: System MUST show crawl/download progress using a CLI progress display.
- **FR-010**: System MUST continue processing remaining rows when one row fails and capture row-level failure details in its summary record.
- **FR-011**: Each JSONL summary row MUST include at least: bacteria name, source URL, latest assembly versions availability status, count of discovered version entries, count of downloaded files, a boolean `download_completed` field, and a list of version objects. Each version object MUST contain `version_url` and `version_label` fields (minimal schema per clarification Q3).
- **FR-012**: Persisted JSONL keys MUST follow `snake_case` naming conventions.

### Key Entities _(include if feature involves data)_

- **Bacteria Input Row**: One CSV row containing `bacteria_name` and `url` used as crawl seed data.
- **Crawl Target**: Computed latest assembly versions location derived from the row URL.
- **Version Entry**: One discovered version listing with human-readable text and resolved URL.
- **Download Artifact**: One file downloaded from the remote hierarchy and mapped into local output.
- **Crawl Summary Row**: One JSON object per input row containing status, counts, and metadata.

### Assumptions and Dependencies

- Input CSV is UTF-8 text and includes a header row.
- `bacteria_name` values are unique in the current dataset (verified: 100,099 rows, 100,099 unique values).
- `bacteria_name` values are suitable for deterministic folder naming after sanitization.
- Source listings expose a parseable index format containing navigable links.
- Sufficient local storage is available for downloaded artifacts.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: 100% of valid input rows produce exactly one JSONL summary record per run.
- **SC-002**: For rows where latest assembly versions are available, at least 99% of discovered downloadable files are saved locally in one run without manual retries, measured as `successful_file_download_count / discovered_downloadable_file_count >= 0.99` for the current run.
- **SC-003**: For rows where latest assembly versions are unavailable, 100% are marked as skipped (not failed) and produce no local bacteria directory.
- **SC-004**: A rerun after prior outputs exist starts from a clean output state in under 30 seconds for output cleanup.

## Non-Functional Requirements & Architectural Decisions _(non-binding guidance for planning phase)_

### Concurrency Model

- **Approach**: Row-level scanning and downloading shall be concurrent with individual task completion driving progress updates, not batch completion.
- **Concurrency Limit**: Configurable at runtime via a constant in the main crawler file (default: 5 concurrent bacteria rows scanned/downloaded simultaneously).
- **Progress Tracking Behavior**: When any single URL scan or file download completes, that task result updates the CLI progress display immediately. New tasks are dispatched concurrently to refill the concurrency pool, independent of whether other tasks in the current pool are complete. This prevents batch-level bottlenecks.
- **Rationale**: Balances NCBI server load courtesy, memory constraints, and reasonable completion time for 100K+ bacteria entries. Runtime configurability allows tuning based on observed memory/bandwidth conditions.

### JSONL Output Schema

**Summary structure (one row per input CSV row):**

```json
{
  "bacteria_name": "string",
  "source_url": "string",
  "latest_assembly_versions_available": boolean,
  "discovered_version_count": number,
  "downloaded_file_count": number,
  "download_completed": boolean,
  "versions": [
    {
      "version_url": "string",
      "version_label": "string"
    }
  ],
  "status": "success" | "failed" | "skipped",
  "error_message": "string (optional, only if status is 'failed')"
}
```

**Rationale**: Minimal version object structure keeps output size reasonable for 100K+ rows while preserving essential provenance (URL and human-readable label for traceability).

## Clarifications

### Session 2026-03-04

- Q: When the input CSV contains two rows with the same bacteria name but different URLs, how should the crawler handle it? → A: Current dataset analysis confirms bacteria names are unique (100,099 rows, 100,099 unique values), so duplicate handling is not a practical concern for this run. Code will treat each row independently (per Option A) for defensive robustness against future data variations.
- Q: Concurrent processing strategy for 100K+ bacteria rows? → A: Concurrency is runtime-configurable (default 5 concurrent row tasks) to adapt to available memory and network bandwidth. Progress updates are fine-grained per individual task completion, not batch-based, enabling new tasks to dispatch immediately as slots free up in the concurrency pool.
- Q: JSONL version object structure? → A: Minimal schema: each version object contains only `version_url` and `version_label` fields. Keeps output lean for 100K+ rows while preserving provenance traceability.
- Q: Error recovery and retry strategy? → A: No automatic retry within run (Option B). Failed rows are marked immediately with error details captured in JSONL record. Subsequent reruns (per User Story 3) naturally reattempt failed rows from the prior JSONL output, enabling deterministic execution without retry loops.
- Q: CSV data quality and validation? → A: Fail-fast validation (Option B): on ingestion, validate that `bacteria_name` and `url` are non-empty and UTF-8 encoded. If any row violates this, log error to console with row number and reason, then halt. User manually fixes CSV and re-runs. This ensures data integrity from start while avoiding silent corruption.
