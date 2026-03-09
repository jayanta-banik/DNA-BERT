# Data Model: Protein Sequence EDA and Tokenization Strategy Evaluation for BERT Pretraining

## Entity: NotebookRunConfig

- Description: Runtime configuration captured from the notebook config cell for one execution.
- Fields:
  - `data_root` (string, required)
  - `max_length` (integer, required, default baseline `512`)
  - `tokenization_strategies` (array of strings, required)
  - `ambiguous_residue_mode` (string, required)
  - `rare_residue_policy` (string, required)
  - `sample_mode` (string, required, baseline default `all`)
  - `analysis_scope_override` (string, optional)
  - `bpe_candidate_modes` (array of strings, optional)
  - `residue_policy_sensitivity_modes` (array of strings, optional)
  - `artifact_output_dir` (string, optional)
  - `figure_output_dir` (string, optional)
  - `save_artifacts` (boolean, optional)
  - `save_figures` (boolean, optional)
- Validation Rules:
  - Reject invalid strategy names or unsupported residue-policy values.
  - Record whether the run used baseline defaults or an explicit scope override.

## Entity: ProteinSequenceRecord

- Description: One parsed FASTA protein record preserved for corpus-level analysis.
- Fields:
  - `assembly_id` (string, required)
  - `file_path` (string, required)
  - `sequence_id` (string, required)
  - `raw_header` (string, required)
  - `header_fields` (object, optional, dynamically extracted)
  - `sequence` (string, required)
  - `sequence_length` (integer, required, `>= 0`)
  - `contains_ambiguous_residue` (boolean, required)
  - `header_is_malformed` (boolean, required)
  - `parse_status` (enum: `parsed`, `malformed_record`, `malformed_header`)
- Validation Rules:
  - Preserve raw header text without loss for every retained record.
  - Mark malformed header structure explicitly even when the record body is still usable.

## Entity: ParseIssueRecord

- Description: One parsing or validation issue detected during FASTA ingestion.
- Fields:
  - `file_path` (string, required)
  - `assembly_id` (string, optional)
  - `issue_type` (enum: `malformed_record`, `malformed_header`, `empty_sequence`, `read_error`)
  - `issue_message` (string, required)
  - `record_identifier` (string, optional)
- Validation Rules:
  - Parse issues are reported and counted even when valid records from the same file continue through analysis.

## Entity: ResiduePolicyComparison

- Description: Summary of one ambiguous/rare residue handling mode evaluated during phase 1.
- Fields:
  - `policy_name` (string, required)
  - `is_primary_policy` (boolean, required)
  - `affected_sequence_count` (integer, required)
  - `tokenization_impacts` (object, required)
  - `recommendation_effect` (string, required)
  - `evidence_plot_paths` (array of strings, optional)
- Validation Rules:
  - Exactly one policy is marked as primary in a notebook run.

## Entity: DuplicateSummaryRecord

- Description: Duplicate analysis result for raw provenance data or deduplicated planning data.
- Fields:
  - `view_name` (enum: `raw_provenance`, `deduplicated_candidate`)
  - `duplicate_scope` (enum: `overall`, `within_assembly`, `across_assemblies`)
  - `duplicate_group_count` (integer, required)
  - `duplicate_sequence_count` (integer, required)
  - `duplicate_rate` (number, required)
- Validation Rules:
  - Raw and deduplicated views must remain distinguishable in saved outputs.

## Entity: TokenizationStrategySummary

- Description: Comparable summary of one tokenization strategy run.
- Fields:
  - `strategy_name` (enum: `single`, `3-mer`, `5-mer`, `bpe`)
  - `variant_label` (string, required)
  - `analysis_scope` (string, required)
  - `vocabulary_size` (integer, required)
  - `token_frequency_distribution` (object or reference, required)
  - `median_tokenized_length` (number, required)
  - `fraction_exceeding_max_length` (number, required)
  - `coverage_or_sparsity_notes` (string, required)
  - `interpretability_notes` (string, required)
  - `downstream_readiness_notes` (string, required)
- Validation Rules:
  - BPE entries must distinguish fixed-grid variants from corpus-informed variants.

## Entity: SavedAnalysisArtifact

- Description: One persisted output table, figure set, or manifest produced by the notebook.
- Fields:
  - `artifact_name` (string, required)
  - `artifact_role` (enum: `table`, `figure`, `manifest`)
  - `storage_format` (enum: `csv`, `parquet`, `json`)
  - `path` (string, required)
  - `analysis_scope` (string, required)
  - `source_view` (string, optional)
  - `is_preview` (boolean, required)
- Validation Rules:
  - Large reusable tables must have a Parquet artifact.
  - Tables benefiting from human inspection must also expose a CSV preview.
