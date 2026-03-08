# Quickstart: Protein Sequence EDA and Tokenization Strategy Evaluation for BERT Pretraining

## Prerequisites

- Python virtual environment available at `~/venv3`
- Jupyter notebook execution environment using the already-initialized shell or manual activation via:

```bash
source ~/venv3/bin/activate
```

- Current protein FASTA corpus available under:

```text
data/raw/prot_only_dehydrated/ncbi_dataset/data/
```

- Notebook dependencies available for:
  - table operations
  - plotting
  - Parquet export
  - BPE tokenizer fitting/comparison

## Notebook Target

- Primary notebook: `EDA.ipynb`

## Configure

1. Open `EDA.ipynb`.
2. Keep the first cell dedicated to imports.
3. Keep the second cell dedicated to global configuration constants.
4. Set or confirm the baseline config values:

```python
DATA_ROOT = "data/raw/prot_only_dehydrated/ncbi_dataset/data"
MAX_LENGTH = 512
TOKENIZATION_STRATEGIES = ["single", "3-mer", "5-mer", "BPE"]
AMBIGUOUS_RESIDUE_MODE = "keep"
RARE_RESIDUE_POLICY = "replace_with_unk"
SAMPLE_MODE = "all"
```

5. If expensive tokenization comparison should run on a narrower scope, set the explicit override in the config block and ensure the notebook records that override in outputs.

## Run

1. Start the notebook kernel from the `venv3` environment.
2. Execute the notebook with Run All.
3. Review the displayed outputs in this order:
   - corpus parsing summary
   - parse-error and malformed-header summary
   - raw sequence statistics and plots
   - duplicate analysis
   - tokenization comparison outputs
   - metadata preview outputs
   - final recommendation section

## Expected Saved Outputs

Tables under `data/interim/protein_eda/`:

- `sequence_stats.parquet`
- `sequence_stats_preview.csv`
- `tokenization_comparison.parquet`
- `tokenization_comparison_preview.csv`
- `duplicate_summary.parquet`
- `duplicate_summary_preview.csv`
- `header_metadata_preview.parquet`
- `header_metadata_preview.csv`

Results under `results/protein_eda/`:

- figure files for required plots
- `analysis_artifact_manifest.json`

## Validation Checklist

- The notebook runs top-to-bottom without reordering cells.
- Invalid config values fail fast with a clear error.
- All current `protein.faa` files are included in corpus discovery.
- Parse issues and malformed headers are reported instead of silently ignored.
- Raw provenance and deduplicated candidate outputs remain distinct.
- Tokenization artifacts record whether they used baseline `SAMPLE_MODE="all"` or an explicit scope override.
- Large tables are saved as Parquet and human-inspection previews are available as CSV.
