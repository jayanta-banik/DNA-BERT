# Quickstart: Discriminative Subsequence Tokenizer (DiST)

## Prerequisites

- Linux workspace with the project Python environment available via `source ~/venv3/bin/activate`
- Repository checked out at the current root
- A training-input folder containing one or more `.txt` shard files
- Each shard file contains one biological sequence per line; empty lines are allowed and ignored

## Training Data Layout

Example shard folder:

```text
data/interim/protein_tokenization/dist_corpus/
├── part-00000.txt
├── part-00001.txt
└── part-00002.txt
```

## Start a Python Session

```bash
source ~/venv3/bin/activate
cd scripts/python
python
```

## Train a Fresh Tokenizer

```python
from tokenizer_module import TfidfTokenizer

corpus_dir = "../../data/interim/protein_tokenization/dist_corpus"
save_dir = "../../results/protein_tokenization/artifacts/tokenizers/TFIDF/vocab8000_keep"

tokenizer = TfidfTokenizer(
    min_k=2,
    max_k=6,
    vocab_size=8000,
    tf_mode="log",
    idf_mode="smooth",
    scoring_mode="complexity_regularized_tfidf",
    rare_residue_policy="keep",
)

tokenizer.fit(corpus_dir, mode="fresh")
tokenizer.save(save_dir)
```

## Tokenize a Sequence

```python
tokens = tokenizer.tokenize("ACDEFGHIK")
print(tokens)
```

Expected behavior:

- Highest-score match is selected at each offset
- Longest match breaks score ties
- Earlier vocabulary insertion breaks remaining ties
- Single-character fallback or `unk_token` covers unmatched positions

## Tokenize a File

```python
batch_tokens = tokenizer.tokenize_file(
    "../../data/interim/protein_tokenization/sample_sequences.txt",
    output_path="../../results/protein_tokenization/artifacts/tokenizers/TFIDF/sample_tokenized.txt",
)

print(batch_tokens[0])
```

Expected behavior:

- Return value is `List[List[str]]`
- Output file contains one space-delimited tokenized sequence per line
- Empty input lines are skipped

## Load and Continue Training

```python
from tokenizer_module import TfidfTokenizer

more_corpus_dir = "../../data/interim/protein_tokenization/dist_corpus_round_2"

tokenizer = TfidfTokenizer.load(
    "../../results/protein_tokenization/artifacts/tokenizers/TFIDF/vocab8000_keep"
)
tokenizer.fit(more_corpus_dir, mode="continue")
tokenizer.save(
    "../../results/protein_tokenization/artifacts/tokenizers/TFIDF/vocab8000_keep_round_2"
)
```

## Validation Checklist

- Folder ingestion fails fast if the input path does not exist or contains no `.txt` shards
- Fresh training builds a vocabulary with mandatory special and single-character tokens present
- `tokenize()` reconstructs normalized input except at explicit `unk_token` substitutions
- Save/load round-trips preserve tokenization output for the same input
- Continue training increases total document count and can admit new high-scoring tokens
- Persisted state includes config, total document count, cumulative candidate stats, vocabulary order, and active vocabulary metadata
