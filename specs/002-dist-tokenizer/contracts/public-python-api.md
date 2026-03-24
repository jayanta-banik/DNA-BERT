# Contract: Public Python API for `TfidfTokenizer`

## Class

```python
class TfidfTokenizer(ProteinTokenizer):
    def fit(self, file_path, mode="fresh"):
        ...

    def continue_fit(self, file_path):
        ...

    def tokenize(self, sequence):
        ...

    def tokenize_file(self, input_path, output_path=None):
        ...

    def save(self, path):
        ...

    @classmethod
    def load(cls, path):
        ...
```

## Constructor Contract

- Accepts configuration for normalization, scoring, filtering, vocabulary sizing, and continued-training behavior.
- Must default to:
  - `case_sensitive=False`
  - `normalize=True`
  - `tf_mode="log"`
  - `idf_mode="smooth"`
  - `scoring_mode="complexity_regularized_tfidf"`
  - `filter_low_complexity=True`
  - `rare_residue_policy="keep"`
  - `search_method="brute"`
  - `merge_strategy="accumulate"`

## `fit(file_path, mode="fresh")`

- Input:
  - `file_path`: path to a folder containing one or more `.txt` shard files
  - `mode`: `"fresh"` or `"continue"`
- Behavior:
  - `fresh`: reset corpus statistics and rebuild vocabulary from only the provided shard folder
  - `continue`: merge counts from the provided shard folder into the previously loaded or trained state
- Output:
  - Returns the tokenizer instance (`self`)
- Errors:
  - Raises a clear error if the folder does not exist, has no `.txt` files, contains no non-empty sequence lines, or if `mode="continue"` is requested without cumulative prior state

## `continue_fit(file_path)`

- Equivalent to `fit(file_path, mode="continue")`
- Returns the tokenizer instance (`self`)

## `tokenize(sequence)`

- Input:
  - `sequence`: raw sequence string
- Output:
  - Ordered `List[str]` of tokens
- Behavior:
  - Normalize input according to configuration
  - At each offset choose the highest-score vocabulary match
  - Break ties by longest match, then by earlier vocabulary insertion order
  - Fall back to valid single-character tokens, else emit `unk_token`
- Errors:
  - Raises a clear error if called before training or loading a trained tokenizer

## `tokenize_file(input_path, output_path=None)`

- Input:
  - `input_path`: path to a plain text file containing one sequence per line
  - `output_path`: optional destination file
- Output:
  - `List[List[str]]`
- Behavior:
  - Skip empty lines
  - Tokenize each non-empty line independently
  - If `output_path` is provided, write one space-delimited tokenized sequence per line

## `save(path)`

- Input:
  - `path`: output directory or JSON target path
- Behavior:
  - Persist config, total document count, cumulative candidate statistics, vocabulary entries, and vocabulary order
- Output:
  - Returns the written artifact path

## `load(path)`

- Input:
  - `path`: saved tokenizer directory or tokenizer-state JSON file
- Output:
  - New `TfidfTokenizer` instance restored from persisted state
- Behavior:
  - Must preserve tokenization behavior, vocabulary order, and continued-training capability
