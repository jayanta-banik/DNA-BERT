# DNA-BERT Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-04

## Active Technologies
- Python in Jupyter notebook workflow using the existing `~/venv3` environment + Python standard library, `pandas`, `matplotlib`, `numpy`, `pyarrow` for Parquet export, and a BPE tokenizer library suitable for notebook-side corpus fitting such as `sentencepiece` (001-protein-eda-tokenization)
- Local filesystem (`data/raw/` FASTA corpus, `data/interim/` tabular outputs, `results/` figures/manifests) (001-protein-eda-tokenization)

- JavaScript (Node.js ESM; version managed by project runtime) + `got`, `cheerio`, `cli-progress`, `p-limit` (001-ncbi-bacteria-crawler)

## Project Structure

```text
src/
tests/
```

## Commands

npm test && npm run lint

## Code Style

JavaScript (Node.js ESM; version managed by project runtime): Follow standard conventions

## Recent Changes
- 001-protein-eda-tokenization: Added Python in Jupyter notebook workflow using the existing `~/venv3` environment + Python standard library, `pandas`, `matplotlib`, `numpy`, `pyarrow` for Parquet export, and a BPE tokenizer library suitable for notebook-side corpus fitting such as `sentencepiece`

- 001-ncbi-bacteria-crawler: Added JavaScript (Node.js ESM; version managed by project runtime) + `got`, `cheerio`, `cli-progress`, `p-limit`

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
