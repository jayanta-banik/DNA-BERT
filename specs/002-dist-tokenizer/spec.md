# Feature Specification: Discriminative Subsequence Tokenizer (DiST)

**Feature Branch**: `002-dist-tokenizer`
**Created**: 2026-03-23
**Status**: Draft
**Input**: User description: "Build a Python tokenizer that learns a vocabulary from biological sequences using a configurable TF-IDF-based scoring framework with optional low-complexity filtering and residue normalization. The tokenizer must support training from a folder of plain text corpus shards, tokenizing new sequences, saving/loading the learned vocabulary, and incremental continued training."

## Compliance Notes _(mandatory)_

- **Relevant Constitution Principles**:
  - **I. Semantic Integrity**: The tokenizer handles genomic/protein domain data; scoring formulas and residue normalization must be implemented exactly as specified, with no guessed domain logic.
  - **II. Minimal Diffs**: Implementation should reuse existing patterns from `scripts/python/tokenizer_module/` where appropriate (e.g., base class conventions, normalizer patterns).
  - **IV. Prefer Existing Patterns**: The new `TfidfTokenizer` class should follow the module structure and naming patterns established by the existing tokenizer module (`base.py`, `*_tokenizer.py`).
  - **V. Naming Discipline**: Python code uses `snake_case` for variables, `UPPER_SNAKE_CASE` for constants. JSON keys saved to files use `snake_case`.
- **Notebook Workflow Constraints**: N/A — this feature is a pure Python module, not a notebook.
- **UI Behavior Standards Applied**: N/A — `.specify/memory/UI_BEHAVIOR_STANDARDS.md` absent.
- **Cross-Feature Learnings Applied**: N/A — `.specify/memory/LEARNINGS.md` absent.
- **Conflicts & Resolution**: None identified. The new tokenizer module fits naturally alongside existing tokenizer implementations.

## Clarifications

### Session 2026-03-23

- Q: How should training input and TF scope work for corpus ingestion? → A: Training input is a folder of `.txt` files treated as corpus shards, and TF is computed corpus-wide across all shards using aggregated substring counts.
- Q: How should tokenization break ties after score and length are tied? → A: Prefer the token inserted earlier into the vocabulary.
- Q: How should document frequency be counted across shard files? → A: Count the number of non-empty sequence lines containing the token across all shard files.
- Q: Which candidate substrings should be counted for vocabulary construction? → A: Count only substrings actually observed in the corpus shards, then rank and prune to `vocab_size`.
- Q: What should `tokenize_file` return and write? → A: Return `List[List[str]]`; if `output_path` is provided, write each tokenized sequence as a space-delimited line.

## User Scenarios & Testing _(mandatory)_

### User Story 1 — Train a Tokenizer on a Sharded Corpus Folder (Priority: P1)

A bioinformatics researcher has a folder containing multiple `.txt` files, each with one protein sequence per line. They want to build a vocabulary of discriminative subsequences scored by TF-IDF, treating each file as a separate corpus shard, and using corpus-wide TF across all shards. The tokenizer should efficiently compute a large hashmap of observed substrings between `min_k` and `max_k`, then rank and prune to `vocab_size`.

**Why this priority**: This is the core value proposition — without training, nothing else works.

**Independent Test**: Create a folder with several `.txt` files (each with 5–10 protein sequences), instantiate `TfidfTokenizer` with defaults, call `fit(folder_path)`, and verify that the resulting vocabulary contains scored tokens with valid tf, df, idf, complexity, and final score values, aggregated corpus-wide.

**Acceptance Scenarios**:

1. **Given** a folder with multiple `.txt` files (each with 20 protein sequences, some empty lines), **When** `fit(folder_path)` is called with default config, **Then** the tokenizer builds a vocabulary of at most `vocab_size` tokens, all single-character residue tokens are present, and every token has non-negative tf, df, idf, complexity, and final score, computed corpus-wide across all shards.
2. **Given** a folder with `.txt` files, **When** `fit(folder_path)` is called, **Then** empty lines are silently ignored and do not count as documents.
3. **Given** a folder with `.txt` files containing mixed-case sequences, **When** `fit(folder_path)` is called with default `case_sensitive=False`, **Then** all sequences are uppercased before processing and the vocabulary contains only uppercase tokens.

---

### User Story 2 — Tokenize a New Sequence (Priority: P1)

After training, the researcher wants to segment an unseen protein sequence into tokens from the learned vocabulary, using highest-score matching with longest-match tie-breaking.

**Why this priority**: Tokenization is the primary output of the system — without it, a trained vocabulary has no utility.

