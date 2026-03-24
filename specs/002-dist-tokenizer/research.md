# Phase 0 Research: Discriminative Subsequence Tokenizer (DiST)

## Decision 1: Integrate as a custom `ProteinTokenizer` subclass

- Decision: Implement `TfidfTokenizer` as a new subclass under `scripts/python/tokenizer_module/`, reuse `SequenceNormalizer`, and register the class in `tokenizer_module.__init__`. Override encode/save/load behavior rather than forcing the implementation through the Hugging Face `tokenizers.Tokenizer` API.
- Rationale: The repository already centers tokenizer implementations in `tokenizer_module`, and `ProteinTokenizer` provides the normalization and factory conventions worth preserving. A TF-IDF tokenizer needs custom corpus statistics and persistence that do not map cleanly onto the existing `tokenizers` model object.
- Alternatives considered:
  - Build a standalone module outside `tokenizer_module`: rejected because it would bypass the repo’s existing tokenizer registry and patterns.
  - Force the implementation into the `tokenizers` library object model: rejected because custom continued-training state and score-driven greedy segmentation would still require parallel custom state.

## Decision 2: Count only observed substrings while streaming shard files

- Decision: Read a folder of `.txt` shard files, normalize each non-empty line as one document, and update a corpus-wide hashmap only for substrings actually observed between `min_k` and `max_k`. Compute TF as total occurrences across all shards and DF as the number of non-empty sequence lines containing the token.
- Rationale: This matches the clarified spec, bounds work to the actual corpus, and avoids the combinatorial explosion of enumerating theoretical residue combinations that never appear.
- Alternatives considered:
  - Enumerate every possible character combination up to `max_k`: rejected because it is unnecessary and does not scale.
  - Build a per-document TF matrix first: rejected because the feature needs global vocabulary ranking rather than retrieval-style document scoring.

## Decision 3: Persist full cumulative candidate statistics in a JSON tokenizer state file

- Decision: Save one JSON tokenizer-state artifact that includes configuration, total document count, vocabulary order, active vocabulary entries, and cumulative candidate statistics for all observed tokens needed to support `mode="continue"` without losing prior counts.
- Rationale: The spec explicitly requires continued training and recommends JSON persistence. Exact or near-exact equivalence between uninterrupted and resumed training depends on retaining more than just the active vocabulary.
- Alternatives considered:
  - Save only the active top-`vocab_size` vocabulary: rejected because continued training would be lossy and could not admit previously pruned tokens correctly.
  - Split counts across multiple binary artifacts: rejected because it adds complexity and weakens inspectability without a demonstrated need.

## Decision 4: Default to brute-force greedy segmentation with lightweight vocabulary indexing

- Decision: Implement brute-force greedy tokenization as the default search mode, backed by a lightweight in-memory index of vocabulary tokens grouped by starting character and ordered deterministically. Preserve `search_method` as a configuration field and extension point, but do not require a first-pass beam-search implementation to complete the core feature.
- Rationale: Brute-force greedy search fully satisfies the required default behavior and acceptance criteria, while a small vocabulary index avoids scanning the entire vocabulary at every position.
- Alternatives considered:
  - Full beam-search implementation in the first slice: rejected because it adds complexity without being required for MVP acceptance.
  - Pure linear scan over all tokens at every offset: rejected because a trivial index is low-cost and reduces unnecessary work.

## Decision 5: Keep dependencies minimal and validate with fixture-based manual checks

- Decision: Use Python standard library modules for counting, math, persistence, and configuration validation, and validate behavior with fixture shard folders plus round-trip save/load and continue-training checks rather than introducing a new automated test framework.
- Rationale: The repository currently has no automated Python test harness, and the constitution requires dependency hygiene. This feature can be validated with deterministic fixtures and explicit acceptance checks without unrelated tooling churn.
- Alternatives considered:
  - Add `pytest` and a new Python test tree: rejected because it is useful but out of scope for this focused feature slice.
  - Use `scikit-learn` TF-IDF helpers: rejected because the feature needs custom substring generation, token metadata, and continued-training persistence beyond the typical vectorizer contract.
