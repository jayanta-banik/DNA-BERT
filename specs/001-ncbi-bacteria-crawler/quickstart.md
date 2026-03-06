# Quickstart: NCBI Bacteria Crawl and Download

## Prerequisites

- Node.js runtime compatible with project dependencies
- Installed dependencies (`yarn install` already run in repo)
- Input CSV available at `data/external/bacteria_index.csv` with columns:
  - `bacteria_name`
  - `url`

## Configure

1. Open `scripts/node/crawl_ncbi_bacteria.js`.
2. Set top-level constants for:
   - CSV path
   - output JSONL path
   - output folder path
   - concurrency (default 5)
3. Optional runtime overrides via environment variables:

- `CSV_FILE_PATH`
- `OUTPUT_JSONL_PATH`
- `OUTPUT_FOLDER_PATH`
- `CONCURRENCY`
- `JSON_SCHEMA_PATH`

## Run

```bash
node scripts/node/crawl_ncbi_bacteria.js
```

Example (small dry run):

```bash
CSV_FILE_PATH=data/interim/test_run/sample_bacteria.csv \
OUTPUT_JSONL_PATH=results/test_run_summary.jsonl \
OUTPUT_FOLDER_PATH=data/interim/test_run/output \
CONCURRENCY=2 \
node scripts/node/crawl_ncbi_bacteria.js
```

## Expected Behavior

- CSV ingestion validates all rows first (fail-fast on missing required data/encoding issue).
- Crawler processes rows concurrently with immediate progress increments per completed row.
- `latest_assembly_versions/` is checked per row before folder creation.
- Downloads preserve remote hierarchy under each bacteria folder (no extra `latest_assembly_versions` local layer).
- One JSONL summary row is written per input row including `download_completed`.
- JSONL output is validated against `contracts/jsonl-summary.schema.json` before write.

## Rerun/Reconciliation

- On rerun, current CSV rows are matched against prior JSONL by (`bacteria_name`, `source_url`).
- Rows with `download_completed=true` and valid output may be skipped.
- Rows incomplete/missing output are cleared and reprocessed.

## Validation Checklist

- JSONL keys are snake_case.
- `download_completed` is present for every summary row.
- Incomplete rows from prior runs are reprocessed in rerun.
- Missing `latest_assembly_versions` rows are marked `skipped`.