**Independent Test**: After `fit()`, call `tokenize("ACDEFGHIK")` and verify the returned token list covers the full input with no gaps or overlaps.

**Acceptance Scenarios**:

1. **Given** a trained tokenizer, **When** `tokenize("ACDEFGHIK")` is called, **Then** the method returns an ordered list of tokens that, when concatenated, reconstruct the original (normalized) input.
2. **Given** a trained tokenizer with two vocabulary tokens starting at the same position with identical scores, **When** `tokenize(sequence)` is called, **Then** the longer token is selected.
3. **Given** a trained tokenizer with two vocabulary tokens starting at the same position with identical scores and identical lengths, **When** `tokenize(sequence)` is called, **Then** the token inserted earlier into the vocabulary is selected.
4. **Given** a trained tokenizer and an input containing an invalid character (e.g., "1" or "$") that is not in the vocabulary after normalization, **When** `tokenize(sequence)` is called, **Then** `unk_token` is emitted for that character.

---

### User Story 3 — Save and Load a Trained Tokenizer (Priority: P1)

The researcher wants to persist a trained tokenizer to disk and reload it later — preserving the full vocabulary, configuration, token scores, and corpus statistics so that it can tokenize new sequences identically.

**Why this priority**: Without persistence, every session requires retraining, which is impractical for large corpora.

**Independent Test**: Train a tokenizer, save it, load it in a fresh instance, tokenize the same sequence, and assert identical output.

**Acceptance Scenarios**:

1. **Given** a trained tokenizer, **When** `save(path)` is called, **Then** all config, vocabulary, token metadata (tf, df, idf, complexity, score), and corpus-level statistics (total document count) are written to disk.
2. **Given** a saved tokenizer file, **When** `TfidfTokenizer.load(path)` is called, **Then** a new tokenizer instance is returned whose `tokenize()` output matches the original tokenizer exactly for any input.
3. **Given** a saved tokenizer file, **When** loaded, **Then** the tokenizer preserves cumulative tf, df, total document count, and scoring config — sufficient for continued training.

---

### User Story 4 — Tokenize a Corpus File (Priority: P2)

The researcher wants to tokenize an entire file of sequences in batch, optionally writing the tokenized output to a new file.

**Why this priority**: Batch processing is essential for downstream pipelines, but depends on single-sequence tokenization working first.

**Independent Test**: Call `tokenize_file(input_path)` on a 10-line file and verify 10 tokenized results. Call again with `output_path` and verify the output file is written correctly.

**Acceptance Scenarios**:

1. **Given** a trained tokenizer and a `.txt` file with 10 non-empty lines plus 2 empty lines, **When** `tokenize_file(input_path)` is called, **Then** 10 tokenized results are returned (empty lines skipped).
2. **Given** a trained tokenizer and `tokenize_file(input_path, output_path="out.txt")`, **When** called, **Then** the tokenized output is written to `out.txt` with one space-delimited tokenized sequence per line.

---

### User Story 5 — Continue Training on a Second Corpus (Priority: P2)

After initial training and saving, the researcher obtains a second corpus and wants to update the tokenizer's vocabulary and statistics incrementally — merging new data with existing corpus statistics rather than retraining from scratch.

**Why this priority**: Incremental training avoids expensive recomputation and enables evolving corpora. It depends on save/load working correctly.

**Independent Test**: Train on file A, save, load, call `fit(file_B, mode="continue")`, verify that total document count equals count(A) + count(B), existing tokens have updated statistics, and new high-scoring tokens from file B can enter the vocabulary.

**Acceptance Scenarios**:

1. **Given** a tokenizer trained on corpus A (100 sequences) and saved, **When** loaded and `fit(corpus_B, mode="continue")` is called on 50 new sequences, **Then** the total document count is 150, existing token tf/df values are sums of old and new counts, and idf/scores are recomputed globally.
2. **Given** a continued training run, **When** a new substring appears only in corpus B with a high score, **Then** it can enter the vocabulary if it ranks within the top `vocab_size`.
3. **Given** a continued training run, **When** an old token's score drops below the vocab cutoff due to merged statistics, **Then** it is pruned from the active vocabulary.
4. **Given** identical preprocessing and config, **When** training on A then continuing on B vs. training on concat(A, B) from scratch, **Then** the results are equivalent (documented exception: if lossy pruning prevents exact equivalence, this is documented).

---

### User Story 6 — Configure Scoring and Filtering (Priority: P2)

