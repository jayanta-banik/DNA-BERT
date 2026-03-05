# Contract: Crawler CLI Behavior

## Entrypoint

- Script: `scripts/node/crawl_ncbi_bacteria.js`
- Execution: `node scripts/node/crawl_ncbi_bacteria.js`

## Input Contract

- Source CSV with header row and required columns:
  - `bacteria_name`
  - `url`
- Validation mode: fail-fast
  - Any empty/missing required field or malformed row encoding logs row+reason and halts run.

## Runtime Behavior Contract

- Concurrency: runtime-configurable constant, default `5` row tasks.
- Progress: updates on individual task completion, with immediate next-task dispatch when slot frees.
- Traversal: ignore `Parent Directory` links.

## Rerun Contract

- Reconciliation key: (`bacteria_name`, `source_url`)
- Resume rule:
  - `download_completed=true` + consistent local output: may skip row.
  - `download_completed=false` or missing/inconsistent output: clear row artifacts and reprocess.

## Output Contract

- JSONL output: one row per CSV row, schema in `contracts/jsonl-summary.schema.json`.
- Persisted key naming: snake_case.
