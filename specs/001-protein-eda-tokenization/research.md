# Phase 0 Research: Protein Sequence EDA and Tokenization Strategy Evaluation for BERT Pretraining

## Decision 1: Notebook placement and execution model

- Decision: Implement the phase-1 workflow in a rerunnable root-level notebook named `EDA.ipynb`, with imports in the first cell, shared constants in the second cell, and subsequent work split into small exploratory cells.
- Rationale: The feature spec explicitly names `EDA.ipynb`, and the repository already contains a root-level exploratory notebook (`EDA_data.ipynb`), so this is consistent with existing practice while still following the constitution’s notebook workflow rules.
- Alternatives considered:
  - Place the notebook under `notebooks/`: rejected because the spec explicitly calls for `EDA.ipynb` and the repo already tolerates root-level exploratory notebooks.
  - Wrap the workflow into a Python script first: rejected because phase 1 is exploratory evidence gathering, not a batch CLI implementation.

## Decision 2: FASTA parsing and metadata preservation strategy

- Decision: Parse every current `protein.faa` record into a provenance-preserving raw table containing assembly identifier, file path, sequence identifier, full FASTA header, sequence text, sequence length, and dynamically extracted structured header fields. Treat any record or header that deviates from the standard format as malformed, preserve the raw content when possible, and report the issue in parse-error outputs.
- Rationale: The spec requires lossless provenance, explicit malformed-data reporting, and dynamic structured extraction without prematurely locking a canonical header schema.
- Alternatives considered:
  - Fail the entire notebook on first malformed record: rejected because the clarified spec prefers audit-tolerant parsing for evidence gathering.
  - Extract only raw headers with no structured fields: rejected because future curation requires more than opaque text.

## Decision 3: Tokenization comparison strategy

- Decision: Compare single amino acid, overlapping 3-mer, overlapping 5-mer, and BPE tokenization using empirical corpus-derived measurements. Run single/3-mer/5-mer statistics on the declared baseline `SAMPLE_MODE="all"` scope, while allowing explicit scope override for expensive BPE fitting and sensitivity analyses. Evaluate BPE using a small fixed vocabulary-size grid plus corpus-informed candidate sizes, and record the chosen scope in saved outputs.
- Rationale: This satisfies the clarified combination of full-corpus evidence gathering, explicit user-controlled scope overrides, and auditable BPE experimentation without turning phase 1 into uncontrolled tokenizer tuning.
- Alternatives considered:
  - Force all expensive tokenization work to full corpus only: rejected because runtime costs may become unreasonable.
  - Leave scope and BPE sizing entirely implicit: rejected because it would weaken reproducibility and artifact interpretation.

## Decision 4: Duplicate and ambiguous-residue handling strategy

- Decision: Preserve a full raw provenance view of all parsed records, generate a deduplicated candidate view for pretraining planning, and use one primary ambiguous-residue handling policy plus smaller sensitivity comparisons across the other supported policies.
- Rationale: This keeps the exploratory notebook scientifically honest about data redundancy and residue-policy sensitivity while preserving enough provenance for future downstream curation.
- Alternatives considered:
  - Deduplicate the entire dataset before all analyses: rejected because duplicate-rate evidence would be lost.
  - Use only one ambiguous-residue policy: rejected because it would hard-code a preprocessing assumption before enough evidence exists.

## Decision 5: Output artifact and dependency strategy

- Decision: Save large tabular outputs as both lightweight CSV previews and full Parquet artifacts, store figures and a run manifest under `results/protein_eda/`, and keep Python dependencies minimal by relying on standard library + `pandas`/`matplotlib` already signaled in the repository, adding only Parquet support and a notebook-suitable BPE library if missing from the environment.
- Rationale: CSV previews keep the workflow easy to inspect manually, Parquet supports larger tables and downstream reuse, and limiting dependencies aligns with the constitution’s dependency-hygiene rule.
- Alternatives considered:
  - CSV-only exports: rejected because large sequence tables will become unwieldy.
  - Parquet-only exports: rejected because quick manual inspection becomes less convenient.