A researcher wants to experiment with different TF-IDF formulations, scoring modes, and low-complexity filtering thresholds to optimize vocabulary quality for their specific dataset.

**Why this priority**: Configurability is the feature's major differentiator, but the system must work with defaults first.

**Independent Test**: Instantiate tokenizers with different `tf_mode`, `idf_mode`, `scoring_mode`, and `filter_low_complexity` settings, train on the same corpus, and verify that vocabulary contents and scores differ as expected.

**Acceptance Scenarios**:

1. **Given** `tf_mode="raw"` vs `tf_mode="log"`, **When** trained on the same corpus, **Then** token tf values differ according to the formula.
2. **Given** `idf_mode="standard"` vs `idf_mode="smooth"` vs `idf_mode="probabilistic"`, **When** trained, **Then** idf values are computed per the documented formula for each mode.
3. **Given** `scoring_mode="complexity_regularized_tfidf"` (default), **When** a low-complexity token like "AAAA" is scored, **Then** its complexity factor (`len(set(token)) / len(token)`) is 0.25 and its score is penalized relative to a diverse token of the same length.
4. **Given** `filter_low_complexity=True` and `low_complexity_threshold=0.3`, **When** a token with complexity 0.25 is encountered, **Then** it is excluded from vocabulary candidacy.

---

### User Story 7 — Residue Normalization and Rare Residue Handling (Priority: P3)

The researcher works with sequences containing non-standard or rare amino acid residues and wants configurable handling — keeping them, replacing with an unknown token, or mapping to a fallback symbol.

**Why this priority**: Important for data quality, but a secondary concern — the system works with standard residues by default.

**Independent Test**: Configure `RARE_RESIDUE_POLICY="replace_with_unk"`, train on sequences containing rare residues (e.g., "U", "O"), and verify they are replaced with `unk_token`.

**Acceptance Scenarios**:

1. **Given** `RARE_RESIDUE_POLICY="keep"` (default), **When** a sequence contains rare residue "U", **Then** "U" is preserved in both training and tokenization.
2. **Given** `RARE_RESIDUE_POLICY="replace_with_unk"`, **When** a sequence contains "U", **Then** "U" is replaced with the configured `unk_token` before processing.
3. **Given** `RARE_RESIDUE_POLICY="replace_with_nn"`, **When** a sequence contains "U", **Then** "U" is replaced with the configured fallback symbol (e.g., "X").

---

### User Story 8 — Fresh Retraining (Priority: P3)

The researcher wants to discard all prior training data and retrain from scratch on a new corpus, while preserving configuration.

**Why this priority**: Useful for experimentation, but straightforward once core training works.

**Independent Test**: Train on corpus A, then call `fit(corpus_B, mode="fresh")`. Verify that all statistics reflect only corpus B, with no residual data from corpus A.

**Acceptance Scenarios**:

1. **Given** a tokenizer previously trained on corpus A, **When** `fit(corpus_B, mode="fresh")` is called, **Then** all corpus statistics (tf, df, document count) reflect only corpus B.
2. **Given** fresh retraining, **When** completed, **Then** configuration (scoring mode, thresholds, residue policy) is preserved unless explicitly changed.

---

### Edge Cases

