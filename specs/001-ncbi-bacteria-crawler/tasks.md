# Tasks: NCBI Bacteria Crawl and Download

**Input**: Design documents from `/specs/001-ncbi-bacteria-crawler/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: No explicit TDD/test-first requirement in spec; this task list focuses on implementation and manual/integration validation steps.

**Organization**: Tasks are grouped by user story for independent implementation and verification.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preflight, configuration constants, and scaffolding for crawler modules.

- [ ] T001 Complete preflight and entrypoint inventory for crawler in scripts/node/crawl_ncbi_bacteria.js
- [ ] T002 Define runtime constants (CSV path, output folder, JSONL path, concurrency default=5) in scripts/node/crawl_ncbi_bacteria.js
- [ ] T003 [P] Create URL/path helper utilities for normalization and safe local path mapping in util/node/path_utils.js
- [ ] T004 [P] Create JSONL read/write helper utilities in util/node/jsonl_store.js
- [ ] T005 [P] Create HTML index parsing helpers (ignore Parent Directory) in util/node/index_parser.js

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core row pipeline needed by all user stories.

**CRITICAL**: No user story implementation starts until this phase is complete.

- [ ] T006 Implement fail-fast CSV ingestion and row validation (`bacteria_name`,`url`, UTF-8 assumptions) in scripts/node/crawl_ncbi_bacteria.js
- [ ] T007 Implement summary row builder with snake_case keys and required FR-011 fields in util/node/jsonl_store.js
- [ ] T008 Implement completion-aware reconciliation loader keyed by (`bacteria_name`,`source_url`) in util/node/jsonl_store.js
- [ ] T009 Implement local output consistency check for `download_completed=true` reuse decisions in util/node/path_utils.js
- [ ] T010 Wire foundational helpers into main crawler startup flow in scripts/node/crawl_ncbi_bacteria.js

**Checkpoint**: Foundation complete. User story work can proceed.

---

## Phase 3: User Story 1 - Build Dataset Snapshot per Bacteria (Priority: P1) 🎯 MVP

**Goal**: Download available `latest_assembly_versions` content per row into bacteria-specific local folders.

**Independent Test**: Run with a mixed CSV and confirm directories/files are created only for rows with available `latest_assembly_versions`.

### Implementation for User Story 1

- [ ] T011 [US1] Implement target URL derivation for `latest_assembly_versions/` in scripts/node/crawl_ncbi_bacteria.js
- [ ] T012 [US1] Implement existence check for target listing before folder creation in scripts/node/crawl_ncbi_bacteria.js
- [ ] T013 [US1] Implement version discovery parser (labels + URLs) using util/node/index_parser.js in scripts/node/crawl_ncbi_bacteria.js
- [ ] T014 [US1] Implement recursive crawl traversal that excludes `Parent Directory` links in scripts/node/crawl_ncbi_bacteria.js
- [ ] T015 [US1] Implement download flow preserving remote hierarchy under per-bacteria folder without extra `latest_assembly_versions` layer in scripts/node/crawl_ncbi_bacteria.js
- [ ] T016 [US1] Ensure unavailable targets are marked as skipped and do not create bacteria folders in scripts/node/crawl_ncbi_bacteria.js
- [ ] T017 [US1] Add per-row error isolation so failed rows do not halt remaining rows in scripts/node/crawl_ncbi_bacteria.js

**Checkpoint**: User Story 1 is independently functional.

---

## Phase 4: User Story 2 - Generate Crawl Summary JSONL (Priority: P2)

**Goal**: Emit one JSONL summary row per input row with required metadata and completion status.

**Independent Test**: Run with success, skipped, and failed rows; verify exactly one summary row per CSV row and schema compliance.

### Implementation for User Story 2

- [ ] T018 [US2] Populate summary fields (`bacteria_name`,`source_url`,`latest_assembly_versions_available`,`discovered_version_count`,`downloaded_file_count`,`download_completed`) in scripts/node/crawl_ncbi_bacteria.js
- [ ] T019 [US2] Populate minimal `versions` objects (`version_url`,`version_label`) in scripts/node/crawl_ncbi_bacteria.js
- [ ] T020 [US2] Set status transitions (`success`,`failed`,`skipped`) and conditional `error_message` handling in scripts/node/crawl_ncbi_bacteria.js
- [ ] T021 [US2] Append exactly one JSONL record per input row in processing order using util/node/jsonl_store.js from scripts/node/crawl_ncbi_bacteria.js
- [ ] T022 [US2] Validate JSONL output against contracts/jsonl-summary.schema.json in scripts/node/crawl_ncbi_bacteria.js

**Checkpoint**: User Stories 1 and 2 are independently functional.

---

## Phase 5: User Story 3 - Safe Reruns with Deterministic Cleanup (Priority: P3)

**Goal**: Reuse completed rows and reprocess incomplete/inconsistent rows via completion-aware reconciliation.

**Independent Test**: Run twice and verify completed rows are skipped when output is intact while incomplete rows are cleared and redownloaded.

### Implementation for User Story 3

- [ ] T023 [US3] Implement reconciliation match by (`bacteria_name`,`source_url`) against prior JSONL in scripts/node/crawl_ncbi_bacteria.js
- [ ] T024 [US3] Implement skip path for rows with `download_completed=true` and consistent output in scripts/node/crawl_ncbi_bacteria.js
- [ ] T025 [US3] Implement cleanup path for rows with `download_completed=false` or missing/inconsistent output in scripts/node/crawl_ncbi_bacteria.js
- [ ] T026 [US3] Remove stale prior JSONL entries for rows chosen for reprocessing in util/node/jsonl_store.js
- [ ] T027 [US3] Ensure reconciliation-skipped rows also emit current-run JSONL records (one record per input row invariant) in scripts/node/crawl_ncbi_bacteria.js

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, documentation, and operational checks.

- [ ] T028 Implement CLI progress updates for per-task completion with immediate slot refill (no batch bottleneck) in scripts/node/crawl_ncbi_bacteria.js
- [ ] T029 [P] Add structured console logging for row start/finish/failure with row identifiers in scripts/node/crawl_ncbi_bacteria.js
- [ ] T030 [P] Update run and configuration notes for final behavior in specs/001-ncbi-bacteria-crawler/quickstart.md
- [ ] T031 Run end-to-end dry run with representative CSV and verify SC-001..SC-004 outcomes in scripts/node/crawl_ncbi_bacteria.js

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies.
- Foundational (Phase 2): depends on Setup completion; blocks all story phases.
- User Stories (Phases 3-5): depend on Foundational completion.
- Polish (Phase 6): depends on completion of all targeted user stories.

### User Story Dependencies

- User Story 1 (P1): starts after Phase 2; no dependency on other user stories.
- User Story 2 (P2): starts after Phase 2 and depends on US1 data flow outputs for discovered versions/download counts.
- User Story 3 (P3): starts after Phase 2 and depends on US2 JSONL schema/fields (`download_completed`) for reconciliation.

### Recommended Completion Order

- US1 -> US2 -> US3

---

## Parallel Opportunities

- Setup parallel tasks: T003, T004, T005
- Foundational parallel-ready sequencing after helper creation: T007 and T009 can proceed in parallel after T003/T004
- Polish parallel tasks: T029 and T030

## Parallel Example: User Story 1

```bash
Task: "Implement version discovery parser (labels + URLs) using util/node/index_parser.js in scripts/node/crawl_ncbi_bacteria.js"
Task: "Implement recursive crawl traversal that excludes Parent Directory links in scripts/node/crawl_ncbi_bacteria.js"
```

## Parallel Example: User Story 2

```bash
Task: "Populate minimal versions objects (version_url,version_label) in scripts/node/crawl_ncbi_bacteria.js"
Task: "Set status transitions (success,failed,skipped) and conditional error_message handling in scripts/node/crawl_ncbi_bacteria.js"
```

## Parallel Example: User Story 3

```bash
Task: "Implement cleanup path for rows with download_completed=false or missing/inconsistent output in scripts/node/crawl_ncbi_bacteria.js"
Task: "Remove stale prior JSONL entries for rows chosen for reprocessing in util/node/jsonl_store.js"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate US1 independently with mixed availability rows.

### Incremental Delivery

1. Deliver US1 download behavior.
2. Add US2 JSONL completeness and schema guarantees.
3. Add US3 completion-aware rerun reconciliation.
4. Finish with Polish for progress/logging and success-criteria verification.

### Execution Notes

- Keep diffs minimal and scoped to crawler feature.
- Persisted JSONL keys must remain snake_case.
- Avoid relative imports when wiring helper modules.
- Use configurable concurrency constant in crawler entrypoint.
