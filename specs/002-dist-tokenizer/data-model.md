# Data Model: Discriminative Subsequence Tokenizer (DiST)

## Entity: TokenizerConfig

- Description: Complete runtime and persistence configuration for one tokenizer instance.
- Fields:
  - `unk_token` (string, required)
  - `special_tokens` (array of strings, required)
  - `standard_residues` (array of strings, required)
  - `rare_residues` (array of strings, required)
  - `rare_residue_policy` (enum: `keep`, `replace_with_unk`, `replace_with_nn`, required)
  - `fallback_residue` (string, optional)
  - `normalize` (boolean, required)
  - `case_sensitive` (boolean, required)
  - `min_k` (integer, required)
  - `max_k` (integer, required)
  - `min_tf` (integer, required)
  - `min_df` (integer, required)
  - `vocab_size` (integer, required)
  - `tf_mode` (enum: `raw`, `log`, required)
  - `idf_mode` (enum: `standard`, `smooth`, `probabilistic`, required)
  - `scoring_mode` (enum: `tfidf`, `log_tfidf`, `complexity_regularized_tfidf`, required)
  - `alpha` (number, required)
  - `filter_low_complexity` (boolean, required)
  - `low_complexity_threshold` (number, required)
  - `search_method` (enum: `brute`, `beam`, required)
  - `merge_strategy` (enum: `accumulate`, `replace_vocab`, `freeze_vocab`, required)
  - `beam_width` (integer, optional)
- Validation Rules:
  - `min_k` must be `>= 1` and `max_k` must be `>= min_k`.
  - `vocab_size`, `min_tf`, and `min_df` must be positive integers.
  - `low_complexity_threshold` must be within `[0.0, 1.0]`.
  - `beam_width` is required only when `search_method = beam`.

## Entity: CorpusShard

- Description: One `.txt` file inside the training-input folder.
- Fields:
  - `path` (string, required)
  - `shard_name` (string, required)
  - `document_count` (integer, required)
  - `is_empty` (boolean, required)
- Validation Rules:
  - Only files with `.txt` suffix participate in training.
  - Empty lines do not contribute to `document_count`.

## Entity: SequenceDocument

- Description: One normalized non-empty sequence line consumed during training or tokenization.
- Fields:
  - `raw_sequence` (string, required)
  - `normalized_sequence` (string, required)
  - `source_shard` (string, optional)
  - `line_number` (integer, optional)
  - `contains_unknown_output` (boolean, required)
- Validation Rules:
  - `normalized_sequence` may be shorter than `min_k`, but it must still be tokenizable through single-character fallback or `unk_token`.

## Entity: CandidateTokenStat

- Description: Cumulative statistics for one observed substring candidate across all seen corpora.
- Fields:
  - `token` (string, required)
  - `length` (integer, required)
  - `tf` (integer, required)
  - `df` (integer, required)
  - `idf` (number, required)
  - `complexity` (number, required)
  - `length_bonus` (number, required)
  - `score` (number, required)
  - `is_low_complexity_filtered` (boolean, required)
- Validation Rules:
  - `tf >= df >= 1` for all observed candidates retained in cumulative stats.
  - `complexity` is `len(set(token)) / len(token)` and must lie in `(0.0, 1.0]`.

## Entity: VocabularyEntry

- Description: One token present in the active vocabulary used during tokenization.
- Fields:
  - `token` (string, required)
  - `token_id` (integer, required)
  - `vocabulary_order` (integer, required)
  - `token_type` (enum: `special`, `single_character`, `learned`, required)
  - `length` (integer, required)
  - `tf` (integer, required)
  - `df` (integer, required)
  - `idf` (number, required)
  - `complexity` (number, required)
  - `score` (number, required)
- Validation Rules:
  - Mandatory tokens (`special`, `single_character`, `unk_token`) remain present even when score-based pruning would otherwise remove them.
  - `vocabulary_order` is stable across save/load and drives the final tie-break rule.

## Entity: TokenizerState

- Description: Persisted state sufficient to restore a trained tokenizer and continue training.
- Fields:
  - `format_version` (string, required)
  - `tokenizer_name` (string, required)
  - `config` (TokenizerConfig, required)
  - `total_documents` (integer, required)
  - `total_shards` (integer, required)
  - `candidate_stats` (map of token string to CandidateTokenStat, required)
  - `vocabulary` (array of VocabularyEntry, required)
  - `saved_at` (string timestamp, optional)
- Validation Rules:
  - Continued training is supported only when `candidate_stats` and `total_documents` are present.
  - `format_version` gates future backward-compatibility decisions.

## Entity: TokenizedSequence

- Description: One tokenization result produced from an input sequence.
- Fields:
  - `input_sequence` (string, required)
  - `normalized_sequence` (string, required)
  - `tokens` (array of strings, required)
  - `token_ids` (array of integers, optional)
  - `contains_unk` (boolean, required)
- Validation Rules:
  - Concatenating `tokens` after removing special formatting must reconstruct the normalized sequence, except where `unk_token` intentionally replaces invalid characters.

## State Transitions

- `untrained` → `trained_fresh`: `fit(path, mode="fresh")`
- `trained_fresh` → `trained_continued`: `fit(path, mode="continue")` or `continue_fit(path)`
- `trained_continued` → `trained_continued`: repeated continue-training on additional shard folders
- `trained_*` → `trained_fresh`: a new `mode="fresh"` run replaces prior corpus statistics while preserving configuration defaults unless explicitly overridden