- **Empty corpus file**: `fit()` on an empty file (or file with only empty lines) raises a clear error rather than producing an empty vocabulary silently.
- **Corpus folder has no `.txt` files**: `fit()` raises a clear error rather than silently training on an empty shard set.
- **Single-sequence corpus**: Training on a corpus with one sequence produces a valid vocabulary (df=1 for all tokens, idf values computed accordingly).
- **Sequence shorter than `min_k`**: A sequence shorter than `min_k` still produces single-character tokens (which are always in the vocabulary).
- **Entire sequence is unknown characters**: `tokenize()` emits a sequence of `unk_token` values.
- **Missing file path**: `fit()`, `tokenize_file()`, `save()`, and `load()` raise clear errors when given a non-existent file path.
- **Untrained tokenizer**: Calling `tokenize()` before `fit()` raises a clear error indicating the tokenizer has not been trained.
- **`vocab_size` smaller than mandatory tokens**: If `vocab_size` is less than the number of special tokens plus single-character tokens, all mandatory tokens are still included (vocab_size acts as a minimum for scored tokens on top of mandatory ones).
- **Continued training on a tokenizer that was never saved with corpus stats**: Raises a clear error indicating that continued training requires saved corpus statistics.
- **`max_k` exceeds sequence length**: Candidate generation gracefully handles this by capping window size at sequence length.
- **Duplicate sequences in corpus**: Each line is treated as a separate document for df counting, even if content is identical.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The system MUST read training data from a folder containing one or more `.txt` files, treating each file as a separate corpus shard. Each non-empty line in any file is one sequence/document; empty lines are ignored.
- **FR-002**: The system MUST normalize sequences by default: strip leading/trailing whitespace, convert to uppercase, operate case-insensitively. Normalization MUST be configurable via `normalize` and `case_sensitive` parameters.
- **FR-003**: The system MUST support configurable residue normalization with policies: `"keep"` (preserve rare residues as-is), `"replace_with_unk"` (replace with `unk_token`), and `"replace_with_nn"` (replace with a configured fallback symbol such as `"X"`). Default: `"keep"`.
- **FR-004**: The system MUST generate candidate tokens as overlapping variable-length substrings from `min_k` to `max_k` for each sequence.
- **FR-004a**: The system MUST aggregate counts only for candidate tokens actually observed across all corpus shards in a corpus-wide hashmap keyed by token string, sufficient to support ranking and pruning to the configured `vocab_size`.
- **FR-005**: The system MUST always include all single-character residue tokens in the final vocabulary, regardless of scoring or filtering.
- **FR-006**: The system MUST compute for each candidate token: term frequency (tf, as total occurrences corpus-wide across all shards), document frequency (df, as the number of non-empty sequence lines containing the token across all shards), inverse document frequency (idf) using the configured formula, and a final score using the configured scoring formula.
- **FR-007**: The system MUST support configurable TF modes: `"raw"` (raw count) and `"log"` (log(1 + tf)). Default: `"log"`.
- **FR-008**: The system MUST support configurable IDF modes: `"standard"` (log(N / df)), `"smooth"` (log((N + 1)/(df + 1)) + 1), and `"probabilistic"` (log((N - df) / df)). Default: `"smooth"`.
- **FR-009**: The system MUST support configurable scoring modes: `"tfidf"` (tf_value × idf), `"log_tfidf"` (log(1 + tf) × idf), and `"complexity_regularized_tfidf"` (tf_value × idf × complexity × length_bonus). Default: `"complexity_regularized_tfidf"`.
- **FR-010**: The complexity-regularized scoring formula MUST compute: `complexity = len(set(token)) / len(token)` and `length_bonus = 1 + alpha * (len(token) - min_k)`, where `alpha` is a configurable parameter.
- **FR-011**: The system MUST filter vocabulary candidates using configurable `min_tf` and `min_df` thresholds, then rank by final score and keep the top `vocab_size` tokens.
- **FR-012**: The system MUST always inject `SPECIAL_TOKENS`, all single-character residue tokens, and `unk_token` into the vocabulary regardless of score or filtering.
- **FR-013**: The system MUST support configurable low-complexity filtering: when `filter_low_complexity=True`, tokens with complexity below `low_complexity_threshold` are excluded from vocabulary candidacy. When disabled, complexity is still available as a score penalty in applicable scoring modes.
- **FR-014**: The `tokenize(sequence)` method MUST segment input using the learned vocabulary by: finding all matching vocabulary tokens at each position, choosing the highest-score match, breaking ties by longest match, and then choosing the token inserted earlier into the vocabulary for any remaining ties.
- **FR-015**: During tokenization, if no learned token matches at a position, the system MUST fall back to a single-character token. If the character is invalid after normalization, the system MUST emit `unk_token`.
- **FR-016**: The `tokenize_file(input_path, output_path=None)` method MUST read a plain text file, tokenize each non-empty line, return tokenized results as `List[List[str]]`, and optionally write tokenized output to `output_path` as one space-delimited tokenized sequence per line.
- **FR-017**: The `save(path)` method MUST persist: tokenizer config, vocabulary, token metadata (tf, df, idf, complexity, score), and corpus-level statistics (cumulative tf, cumulative df, total document count, scoring config, low-complexity settings, residue normalization settings).
- **FR-018**: The `load(path)` class method MUST restore a fully functional trained tokenizer from a saved file, including all config, vocabulary, scores, and corpus statistics sufficient for continued training.
- **FR-019**: The `fit(file_path, mode="fresh")` method MUST support `mode="fresh"` (discard prior statistics, rebuild from scratch) and `mode="continue"` (merge new corpus data with existing statistics).
- **FR-020**: In `mode="continue"`, the system MUST: retain prior corpus statistics, process the new file as additional corpus data, merge tf and df counts, update total document count, recompute idf and scores globally, rerank vocabulary, allow new tokens to enter, and allow old low-value tokens to be pruned.
- **FR-021**: The system MUST also expose a `continue_fit(file_path)` convenience method equivalent to `fit(file_path, mode="continue")`.
- **FR-022**: The system MUST support configurable `merge_strategy` for continued training: `"accumulate"` (merge prior and new stats — default), `"replace_vocab"` (keep stats but rebuild vocab fully from merged candidates), and `"freeze_vocab"` (update scores for existing vocab only, do not admit new tokens).
- **FR-023**: The system MUST support brute-force search (default) during segmentation: enumerate candidate lengths from `max_k` down to 1 at each position. Optionally support beam search with configurable beam width.
- **FR-024**: The system MUST expose or store for each vocabulary token: token string, token length, tf (corpus-wide), df, idf, complexity, and final score.
- **FR-025**: The system MUST raise clear errors for: missing files, empty corpus, untrained tokenizer usage, invalid configuration values, and insufficient saved state for continued training.
- **FR-026**: The system MUST produce deterministic output for the same input, config, and training order.

