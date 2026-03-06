# Data Model: NCBI Bacteria Crawl and Download

## Entity: BacteriaInputRow

- Description: Normalized input record loaded from CSV.
- Fields:
  - `bacteria_name` (string, required, non-empty)
  - `source_url` (string, required, non-empty, absolute URL)
  - `row_index` (integer, required, 1-based row number after header)
- Validation Rules:
  - Fail-fast if `bacteria_name` or `source_url` is empty/missing.
  - Fail-fast on malformed/invalid row encoding.

## Entity: CrawlTarget

- Description: Computed row-level target rooted at `latest_assembly_versions/`.
- Fields:
  - `bacteria_name` (string)
  - `source_url` (string)
  - `latest_assembly_versions_url` (string)
  - `latest_assembly_versions_available` (boolean)
- State Transitions:
  - `pending` -> `available` when target URL exists/listing loads.
  - `pending` -> `unavailable` when target URL missing/not listable.

## Entity: VersionEntry

- Description: Version listing discovered under `latest_assembly_versions`.
- Fields:
  - `version_url` (string, required)
  - `version_label` (string, required)
- Validation Rules:
  - Exclude `Parent Directory` entries.
  - Require normalized absolute URL.

## Entity: DownloadArtifact

- Description: One downloaded file mapped into local output hierarchy.
- Fields:
  - `bacteria_name` (string)
  - `source_url` (string)
  - `remote_url` (string)
  - `relative_output_path` (string)
  - `bytes_written` (integer, optional)
  - `download_status` (enum: `success`, `failed`)
- Validation Rules:
  - Preserve remote hierarchy under local bacteria folder.
  - Do not create extra `latest_assembly_versions` local layer.

## Entity: CrawlSummaryRow (JSONL persisted)

- Description: One line of JSONL output representing one input row outcome.
- Fields:
  - `bacteria_name` (string)
  - `source_url` (string)
  - `latest_assembly_versions_available` (boolean)
  - `discovered_version_count` (integer >= 0)
  - `downloaded_file_count` (integer >= 0)
  - `download_completed` (boolean)
  - `versions` (array of `VersionEntry`)
  - `status` (enum: `success`, `failed`, `skipped`)
  - `error_message` (string, optional, required when `status=failed`)
- Validation Rules:
  - Keys must be snake_case.
  - Exactly one summary row per input row in each run output.
- State Transitions:
  - `pending` -> `success` when row completes and artifacts are consistent.
  - `pending` -> `skipped` when target unavailable.
  - `pending` -> `failed` on row-level crawl/download error.
  - `download_completed=true` only for successful, complete row outcome.
