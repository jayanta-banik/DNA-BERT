# Tasks: Protein Sequence EDA and Tokenization Strategy Evaluation for BERT Pretraining

**Input**: Design documents from `/specs/001-protein-eda-tokenization/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No separate automated test suite was explicitly requested in the specification. Validation work is implemented as notebook Run All checks, artifact/schema checks, and independent user-story verification tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the notebook target, helper-module surface, and output locations without yet implementing story behavior.

- [ ] T001 Complete mandatory preflight using `.specify/memory/constitution.md`, `notebooks/readme.md`, `specs/001-protein-eda-tokenization/spec.md`, and `specs/001-protein-eda-tokenization/plan.md`
- [ ] T002 Create feature scaffolding for `EDA.ipynb`, `util/python/`, `data/interim/protein_eda/`, and `results/protein_eda/figures/`
- [ ] T003 Define the imports-first and config-second notebook skeleton in `EDA.ipynb`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared parsing, artifact, and configuration plumbing that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 [P] Create shared FASTA discovery and record-loading helpers in `util/python/protein_fasta_io.py`
- [ ] T005 [P] Create shared artifact-writing and manifest helpers in `util/python/protein_eda_artifacts.py`
- [ ] T006 [P] Create shared tokenization helper scaffolding in `util/python/tokenization_strategies.py`
- [ ] T006a Verify `~/venv3` provides Parquet-export and BPE-comparison dependencies needed by `EDA.ipynb`, and document or install any missing packages for `pyarrow` and the chosen BPE library
- [ ] T007 Wire helper imports, baseline config values, and fail-fast config validation into `EDA.ipynb`
- [ ] T007a Place all runtime controls and switches in the config block of `EDA.ipynb`, including optional scope overrides, residue-sensitivity modes, and output toggles
- [ ] T008 Implement shared output-path setup, scope logging, and manifest-plumbing cells in `EDA.ipynb`
- [ ] T009 Align notebook output behavior with `specs/001-protein-eda-tokenization/contracts/eda-notebook-config.md` and `specs/001-protein-eda-tokenization/contracts/analysis-artifact-manifest.schema.json`

**Checkpoint**: Foundation ready. User story work can now proceed.

---

## Phase 3: User Story 1 - Profile the Protein Corpus (Priority: P1) 🎯 MVP

**Goal**: Parse every current `protein.faa` file, preserve provenance, and generate the core corpus-quality evidence needed before any tokenization choice is trusted.

**Independent Test**: Run `EDA.ipynb` with baseline config and verify that it discovers all current `.faa` files, produces raw sequence counts and distributions, emits residue/ambiguity summaries, reports parse issues, and saves sequence-stat and duplicate-summary artifacts.

### Implementation for User Story 1

- [ ] T010 [P] [US1] Extend FASTA parsing in `util/python/protein_fasta_io.py` to capture `assembly_id`, `file_path`, `sequence_id`, `raw_header`, `sequence`, and `sequence_length`
- [ ] T011 [P] [US1] Add raw sequence-stat and duplicate-summary export helpers in `util/python/protein_eda_artifacts.py`
- [ ] T012 [US1] Integrate full-corpus FASTA discovery and raw provenance table creation in `EDA.ipynb`
- [ ] T013 [US1] Add dynamic header-field extraction and malformed-header reporting cells in `EDA.ipynb`
- [ ] T014 [US1] Compute raw sequence length thresholds, amino-acid frequencies, and ambiguous-residue summaries in `EDA.ipynb`
- [ ] T015 [US1] Build raw-provenance and deduplicated-candidate duplicate views in `EDA.ipynb`
- [ ] T016 [US1] Generate raw-length, residue, ambiguity, and duplicate visualizations in `EDA.ipynb`
- [ ] T017 [US1] Save `sequence_stats.parquet`, `sequence_stats_preview.csv`, `duplicate_summary.parquet`, and `duplicate_summary_preview.csv` from `EDA.ipynb` into `data/interim/protein_eda/`

**Checkpoint**: User Story 1 should now provide a complete corpus profiling notebook slice that is independently runnable and reviewable.

---

## Phase 4: User Story 2 - Compare Tokenization Strategies for Pretraining Readiness (Priority: P2)

**Goal**: Compare single-token, 3-mer, 5-mer, and BPE strategies empirically and end with a defensible recommendation for pretraining-oriented preprocessing.

**Independent Test**: Run the tokenization-comparison sections of `EDA.ipynb` and verify that all four strategies produce comparable vocabulary, token-length, and exceedance outputs, with scope-aware artifact metadata and a final recommendation grounded in notebook evidence.

### Implementation for User Story 2

- [ ] T018 [P] [US2] Implement single-amino-acid and overlapping k-mer tokenization helpers in `util/python/tokenization_strategies.py`
- [ ] T019 [P] [US2] Implement BPE comparison helpers for fixed-grid and corpus-informed variants in `util/python/bpe_experiments.py`
- [ ] T020 [US2] Add scope-aware tokenization execution cells for `single`, `3-mer`, `5-mer`, and `BPE` in `EDA.ipynb`
- [ ] T021 [US2] Compute tokenized-length, vocabulary-size, frequency-distribution, and `> MAX_LENGTH` comparison tables in `EDA.ipynb`
- [ ] T022 [US2] Run and compare alternative residue-handling policies in `EDA.ipynb`, capturing explicit sensitivity tables for affected-sequence counts, token-length changes, and recommendation impact
- [ ] T023 [US2] Add sparsity, interpretability, and downstream-readiness proxy summaries in `EDA.ipynb`
- [ ] T023a [US2] Generate tokenized-length, exceedance, vocabulary, and residue-policy comparison plots in `EDA.ipynb` to show evidence for next suggested pretraining steps
- [ ] T024 [US2] Save `tokenization_comparison.parquet` and `tokenization_comparison_preview.csv` from `EDA.ipynb` into `data/interim/protein_eda/`
- [ ] T025 [US2] Add the evidence-based recommendation and caveats section in `EDA.ipynb`

**Checkpoint**: User Story 2 should now provide an independently reviewable tokenization-comparison and recommendation workflow on top of the shared parsing foundation.

---

## Phase 5: User Story 3 - Preserve Metadata for Future Functional Curation (Priority: P3)

**Goal**: Preserve FASTA header provenance and export metadata previews that support later curation without implying unsupported biological labels.

**Independent Test**: Run the metadata sections of `EDA.ipynb` and verify that raw headers are preserved, structured fields are exported dynamically, malformed headers are reported, and metadata preview artifacts are saved without asserting validated function labels.

### Implementation for User Story 3

- [ ] T026 [P] [US3] Implement structured-header extraction and malformed-header normalization helpers in `util/python/header_metadata.py`
- [ ] T027 [P] [US3] Add metadata-preview export helpers in `util/python/protein_eda_artifacts.py`
- [ ] T028 [US3] Integrate metadata-preview and malformed-header summary cells in `EDA.ipynb`
- [ ] T029 [US3] Add exploratory curation-hint analysis and provenance-linkage cells in `EDA.ipynb`
- [ ] T030 [US3] Save `header_metadata_preview.parquet` and `header_metadata_preview.csv` from `EDA.ipynb` into `data/interim/protein_eda/`

**Checkpoint**: User Story 3 should now provide an independently usable metadata-preservation and preview slice on top of the shared parsing foundation.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize reusable outputs, documentation, and rerunnable execution quality across all stories.

- [ ] T031 Emit `results/protein_eda/analysis_artifact_manifest.json` from `EDA.ipynb` using `util/python/protein_eda_artifacts.py`
- [ ] T032 Validate manifest/output behavior against `specs/001-protein-eda-tokenization/contracts/analysis-artifact-manifest.schema.json` and `specs/001-protein-eda-tokenization/contracts/eda-notebook-config.md`
- [ ] T033 Update `specs/001-protein-eda-tokenization/quickstart.md` if implementation-specific notebook paths, outputs, or dependency notes drift during delivery
- [ ] T034 Run full execution-order validation in `EDA.ipynb` and remove any exploratory cells that break the final Run All workflow

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion.
- **User Story 2 (Phase 4)**: Depends on Foundational completion and uses the parsing outputs established by shared notebook foundations.
- **User Story 3 (Phase 5)**: Depends on Foundational completion and uses the same provenance-preserving parsing outputs.
- **Polish (Phase 6)**: Depends on the user stories you intend to ship.

### User Story Dependencies

- **User Story 1 (P1)**: Primary MVP slice. No dependency on other user stories.
- **User Story 2 (P2)**: Uses shared parsing/provenance foundation but should remain independently reviewable once Phase 2 is complete.
- **User Story 3 (P3)**: Uses shared parsing/provenance foundation but should remain independently reviewable once Phase 2 is complete.

### Within Each User Story

- Helper-module work before notebook integration.
- Data production before visualization and artifact export.
- Artifact export before final recommendation or validation notes.

### Parallel Opportunities

- **Setup**: Minimal; `EDA.ipynb` skeleton and directory scaffolding are tightly coupled.
- **Foundational**: `util/python/protein_fasta_io.py`, `util/python/protein_eda_artifacts.py`, and `util/python/tokenization_strategies.py` can be created in parallel.
- **User Story 1**: Parsing-extension tasks and malformed-issue helper tasks can run in parallel before notebook integration.
- **User Story 2**: K-mer helper work and BPE helper work can run in parallel before notebook integration.
- **User Story 3**: Header-metadata helper work can proceed in parallel with non-conflicting artifact-validation preparation.

---

## Parallel Example: User Story 1

```bash
# Safe parallel helper work before notebook integration:
Task: "Extend FASTA parsing in util/python/protein_fasta_io.py to capture assembly_id, file_path, sequence_id, raw_header, sequence, and sequence_length"
Task: "Add raw sequence-stat and duplicate-summary export helpers in util/python/protein_eda_artifacts.py"
```

## Parallel Example: User Story 2

```bash
# Safe parallel helper work before notebook integration:
Task: "Implement single-amino-acid and overlapping k-mer tokenization helpers in util/python/tokenization_strategies.py"
Task: "Implement BPE comparison helpers for fixed-grid and corpus-informed variants in util/python/bpe_experiments.py"
```

## Parallel Example: User Story 3

```bash
# Limited but safe parallelism around metadata and final artifact checks:
Task: "Implement structured-header extraction and malformed-header normalization helpers in util/python/header_metadata.py"
Task: "Add metadata-preview export helpers in util/python/protein_eda_artifacts.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. Stop and validate the corpus-profiling notebook slice before adding tokenization-comparison complexity.

### Incremental Delivery

1. Build the notebook skeleton and shared helpers.
2. Deliver User Story 1 to establish trustworthy parsing, provenance, and corpus profiling.
3. Add User Story 2 to compare tokenization strategies and emit the recommendation section.
4. Add User Story 3 to strengthen metadata-preservation outputs for future curation.
5. Finish with full Run All validation and manifest/artifact contract checks.

### Parallel Team Strategy

1. One developer owns notebook structure and shared config/output plumbing.
2. One developer can work on helper modules for parsing/tokenization in parallel with artifact helper work.
3. After foundations land, one developer can focus on tokenization comparison while another finalizes metadata-preservation helpers and preview outputs.

---

## Notes

- `[P]` tasks indicate different files with no direct dependency on an incomplete task.
- Story labels map each implementation task back to the corresponding user story.
- This feature is notebook-centric, so parallelism is intentionally limited once work converges inside `EDA.ipynb`.
- Keep diffs minimal and scoped; avoid drive-by refactors outside the notebook/helpers/output paths above.
- Persisted table columns, JSON keys, and manifest keys must remain `snake_case`.