### Key Entities

- **Corpus**: A folder of plain text shard files, where each `.txt` file is a corpus shard containing biological sequences, one per line. Characterized by total document count (N) across all shards, where each non-empty line is one document.
- **Corpus Shard**: A single `.txt` file within the training folder. Used as an input partition for ingestion; shard boundaries do not change TF aggregation semantics.
- **Candidate Token**: An overlapping substring of length `min_k` to `max_k` extracted from corpus sequences. Carries raw tf, df, and position metadata.
- **Vocabulary Token**: A candidate token that survived filtering and ranking. Includes: token string, length, tf, df, idf, complexity, final score, and membership flags (special token, single-character, learned).
- **Vocabulary Order**: The deterministic insertion order assigned to vocabulary tokens during vocabulary construction and preserved through save/load so it can be used as the final tokenization tie-break rule.
- **Tokenizer Configuration**: The full set of user-configurable parameters governing normalization, candidate generation, scoring, filtering, search, and continued training behavior.
- **Corpus Statistics**: Aggregated data needed for scoring and continued training: per-token cumulative tf and df, total document count N measured in non-empty sequence lines across all shards, and scoring/filtering configuration at time of training.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: A researcher can train the tokenizer on a corpus of 10,000+ sequences and produce a scored vocabulary within a reasonable time on a standard workstation.
- **SC-002**: The tokenizer segments any valid sequence into an ordered token list that, when concatenated, exactly reconstructs the normalized input — 100% reconstruction fidelity.
- **SC-003**: Save/load round-trip preserves tokenizer behavior: tokenizing the same sequence before save and after load produces identical output.
- **SC-004**: Continued training on a second corpus updates vocabulary and statistics without requiring full retraining; total document count reflects the sum of both corpora.
- **SC-005**: Low-complexity tokens (e.g., "AAAA", "LLLL") receive lower scores or are excluded from the vocabulary when filtering is enabled, compared to diverse tokens of the same length.
- **SC-006**: Switching between supported TF, IDF, and scoring modes produces measurably different vocabulary compositions and token scores on the same corpus.
- **SC-007**: Default configuration (no custom parameters) produces a valid, usable tokenizer without errors.
- **SC-008**: The tokenizer handles edge cases (empty lines, short sequences, unknown characters) gracefully without crashing.

## Assumptions

- The input corpus consists of a folder of `.txt` shard files containing biological sequences (primarily protein-like), but the tokenizer is not restricted to any specific alphabet.
- Default `STANDARD_RESIDUES` corresponds to the 20 standard amino acids: A, C, D, E, F, G, H, I, K, L, M, N, P, Q, R, S, T, V, W, Y.
- Default `RARE_RESIDUES` includes non-standard residues commonly encountered in protein datasets: B, J, O, U, Z, X.
- Default `SPECIAL_TOKENS` includes at minimum: `[PAD]`, `[UNK]`, `[CLS]`, `[SEP]`, `[MASK]`.
- Default `unk_token` is `[UNK]`.
- Default `min_k` is 2 and default `max_k` is 6.
- Default `vocab_size` is 8000.
- Default `min_tf` is 1 and default `min_df` is 1.
- Default `low_complexity_threshold` is 0.3.
- The `alpha` parameter in the length bonus formula defaults to 0.1.
- JSON is the recommended storage format for save/load, with `snake_case` keys per constitution naming conventions.
- Beam search parameters (beam width, etc.) are optional and only relevant when `search_method="beam"`.
- Performance optimization (e.g., caching, indexing) is outside the initial scope — correctness and clarity take precedence.
