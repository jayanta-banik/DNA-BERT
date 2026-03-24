# Implementation Plan: Discriminative Subsequence Tokenizer (DiST)

**Branch**: `002-dist-tokenizer` | **Date**: 2026-03-23 | **Spec**: `/specs/002-dist-tokenizer/spec.md`
**Input**: Feature specification from `/specs/002-dist-tokenizer/spec.md`

## Summary

Add a new Python tokenizer module that learns a discriminative subsequence vocabulary from a folder of `.txt` corpus shards by streaming observed substrings, computing corpus-wide TF and per-sequence DF, ranking tokens with configurable TF-IDF-style scoring, and persisting enough cumulative statistics to support deterministic save/load and continued training.

## Technical Context

**Language/Version**: Python 3.12.3 using the repository-selected system interpreter  
**Primary Dependencies**: Python standard library (`collections`, `dataclasses`, `json`, `math`, `pathlib`, `typing`) plus the existing `scripts/python/tokenizer_module` abstractions (`ProteinTokenizer`, `SequenceNormalizer`)  
**Storage**: Local filesystem (folder of `.txt` shard files for training input, JSON state files for saved tokenizer artifacts)  
**Testing**: Manual Python validation using acceptance-scenario fixture shards, save/load round-trip checks, continue-training equivalence checks, and fail-fast config/error-path assertions; no existing automated Python test framework is present  
**Target Platform**: Linux Python environment in the current repository workspace  
**Project Type**: Python library module with file-backed persistence  
**Performance Goals**: Train on 10k+ sequences and produce a ranked vocabulary up to the configured `vocab_size` on a standard workstation while streaming shard files and avoiding full-corpus retention in memory  
**Constraints**: Deterministic token ordering, `snake_case` JSON keys, no unnecessary new dependencies, observed-substring counting only, continued-training state must preserve cumulative candidate statistics, and the implementation must fit the existing `tokenizer_module` factory/normalization patterns  
**Scale/Scope**: One or more shard files, each containing one sequence per line; potentially large enough that counting must proceed line-by-line with a corpus-wide hashmap of observed substrings between `min_k` and `max_k`

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

Research decisions are documented in `/specs/002-dist-tokenizer/research.md` and resolve integration with the existing tokenizer module, shard-streaming statistics, JSON persistence for continued training, validation strategy without a new test framework, and the default search/indexing approach.

## Phase 1 Design Summary

- Data model defined in `/specs/002-dist-tokenizer/data-model.md`
- Contracts defined in `/specs/002-dist-tokenizer/contracts/`
- Execution runbook defined in `/specs/002-dist-tokenizer/quickstart.md`

## Post-Design Constitution Re-Check

- [x] Design remains scoped to one new tokenizer module plus minimal registry wiring
- [x] Persisted JSON state keys remain `snake_case`
- [x] Python variable names and constants follow repository naming rules
- [x] No new dependency is required beyond standard library plus existing tokenizer-module helpers
- [x] Planned module boundaries reuse the current `tokenizer_module` structure instead of introducing a new architecture

## Project Structure

### Documentation (this feature)

```text
specs/002-dist-tokenizer/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── public-python-api.md
│   └── tokenizer-state.schema.json
└── tasks.md
```

### Source Code (repository root)

```text
scripts/
└── python/
    └── tokenizer_module/
        ├── __init__.py
        ├── base.py
        ├── seq_normalizer.py
        └── tfidf_tokenizer.py

results/
└── protein_tokenization/
    └── artifacts/
        └── tokenizers/
            └── TFIDF/
                └── (user-selected save directories during manual validation)

data/
└── (user-supplied folder of `.txt` corpus shards outside the module contract)
```

**Structure Decision**: Add one new module at `scripts/python/tokenizer_module/tfidf_tokenizer.py` and update `scripts/python/tokenizer_module/__init__.py` to register it. Reuse `base.py` and `seq_normalizer.py` without introducing a separate service, CLI, or notebook workflow. Persistence remains file-backed and user-directed rather than hard-wired to a new output tree.

## Phase 2 Planning Preview (for `/speckit.tasks`)

1. Implement `TfidfTokenizer` configuration validation, normalization wiring, and internal encoding adapter.
2. Implement shard-folder ingestion with observed-substring counting, corpus-wide TF, and per-sequence DF updates.
3. Implement scoring, low-complexity filtering, mandatory token injection, and deterministic vocabulary construction.
4. Implement greedy tokenization, fallback behavior, and vocabulary-order tie-breaking.
5. Implement JSON save/load and continued-training state merge behavior.
6. Register the tokenizer in `tokenizer_module.__init__` and align introspection helpers with the custom tokenizer backend.
7. Validate fresh training, continued training, tokenize/tokenize_file behavior, and save/load round-trips with fixture shard folders.

## Complexity Tracking

No constitution violations requiring justification.
