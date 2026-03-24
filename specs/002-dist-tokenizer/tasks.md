# Tasks: Discriminative Subsequence Tokenizer (DiST)

**Input**: Design documents from `/specs/002-dist-tokenizer/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: No separate automated test tasks are included because the feature spec does not require TDD or a new test framework. Validation is captured as fixture-based manual verification tasks aligned to the acceptance scenarios and quickstart.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the new tokenizer module entrypoint and implementation handoff files.

- [x] T001 Create the `TfidfTokenizer` module scaffold in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T002 Prepare the feature execution checklist and validation examples in `specs/002-dist-tokenizer/quickstart.md`
- [x] T003 Confirm the public API handoff contract for implementation in `specs/002-dist-tokenizer/contracts/public-python-api.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared state, validation, and serialization infrastructure that all user stories rely on.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [x] T004 Define tokenizer config/state dataclasses and validation helpers in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T005 Define the custom encoding/introspection adapter used by `ProteinTokenizer`-compatible workflows in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T006 Define JSON state serialization helpers aligned to `specs/002-dist-tokenizer/contracts/tokenizer-state.schema.json` in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T007 Register `TfidfTokenizer` in `scripts/python/tokenizer_module/__init__.py`
- [x] T008 Document persisted tokenizer-state field expectations in `specs/002-dist-tokenizer/contracts/tokenizer-state.schema.json`

**Checkpoint**: Shared tokenizer infrastructure is ready; user story work can begin.

---

## Phase 3: User Story 1 - Train a Tokenizer on a Sharded Corpus Folder (Priority: P1) 🎯 MVP

**Goal**: Train a vocabulary from a folder of `.txt` shard files using observed substrings, corpus-wide TF, and per-sequence DF.

**Independent Test**: Train `TfidfTokenizer` on a small shard folder and verify scored vocabulary metadata plus mandatory single-character tokens.

- [x] T009 [US1] Implement shard-folder discovery and non-empty sequence streaming in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T010 [US1] Implement observed substring generation from `min_k` to `max_k` with corpus-wide TF and per-sequence DF accumulation in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T011 [US1] Implement default complexity-regularized scoring and ranked vocabulary construction with mandatory token injection in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T012 [US1] Implement fresh training flow in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T013 [US1] Validate fresh shard-folder training behavior using the scenarios in `specs/002-dist-tokenizer/spec.md`

**Checkpoint**: User Story 1 is independently functional and provides the MVP training workflow.

---

## Phase 4: User Story 2 - Tokenize a New Sequence (Priority: P1)

**Goal**: Segment a new sequence with highest-score greedy matching, longest-match tie-breaking, and deterministic fallback behavior.

**Independent Test**: Tokenize a normalized sequence and verify full coverage, deterministic tie-breaking, and fallback behavior.

- [x] T014 [US2] Build deterministic vocabulary ordering and lightweight token lookup indexing in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T015 [US2] Implement greedy `tokenize(sequence)` matching with highest-score and longest-match selection in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T016 [US2] Implement vocabulary-order final tie-breaking plus single-character and `unk_token` fallback behavior in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T017 [US2] Implement `encode()` output compatibility for tokenized sequences in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T018 [US2] Validate tokenization coverage and deterministic tie-break behavior using the scenarios in `specs/002-dist-tokenizer/spec.md`

**Checkpoint**: User Story 2 is independently functional on top of the trained vocabulary.

---

## Phase 5: User Story 3 - Save and Load a Trained Tokenizer (Priority: P1)

**Goal**: Persist and restore the tokenizer without losing config, vocabulary order, scores, or cumulative corpus statistics.

**Independent Test**: Save a trained tokenizer, load it back, and verify identical tokenization output for the same sequence.

- [x] T019 [US3] Implement JSON save-path handling and persisted tokenizer-state payload generation in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T020 [US3] Implement `@classmethod load()` and restore trained tokenizer state in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T021 [US3] Preserve vocabulary order, token metadata, and cumulative candidate stats through save/load in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T022 [US3] Validate save/load round-trip behavior against `specs/002-dist-tokenizer/contracts/tokenizer-state.schema.json`

**Checkpoint**: User Story 3 is independently functional and enables reusable trained tokenizers.

---

## Phase 6: User Story 4 - Tokenize a Corpus File (Priority: P2)

**Goal**: Tokenize a plain-text sequence file line by line and optionally write space-delimited output.

**Independent Test**: Tokenize a small input file, confirm `List[List[str]]` return shape, and verify the optional output file contents.

- [x] T023 [US4] Implement `tokenize_file(input_path, output_path=None)` with empty-line skipping in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T024 [US4] Implement space-delimited output serialization for `tokenize_file` in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T025 [US4] Validate batch file tokenization behavior using the scenarios in `specs/002-dist-tokenizer/spec.md`

**Checkpoint**: User Story 4 is independently functional for batch tokenization workflows.

---

## Phase 7: User Story 5 - Continue Training on a Second Corpus (Priority: P2)

**Goal**: Merge new shard-folder statistics into an existing tokenizer state and rerank the active vocabulary.

**Independent Test**: Load a saved tokenizer, continue training on a second shard folder, and verify document-count growth plus token admission/pruning.

- [x] T026 [US5] Implement cumulative state merge for `fit(path, mode="continue")` in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T027 [US5] Implement `merge_strategy` handling and `continue_fit(path)` in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T028 [US5] Recompute global IDF/scores, rerank vocabulary, and admit/prune tokens after merged training in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T029 [US5] Validate continued-training equivalence and vocabulary updates using the scenarios in `specs/002-dist-tokenizer/spec.md`

