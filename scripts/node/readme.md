# Node Scripts

Node.js scripts for crawling and ingestion workflows.

## AMR Annotation

Run the standalone AMR annotator with:

`OPENAI_API_KEY=... yarn annotate:amr -- --limit 20`

It reads `results/protein_tokenization/artifacts/semantic_annotation_matches.csv`, creates `results/protein_tokenization/artifacts/semantic_annotation_matches_checkpoint.csv` on first run, bootstraps prior Python results from `results/protein_tokenization/artifacts/semantic_annotation_amr_labels.csv`, and then processes pending rows in 5-wide batches staggered by 100 ms.
