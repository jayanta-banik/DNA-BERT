# Implementation Plan: Protein Sequence EDA and Tokenization Strategy Evaluation for BERT Pretraining

**Branch**: `001-protein-eda-tokenization` | **Date**: 2026-03-08 | **Spec**: `/specs/001-protein-eda-tokenization/spec.md`
**Input**: Feature specification from `/specs/001-protein-eda-tokenization/spec.md`

## Summary

Build a rerunnable notebook-first EDA workflow in `EDA.ipynb` that parses all current `protein.faa` files under the NCBI dehydrated dataset tree, preserves provenance and FASTA headers, compares single-token, overlapping 3-mer, overlapping 5-mer, and BPE tokenization strategies, saves CSV preview plus Parquet analysis artifacts, and ends with an evidence-based recommendation for pretraining setup.

## Technical Context

**Language/Version**: Python in Jupyter notebook workflow using the existing `~/venv3` environment  
**Primary Dependencies**: Python standard library, `pandas`, `matplotlib`, `numpy`, `pyarrow` for Parquet export, and a BPE tokenizer library suitable for notebook-side corpus fitting such as `sentencepiece`  
**Storage**: Local filesystem (`data/raw/` FASTA corpus, `data/interim/` tabular outputs, `results/` figures/manifests)  
**Testing**: Run All notebook validation, artifact existence/schema checks, and spot-check data assertions on parsed counts and output tables  
**Target Platform**: Linux Jupyter environment with the existing `venv3` activated or available via `source ~/venv3/bin/activate`  
**Project Type**: Exploratory notebook and file-backed data-analysis workflow  
**Performance Goals**: Parse the current corpus (`22,141` `protein.faa` files) in a single rerunnable notebook workflow, compute corpus-wide descriptive statistics on the full dataset, and keep expensive tokenization comparisons explicitly scope-controlled and auditable  
**Constraints**: Notebook imports first and shared constants second, Run All safe cell order, fail-fast config validation, no silent fallback, preserve raw FASTA/header provenance, save file-facing schemas in `snake_case`, and record scope overrides for expensive analyses  
**Scale/Scope**: Current corpus spans `22,141` FASTA files with sequence count determined at runtime, full-corpus parsing is in scope, and tokenization comparison may mix full-corpus and explicitly overridden scopes depending on user-selected runtime configuration

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
- [x] If notebooks are in scope, the first cell contains imports and the second cell
      defines shared constants/parameters
- [x] If notebooks are in scope, cell order is Run All safe, work is split into small
      logical cells, and invalid assumptions fail fast
- [x] If notebooks are in scope, functions are added only for reuse/repetition and the
      final notebook preserves an exploratory but rerunnable workflow
- [x] `.specify/memory/*` reviewed (including `UI_BEHAVIOR_STANDARDS.md` and
      `LEARNINGS.md` when present)

## Phase 0 Research Summary

Research decisions are documented in `/specs/001-protein-eda-tokenization/research.md` and resolve notebook placement, FASTA/header parsing policy, BPE evaluation strategy, duplicate/residue handling, and output artifact conventions.

## Phase 1 Design Summary

- Data model defined in `/specs/001-protein-eda-tokenization/data-model.md`
- Contracts defined in `/specs/001-protein-eda-tokenization/contracts/`
- Execution runbook defined in `/specs/001-protein-eda-tokenization/quickstart.md`

## Post-Design Constitution Re-Check

- [x] Design remains notebook-first and scoped to phase-1 evidence gathering
- [x] Persisted table/manifest keys remain `snake_case`
- [x] Planned Python variables and constants follow repository naming rules
- [x] New dependencies are limited to those needed for Parquet output and BPE comparison
- [x] Notebook design preserves imports-first/config-second and Run All safety

## Project Structure

### Documentation (this feature)

```text
specs/001-protein-eda-tokenization/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── analysis-artifact-manifest.schema.json
│   └── eda-notebook-config.md
└── tasks.md
```

### Source Code (repository root)

```text
EDA.ipynb

data/
├── raw/
│   └── prot_only_dehydrated/
│       └── ncbi_dataset/
│           └── data/
├── interim/
│   └── protein_eda/
│       ├── sequence_stats.parquet
│       ├── sequence_stats_preview.csv
│       ├── tokenization_comparison.parquet
│       ├── tokenization_comparison_preview.csv
│       ├── duplicate_summary.parquet
│       ├── duplicate_summary_preview.csv
│       ├── header_metadata_preview.parquet
│       └── header_metadata_preview.csv
└── processed/

results/
└── protein_eda/
    ├── figures/
    └── analysis_artifact_manifest.json

util/
└── python/
    └── (optional) shared parsing or tokenization helpers only if notebook repetition justifies extraction
```

**Structure Decision**: Keep the feature notebook at repository root as `EDA.ipynb` to match the feature spec and existing root-level exploratory notebook pattern (`EDA_data.ipynb`). Save reusable tables under `data/interim/protein_eda/` and figures/manifests under `results/protein_eda/`. Only extract helper code into `util/python/` if notebook repetition materially harms readability.

## Phase 2 Planning Preview (for `/speckit.tasks`)

1. Create or update `EDA.ipynb` with imports-first and config-second cells.
2. Implement full-corpus FASTA discovery, parsing, provenance capture, and parse-error reporting.
3. Add raw sequence profiling, residue distribution analysis, malformed-header reporting, and duplicate analysis.
4. Add tokenization simulation and comparison for single, 3-mer, 5-mer, and BPE strategies with scope-aware execution.
5. Persist CSV preview plus Parquet artifacts and an analysis manifest.
6. Add metadata curation preview and final recommendation sections.
7. Validate Run All execution order and artifact outputs.

## Complexity Tracking

No constitution violations requiring justification.