**Checkpoint**: User Story 5 is independently functional for incremental retraining workflows.

---

## Phase 8: User Story 6 - Configure Scoring and Filtering (Priority: P2)

**Goal**: Support alternate TF, IDF, scoring, and low-complexity filtering modes beyond the default training path.

**Independent Test**: Train on the same shard folder under multiple scoring/filter settings and verify score and vocabulary differences.

- [x] T030 [US6] Implement configurable `tf_mode` and `idf_mode` calculation branches in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T031 [US6] Implement configurable `scoring_mode`, `alpha`, and low-complexity filtering logic in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T032 [US6] Validate alternate scoring and filtering outcomes using the scenarios in `specs/002-dist-tokenizer/spec.md`

**Checkpoint**: User Story 6 is independently functional for scoring experimentation.

---

## Phase 9: User Story 7 - Residue Normalization and Rare Residue Handling (Priority: P3)

**Goal**: Support configurable rare-residue policies during training and tokenization.

**Independent Test**: Train and tokenize sequences containing rare residues under each configured policy and verify normalization outcomes.

- [x] T033 [US7] Integrate configurable rare-residue and fallback-residue handling into training/tokenization normalization in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T034 [US7] Preserve mandatory single-character and `unk_token` behavior for rare and invalid residues in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T035 [US7] Validate rare-residue policy behavior using the scenarios in `specs/002-dist-tokenizer/spec.md`

**Checkpoint**: User Story 7 is independently functional for non-standard residue inputs.

---

## Phase 10: User Story 8 - Fresh Retraining (Priority: P3)

**Goal**: Explicitly reset prior training state while preserving config defaults when `mode="fresh"` is called on an already trained tokenizer.

**Independent Test**: Train on one shard folder, retrain fresh on another, and verify that only the second corpus contributes to the resulting statistics.

- [x] T036 [US8] Implement explicit trained-state reset semantics for `fit(path, mode="fresh")` in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T037 [US8] Preserve configuration defaults across fresh retraining in `scripts/python/tokenizer_module/tfidf_tokenizer.py`
- [x] T038 [US8] Validate retrain-from-scratch behavior using the scenarios in `specs/002-dist-tokenizer/spec.md`

**Checkpoint**: User Story 8 is independently functional for resetting and rebuilding tokenizer state.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, docs alignment, and end-to-end validation across all stories.

- [x] T039 [P] Reconcile final public API examples with the implementation in `specs/002-dist-tokenizer/contracts/public-python-api.md`
- [x] T040 [P] Reconcile final tokenizer-state details with the implementation in `specs/002-dist-tokenizer/contracts/tokenizer-state.schema.json`
- [x] T041 Run the end-to-end validation checklist and capture any required documentation corrections in `specs/002-dist-tokenizer/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories
- **User Stories (Phases 3-10)**: Depend on Foundational completion
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P1)**: Depends on US1 because tokenization requires a trained vocabulary
- **US3 (P1)**: Depends on US1 because persistence requires trained tokenizer state
- **US4 (P2)**: Depends on US2 because batch tokenization builds on single-sequence tokenization
- **US5 (P2)**: Depends on US1 and US3 because continued training requires saved cumulative state
- **US6 (P2)**: Depends on US1 because alternative scoring/filtering extends the training path
- **US7 (P3)**: Depends on US1 because rare-residue handling is exercised through training/tokenization
- **US8 (P3)**: Depends on US1 because fresh retraining resets an already trained tokenizer

### Within Each User Story

- Implement core state and parsing helpers before higher-level workflow methods
- Complete the story’s validation task before moving to lower-priority stories
- Keep diffs scoped to `scripts/python/tokenizer_module/` plus the feature docs/contracts files listed above

### Parallel Opportunities

- `T039` and `T040` can run in parallel during the polish phase
- After Phase 2, documentation-only validation updates can proceed in parallel with code review if implementation is stable
- Most implementation tasks are intentionally sequential because the feature is concentrated in `scripts/python/tokenizer_module/tfidf_tokenizer.py`

---

## Parallel Example: Polish Phase

```bash
Task: "Reconcile final public API examples with the implementation in specs/002-dist-tokenizer/contracts/public-python-api.md"
Task: "Reconcile final tokenizer-state details with the implementation in specs/002-dist-tokenizer/contracts/tokenizer-state.schema.json"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Complete Phase 4: User Story 2
5. Complete Phase 5: User Story 3
6. **Stop and validate**: fresh training, single-sequence tokenization, and save/load round-trip

### Incremental Delivery

1. Deliver MVP with US1-US3
2. Add US4 for file tokenization
3. Add US5 for continued training
4. Add US6 for scoring/filter experimentation
5. Add US7 and US8 for residue-policy coverage and explicit retraining semantics
6. Finish with Phase 11 polish tasks

### Suggested Story Completion Order

1. US1 → US2 → US3
2. US4 → US5 → US6
3. US7 → US8

---

## Notes

- All tasks use the required checklist format: `- [ ] T### [P?] [US?] Description with file path`
- No automated test-framework tasks are included because the feature spec does not require TDD and the repository has no existing Python test harness
- Validation tasks point to the existing feature spec and quickstart so the implementation remains traceable to the approved behavior
- Keep changes minimal and avoid unrelated refactors outside `scripts/python/tokenizer_module/`
