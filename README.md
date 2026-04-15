# DNA-BERT

DNA-BERT is a bioinformatics workspace for collecting bacterial genome-derived protein data, exploring protein sequence distributions, building tokenization pipelines, and preparing inputs for BERT-style modeling experiments.

## Repository Overview

The repository combines:

- Node.js scripts for crawling and dataset indexing.
- Python notebooks and modules for exploratory analysis, tokenization, and modeling.
- Structured data directories for raw, interim, processed, and external artifacts.
- Specs and research notes that document planned and completed workflows.

## Repository Layout

```text
.
|- data/        # Raw, interim, processed, and external datasets
|- docs/        # Project documentation and methodology notes
|- notebooks/   # Notebook-based experiments and analysis
|- results/     # Output datasets, figures, and derived artifacts
|- scripts/     # Node.js and Python automation scripts
|- specs/       # Feature specs, plans, and task breakdowns
|- util/        # Shared utility code
```

## Prerequisites

- Linux environment
- Yarn 1.x for Node.js dependencies
- Python environment for notebooks and modeling workflows
- NCBI Datasets CLI for downloading genome and protein data

## Install the NCBI Datasets CLI

Download the latest Linux binary and place it on your `PATH`:

```bash
curl -o datasets \
	https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/LATEST/linux-amd64/datasets
chmod +x datasets
sudo mv datasets /usr/local/bin/
datasets version
```

## Download Bacterial Genome Protein Data

Download a dehydrated bacteria genome dataset that includes protein records:

```bash
cd data/raw/
datasets download genome taxon bacteria \
	--dehydrated \
	--include protein \
	--filename bacteria_dataset.zip
```

Extract the archive:

```bash
unzip bacteria_dataset.zip -d bacteria_dataset
```

Rehydrate the downloaded dataset:

```bash
datasets rehydrate --directory bacteria_dataset
```

## Data Organization

The main dataset folders follow a standard pipeline layout:

- `data/raw/`: Original downloaded or source data
- `data/interim/`: Cleaned or transformed intermediate artifacts
- `data/processed/`: Analysis-ready or model-ready datasets
- `data/external/`: Third-party or reference datasets

## Scripts

- `scripts/node/`: Crawling, indexing, and ETL scripts
- `scripts/python/`: Exploratory analysis, tokenization, and modeling assets

## Outputs

Generated outputs are primarily stored in:

- `results/`: JSONL indexes, figures, tokenization outputs, and analysis artifacts
- `data/interim/`: Intermediate corpora and tokenized text
- `data/processed/`: Processed datasets prepared for downstream use

## Notes

- Some workflows are notebook-driven and live under `scripts/python/` and `notebooks/`.
- Planning and implementation details for major features live under `specs/`.
