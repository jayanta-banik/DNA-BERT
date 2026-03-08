# Contract: EDA Notebook Configuration and Runtime Behavior

## Notebook Entrypoint

- Notebook: `EDA.ipynb`
- Execution mode: Run All in a Jupyter kernel backed by the existing `~/venv3` environment

## Configuration Contract

The second notebook cell defines the shared runtime constants. Required keys:

- `DATA_ROOT`
- `MAX_LENGTH`
- `TOKENIZATION_STRATEGIES`
- `AMBIGUOUS_RESIDUE_MODE`
- `RARE_RESIDUE_POLICY`
- `SAMPLE_MODE`

Baseline documented values:

- `DATA_ROOT="data/raw/prot_only_dehydrated/ncbi_dataset/data"`
- `MAX_LENGTH=512`
- `TOKENIZATION_STRATEGIES=["single", "3-mer", "5-mer", "BPE"]`
- `SAMPLE_MODE="all"`

Optional explicit overrides may narrow the scope of expensive tokenization-comparison work, but those overrides must be recorded in displayed outputs and saved artifacts.

## Validation Contract

- Invalid tokenization strategies or residue-policy values fail fast.
- Missing or unreadable data roots fail fast.
- Baseline corpus parsing still uses the declared `SAMPLE_MODE="all"` default unless an explicit override is documented.

## Runtime Behavior Contract

- Imports appear in notebook cell 1.
- Shared configuration appears in notebook cell 2.
- Parsing and statistics cells precede recommendation cells.
- Malformed FASTA records or headers are reported and summarized instead of silently ignored.
- Raw provenance outputs and deduplicated planning outputs remain distinct.

## Output Contract

- Large reusable tables are saved as both Parquet and CSV preview artifacts.
- Figures and an analysis manifest are saved under `results/protein_eda/`.
- Saved artifact keys and persisted column names use `snake_case`.
