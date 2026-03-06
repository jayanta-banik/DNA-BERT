# Implementation Plan: NCBI Bacteria Crawl and Download

**Branch**: `001-ncbi-bacteria-crawler` | **Date**: 2026-03-04 | **Spec**: `/specs/001-ncbi-bacteria-crawler/spec.md`
**Input**: Feature specification from `/specs/001-ncbi-bacteria-crawler/spec.md`

## Summary

Implement a resumable Node.js crawler that reads `bacteria_name,url` CSV input, discovers and downloads `latest_assembly_versions` content per row, writes one JSONL summary per input row (including `download_completed`), and supports completion-aware reruns that skip completed rows and reprocess incomplete rows.

## Technical Context

**Language/Version**: JavaScript (Node.js ESM; version managed by project runtime)  
**Primary Dependencies**: `got`, `cheerio`, `cli-progress`, `p-limit`  
**Storage**: Local filesystem (`data/*` and output directories) + JSONL file  
**Testing**: CLI/manual integration validation with fixture CSV + output assertions (counts, schema, rerun behavior)  
**Target Platform**: Linux CLI environment  
**Project Type**: Data-ingestion CLI crawler  
**Performance Goals**: Maintain configured concurrency (default 5), satisfy SC-002 (>=99% discovered file download success for available rows), and SC-004 cleanup budget (<30s)  
**Constraints**: Fail-fast CSV validation, bounded concurrency, no batch barrier for progress updates, snake_case persisted JSONL keys, no `Parent Directory` traversal  
**Scale/Scope**: ~100,099 CSV rows (current dataset size), potentially deep directory trees per row

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- [x] Semantic behavior preserved unless spec explicitly changes it
- [x] Source-of-truth behavior identified for domain logic; unknowns escalated
- [x] Diff is minimal and scoped; no drive-by refactors included
- [x] Migration is incremental with explicit checkpoints and runnable state
- [x] Existing project patterns are reused; no unnecessary architecture changes
- [x] Secrets handling and dependency hygiene requirements are satisfied
- [x] Mandatory preflight complete: target project, local rules, entrypoints, patterns
- [x] Naming and schema conventions enforced (Python `snake_case`, Node.js `camelCase`,
      DataFrame/DB/file JSON `snake_case`, constants/enums `UPPER_SNAKE_CASE`)
- [x] JSON message key casing follows runtime language conventions at boundaries
- [x] JS extensible functions use object-parameter signatures (for example, `fn({} = {})`)
- [x] Relative imports are avoided unless explicitly justified by project constraints
- [x] `.specify/memory/*` reviewed (including `UI_BEHAVIOR_STANDARDS.md` and
      `LEARNINGS.md` when present)

## Phase 0 Research Summary

Research decisions are documented in `/specs/001-ncbi-bacteria-crawler/research.md` and resolve crawler unknowns around resumable reconciliation, progress model, HTML index parsing rules, and file-safe download semantics.

## Phase 1 Design Summary

- Data model defined in `/specs/001-ncbi-bacteria-crawler/data-model.md`
- Contracts defined in `/specs/001-ncbi-bacteria-crawler/contracts/`
- Execution runbook defined in `/specs/001-ncbi-bacteria-crawler/quickstart.md`

## Post-Design Constitution Re-Check

- [x] Design remains incremental and scoped to crawler/resume workflow
- [x] Persisted schema keys remain snake_case (`download_completed` included)
- [x] Node.js implementation keeps camelCase variable naming
- [x] No new dependency required beyond already-declared packages
- [x] Planned module boundaries prefer existing script/util structure

## Project Structure

### Documentation (this feature)

```text
specs/001-ncbi-bacteria-crawler/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── crawler-cli.md
│   └── jsonl-summary.schema.json
└── tasks.md
```

### Source Code (repository root)

```text
scripts/
└── node/
    └── crawl_ncbi_bacteria.js

util/
└── node/
    ├── (optional) csv_reader.js
    ├── (optional) index_parser.js
    ├── (optional) downloader.js
    ├── (optional) path_utils.js
    └── (optional) jsonl_store.js

data/
├── external/
│   └── bacteria_index.csv
├── raw/
├── interim/
└── processed/

results/
└── (optional) run logs/metrics
```

**Structure Decision**: Keep crawler entrypoint in `scripts/node/crawl_ncbi_bacteria.js` and add helper modules under `util/node/` only where complexity justifies extraction. Preserve minimal-diff preference by first implementing in-place, then extracting isolated helpers.

## Phase 2 Planning Preview (for `/speckit.tasks`)

1. Add strict CSV ingestion + fail-fast validation path.
2. Implement completion-aware reconciliation against prior JSONL.
3. Implement concurrent row processing with immediate progress updates.
4. Implement latest_assembly_versions discovery and filtered traversal.
5. Implement download pipeline preserving remote hierarchy without extra local layer.
6. Write per-row JSONL summaries with `download_completed` and status/error fields.
7. Validate rerun behavior: skip completed, reprocess incomplete/missing outputs.

## Complexity Tracking

No constitution violations requiring justification.
