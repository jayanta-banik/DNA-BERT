# Phase 0 Research: NCBI Bacteria Crawl and Download

## Decision 1: Completion-aware rerun reconciliation key

- Decision: Match prior run rows using (`bacteria_name`, `source_url`) and use `download_completed` plus local output existence to determine skip vs reprocess.
- Rationale: `bacteria_name` alone can be ambiguous in future datasets; pairing with URL avoids accidental reuse. `download_completed` supports resumability while preventing stale partial state reuse.
- Alternatives considered:
  - Match only by `bacteria_name`: rejected due to potential future collisions/source changes.
  - Always wipe all outputs before run: rejected because expensive at 100k+ rows and prevents resume.

## Decision 2: Concurrency and progress behavior

- Decision: Use `p-limit` with runtime-configurable constant (default `5`) and update CLI progress per individual row completion (no batch barrier).
- Rationale: Aligns with user requirement for immediate slot refill and rough throughput visibility while staying polite to remote infrastructure.
- Alternatives considered:
  - Sequential processing: rejected as too slow for 100k+ rows.
  - Unbounded concurrency: rejected due to memory/network pressure and server courtesy risk.

## Decision 3: HTML index traversal and loop prevention

- Decision: Parse directory listings via `cheerio`, ignore `Parent Directory`, and resolve links using URL normalization before recursion/download.
- Rationale: NCBI directory indexes are HTML listing pages; explicit filtering avoids recursive loop patterns.
- Alternatives considered:
  - Regex-only parsing: rejected as brittle against index formatting changes.
  - Headless browser crawling: rejected as unnecessary complexity/dependency weight.

## Decision 4: JSONL summary contract

- Decision: Persist one JSON object per input row with snake_case keys and required fields including `download_completed`, `status`, optional `error_message`, and minimal `versions[]` objects (`version_url`, `version_label`).
- Rationale: Supports auditability, rerun matching, and manageable file size for high-row-volume runs.
- Alternatives considered:
  - Store all discovered file paths in JSONL: rejected due to large output size.
  - Omit completion flag: rejected because rerun reconciliation requires explicit completion state.

## Decision 5: CSV ingestion quality gate

- Decision: Fail fast during ingestion on missing/empty `bacteria_name` or `url`, or malformed encoding; log row number and reason then halt.
- Rationale: User explicitly prefers manual correction over silent skipping, preserving dataset integrity.
- Alternatives considered:
  - Skip invalid rows with warning: rejected per user instruction.
  - Auto-correct malformed rows: rejected to avoid implicit data mutation.
