# Feature Specification: Protein Sequence EDA and Tokenization Strategy Evaluation for BERT Pretraining

**Feature Branch**: `001-protein-eda-tokenization`  
**Created**: 2026-03-08  
**Status**: Draft  
**Input**: User description: "Build an exploratory notebook that profiles all available protein FASTA files, compares single-token, 3-mer, 5-mer, and BPE tokenization strategies, preserves metadata for future downstream curation, and ends with an evidence-based recommendation for pretraining setup."

## Compliance Notes _(mandatory)_

- **Relevant Constitution Principles**: I. Semantic Integrity and Source-of-Truth Behavior; II. Minimal Diffs; IV. Prefer Existing Patterns Over New Architecture; V. Security, Dependency Hygiene, Mandatory Preflight, and Naming Discipline.
- **Notebook Workflow Constraints**: This feature is explicitly notebook-scoped. The notebook must be runnable top-to-bottom, place imports in the first cell, define configuration constants in the second cell, keep work split into small logical cells, perform fail-fast validation for invalid configuration, and preserve exploratory readability without hiding core logic inside large wrappers.
- **UI Behavior Standards Applied**: N/A. No `.specify/memory/UI_BEHAVIOR_STANDARDS.md` file is present.
- **Cross-Feature Learnings Applied**: No `.specify/memory/LEARNINGS.md` file is present. Existing repository governance is applied directly from the constitution and the established notebook-oriented workflow in the repository.
- **Conflicts & Resolution**: Exploratory notebooks often tolerate silent fallback and ad hoc cell ordering, but this feature must remain rerunnable and auditable. The compliant resolution is to require explicit configuration validation, deterministic cell ordering, and clear saved artifacts while still allowing exploratory analysis and narrative discussion.

## Clarifications

### Session 2026-03-08

- Q: How should the notebook handle malformed FASTA records or files encountered during corpus parsing? → A: Skip malformed records or files, record them in a parse-error summary, and continue analysis on valid records.
- Q: How should BPE be evaluated in phase 1? → A: Combine a small fixed BPE vocabulary-size grid with corpus-informed candidate sizes, and compare the resulting tokenization behavior using downstream-readiness evidence rather than actual downstream training.
- Q: How should exact-sequence duplicates be handled for outputs intended to inform pretraining? → A: Preserve the full raw record-level table for provenance and analysis, and also produce a deduplicated candidate view or artifact for pretraining planning.
- Q: How should ambiguous residues be handled during phase-1 analysis? → A: Use one primary handling policy for the main analysis and also run a smaller sensitivity comparison across the other allowed policies.
- Q: How should expensive tokenization-comparison work be scoped at runtime? → A: The notebook user chooses the analysis scope manually on each run, and the spec does not impose a default full-corpus or subset policy.
- Q: What saved artifact format convention should the notebook use by default? → A: Save a lightweight CSV preview for human inspection and a full Parquet artifact for large tables.
- Q: How should FASTA header metadata be parsed and preserved? → A: Treat headers as following a standard structure; extract the standard fields and save them, preserve the full raw header so no data is lost, and report any non-standard header as malformed.
- Q: Should the notebook lock a canonical structured header schema now? → A: No. Parse the standard header structure into dynamic structured fields per record, preserve the full raw header, and report any non-standard header as malformed.
- Q: How should `SAMPLE_MODE` behave by default? → A: Keep a declared baseline default of `SAMPLE_MODE="all"` in the config block, while allowing explicit override for expensive tokenization analyses.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Profile the Protein Corpus (Priority: P1)

As a researcher preparing a protein language model corpus, I want one notebook to parse every currently available protein FASTA file and summarize sequence quality, lengths, and residue composition so I can judge whether the corpus is usable for BERT-style pretraining.

**Why this priority**: The project cannot make a defensible tokenization or preprocessing choice until the raw corpus has been measured directly.

**Independent Test**: Run the notebook against the configured data root and verify it parses all discoverable `.faa` files, produces dataset-level counts and length statistics, reports residue and ambiguity summaries without requiring manual code edits, and emits a parse-error summary when malformed records or files are skipped.

**Acceptance Scenarios**:

1. **Given** a valid root directory containing protein FASTA files in nested assembly folders, **When** the notebook runs, **Then** it discovers every current `.faa` file, parses every valid record, and shows the total number of files, assemblies, and protein sequences.
2. **Given** parsed protein records, **When** the exploratory analysis cells run, **Then** the notebook displays raw sequence length distributions, counts above key thresholds (128, 256, 512, 1024), amino acid frequencies, and ambiguous residue frequencies.

---

### User Story 2 - Compare Tokenization Strategies for Pretraining Readiness (Priority: P2)

As a researcher deciding how to pretrain a BERT-style protein model, I want the notebook to compare single-token, overlapping 3-mer, overlapping 5-mer, and BPE strategies on the actual corpus so I can choose a strategy that fits sequence length, vocabulary growth, sparsity, and hardware constraints.

**Why this priority**: The main scientific decision in this phase is selecting a pretraining representation that is defensible for the current dataset rather than chosen by preference.

**Independent Test**: Run the tokenization comparison section and verify that each required strategy is evaluated with comparable summary tables and plots, including vocabulary size, token-frequency behavior, tokenized-length distributions, and the fraction of sequences that exceed a length budget of 512 tokens.

**Acceptance Scenarios**:

1. **Given** parsed protein sequences and a configured maximum length of 512, **When** the tokenization comparison runs, **Then** the notebook computes tokenized lengths for all four strategies and reports the proportion of sequences requiring sliding windows under each strategy.
2. **Given** the comparison results, **When** the notebook reaches its conclusion section, **Then** it presents an evidence-based recommendation for tokenization and preprocessing choices, including caveats for single-token, 3-mer, 5-mer, and BPE options and an explicit discussion of which strategy appears most promising for later downstream fine-tuning based on phase-1 proxy evidence.

---

### User Story 3 - Preserve Metadata for Future Functional Curation (Priority: P3)

As a researcher planning later functionality-oriented fine-tuning, I want FASTA header information preserved and lightly profiled so I can assess whether current metadata may support future curation without falsely claiming biological labels.

**Why this priority**: The downstream direction depends on preserving provenance and curation hooks now, even though functionality classification is out of scope for this notebook.

**Independent Test**: Run the metadata-focused section and verify the notebook retains full header text, extracts structured header fields dynamically into saved outputs, reports any non-standard header as malformed, and exports a metadata preview artifact without generating unsupported functionality labels.

**Acceptance Scenarios**:

1. **Given** FASTA records with assembly context and header text, **When** the metadata preservation section runs, **Then** the notebook keeps the full header and record provenance alongside each sequence summary.
2. **Given** the preserved headers, **When** exploratory metadata curation runs, **Then** the notebook extracts structured header fields losslessly from the standard header format, reports malformed header structures, and highlights possible future curation hints while explicitly avoiding claims that headers alone provide validated functionality labels.

### Edge Cases

- A configured data root contains no `.faa` files.
- One or more FASTA files are present but contain malformed records or empty sequences; valid records must still be analyzed while malformed inputs are counted and reported.
- A sequence contains only ambiguous or rare residues and becomes unusable under a selected residue-handling policy.
- The same exact protein sequence appears multiple times within one assembly and across different assemblies.
- Very long proteins cause most tokenization strategies to exceed the configured maximum length and require sliding-window discussion.
- A configured tokenization strategy or residue-handling policy is invalid.
- A header deviates from the expected standard structure; the raw header must still be preserved and the record must be reported as malformed for header-format review.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The notebook MUST target phase-1 evidence gathering only and MUST NOT include model training, downstream contact prediction, secondary structure prediction, functionality classification, structural supervision, or final antimicrobial-resistance labeling.
- **FR-002**: The notebook MUST expose a clear top-level configuration section containing `DATA_ROOT`, `MAX_LENGTH`, `TOKENIZATION_STRATEGIES`, `AMBIGUOUS_RESIDUE_MODE`, `RARE_RESIDUE_POLICY`, and `SAMPLE_MODE`, and the documented baseline configuration MUST include `SAMPLE_MODE="all"`.
- **FR-002a**: The notebook MUST expose the runtime analysis scope clearly enough that a user can choose manually on each run whether expensive tokenization-comparison work executes on the full corpus, a subset, or another explicitly configured scope. The notebook MUST NOT assume one default scope for those expensive comparisons.
- **FR-002b**: The baseline default `SAMPLE_MODE="all"` MUST apply to corpus-level parsing and analysis unless the user explicitly overrides the scope for expensive tokenization-comparison work.
- **FR-002c**: All runtime controls, switches, optional overrides, and artifact/figure output settings used by the notebook MUST be declared in the config block rather than hidden in downstream cells.
- **FR-003**: The notebook MUST fail early with a clear error message when a configured tokenization strategy, residue-handling mode, rare-residue policy, or data root is invalid. It MUST NOT silently fall back to a default behavior.
- **FR-004**: The notebook MUST discover and parse all current `.faa` files under the configured root directory.
- **FR-004a**: When FASTA parsing encounters malformed records or unreadable `.faa` files, the notebook MUST skip those invalid inputs, continue analysis on valid records, and report a parse-error summary with counts and source locations.
- **FR-005**: For every parsed FASTA record, the notebook MUST preserve at least the parent assembly identifier or folder name, source file path, sequence identifier, full FASTA header, raw amino acid sequence, and raw sequence length.
- **FR-006**: The notebook MUST allow ambiguous residues to remain part of the dataset and MUST support configurable handling modes that cover: keep as-is, replace with an unknown token, normalize selected residues, and drop the affected sequence.
- **FR-006a**: The notebook MUST designate one primary ambiguous-residue handling policy for the main analysis outputs and MUST also run a smaller sensitivity comparison across the other supported handling policies so the stability of the recommendation can be assessed.
- **FR-006b**: The sensitivity comparison for alternative residue-handling policies MUST produce explicit comparative tables and, where meaningful, comparison plots that show how policy changes affect affected-sequence counts, tokenized-length behavior, vocabulary behavior, and recommendation implications.
- **FR-007**: The notebook MUST explicitly record the active ambiguous-residue and rare-residue handling choices in displayed outputs and saved artifacts used for downstream reference.
- **FR-008**: The notebook MUST avoid padding raw sequences during exploratory analysis except where tokenization simulation or model-shape demonstration specifically requires it.
- **FR-009**: The notebook MUST compute and display the total number of protein sequences in the current corpus.
- **FR-010**: The notebook MUST analyze raw protein sequence lengths and report counts and fractions exceeding 128, 256, 512, and 1024 residues.
- **FR-011**: The notebook MUST compute and display the fraction of protein sequences that would require sliding windows under a maximum token length of 512 for each supported tokenization strategy.
- **FR-012**: The notebook MUST compute and visualize amino acid frequencies for the current corpus.
- **FR-013**: The notebook MUST measure ambiguous residue occurrence at both the residue level and the affected-sequence level.
- **FR-014**: The notebook MUST perform exact-sequence duplicate analysis and distinguish duplicate rates within assemblies from duplicate rates across assemblies.
- **FR-014a**: The notebook MUST preserve raw record-level duplicate information for provenance while also producing a deduplicated candidate dataset or exported artifact intended specifically for pretraining planning.
- **FR-015**: The notebook MUST support comparison of the following tokenization strategies on the observed corpus: single amino acid, overlapping 3-mer, overlapping 5-mer, and BPE.
- **FR-016**: For the 3-mer and 5-mer strategies, the notebook MUST treat tokens as overlapping k-mers and MUST evaluate them without padding-based reinterpretation of the raw sequence.
- **FR-017**: The notebook MUST include a short explanatory section describing what BPE is and how it differs from fixed k-mer tokenization.
- **FR-018**: The notebook MUST compare all supported tokenization strategies empirically using corpus-derived results rather than conceptual discussion alone.
- **FR-018a**: BPE evaluation MUST include both a small fixed comparison grid of vocabulary sizes and one or more corpus-informed candidate sizes derived from observed corpus statistics so the notebook can compare static and adaptive BPE choices in the same phase-1 analysis.
- **FR-019**: For each tokenization strategy, the notebook MUST compute at least: vocabulary size, token frequency distribution, tokenized sequence length distribution, fraction of sequences exceeding 512 tokens, approximate sparsity or coverage characteristics, and notes on interpretability and biological plausibility.
- **FR-019a**: The tokenization comparison MUST include a downstream-readiness proxy assessment for each strategy that discusses likely suitability for later fine-tuning based on evidence available in phase 1, such as metadata preservation, interpretability, vocabulary efficiency, sequence-length behavior, and sparsity, without running downstream prediction tasks.
- **FR-020**: The notebook MUST explicitly investigate whether 3-mer and 5-mer vocabularies appear too sparse for the current corpus size and MUST discuss the practical implications for pretraining.
- **FR-021**: The notebook MUST produce, at minimum, the following plots: histogram of raw sequence lengths, boxplot or violin plot of raw sequence lengths, cumulative distribution of raw sequence lengths, bar chart of amino acid frequencies, bar chart of ambiguous residue frequencies, histogram of tokenized lengths for each strategy, comparison plot of the fraction exceeding the max length under each strategy, vocabulary-size comparison across strategies, and a duplicate-rate summary visualization.
- **FR-021a**: The notebook SHOULD add evidence-oriented comparison plots for next-step decision making when they materially improve interpretability, including plots comparing alternative residue-handling policies and plots highlighting strategy-specific tradeoffs for suggested pretraining follow-up.
- **FR-022**: The notebook MUST preserve full FASTA header text and include an exploratory metadata section that extracts simple parseable fields when possible and assesses whether headers may contain future curation hints.
- **FR-022a**: The notebook MUST treat the FASTA headers as following a standard parseable structure, extract structured header fields into saved outputs without locking a canonical schema yet, preserve the original raw header text without loss, and report any header that does not match the standard structure as malformed.
- **FR-023**: The notebook MUST not claim that FASTA headers provide validated functionality labels unless those labels are directly derivable from the source data.
- **FR-024**: The notebook MUST display summary tables, plots, surfaced open questions, and recommendation notes during notebook execution.
- **FR-024a**: When a user-selected runtime scope limits expensive tokenization-comparison work to less than the full corpus, the notebook MUST make that scope visible in displayed outputs and saved artifacts so conclusions remain auditable.
- **FR-025**: The notebook MUST save analysis artifacts that include, at minimum, a sequence-level statistics table, a tokenization comparison table, a duplicate summary table, and a header metadata preview table. It MAY also save a cleaned or curated master table for future downstream work.
- **FR-025a**: Saved outputs MUST make the distinction between raw record-level data and deduplicated candidate data explicit so later pretraining work can choose between provenance-preserving analysis outputs and deduplicated planning outputs without ambiguity.
- **FR-025b**: For large tabular outputs, the notebook MUST save both a lightweight CSV preview for manual inspection and a full Parquet artifact for downstream processing unless a table is small enough that one human-readable CSV is sufficient.
- **FR-026**: The notebook MUST end with a written conclusion section that states the recommended tokenization strategy for the current corpus, the recommended residue-handling policy, the duplicate-handling recommendation, a sufficiency assessment for single-token baseline, 3-mer baseline, 5-mer exploration, and BPE exploration, the justification for the recommended pretraining setup, and the key caveats and open risks.
- **FR-027**: The conclusion section MUST base its recommendations on observed evidence from the notebook outputs and MUST NOT hard-code a preferred strategy before analysis.
- **FR-028**: The notebook MUST preserve enough provenance and metadata linkage that future downstream fine-tuning work can connect derived training examples back to their source assemblies, file paths, and FASTA headers.

### Key Entities _(include if feature involves data)_

- **Protein Sequence Record**: One parsed FASTA entry with its assembly context, file provenance, full header, raw sequence text, and sequence length.
- **Residue Handling Policy**: The configured rule describing how ambiguous and rare residues are preserved, normalized, replaced, or dropped during exploratory analysis, including which policy is primary and which are used only for sensitivity comparisons.
- **Tokenization Strategy Summary**: A comparable summary of one tokenization option containing vocabulary size, token-frequency behavior, tokenized-length behavior, exceedance rates, sparsity observations, and interpretability notes.
- **Duplicate Summary Record**: An analysis result describing exact-sequence duplication overall, within an assembly, or across assemblies, together with whether a row belongs to the raw provenance view or the deduplicated candidate view.
- **Header Metadata Preview Record**: A lightweight exploratory record that preserves the full FASTA header text, stores the extracted structured header fields for each record, and flags whether the header matched the expected standard structure.
- **Saved Analysis Artifact**: A persisted notebook output that records both its semantic role and storage format, including when a CSV preview and Parquet full export represent the same underlying table.
- **Recommendation Summary**: The notebook’s evidence-based conclusion tying observed corpus statistics to a proposed pretraining setup and explicit risks.

### Assumptions and Dependencies

- The current corpus is defined by the set of `.faa` files available under the configured root at execution time.
- FASTA files are expected to use a standard header structure suitable for deterministic field extraction; any deviation is treated as malformed data and reported rather than silently tolerated.
- BPE comparison in this phase is exploratory and is intended to judge corpus fit, not to finalize a production tokenizer implementation.
- Downstream usefulness in this phase is evaluated through corpus-derived proxy evidence only and does not include actual downstream supervised training or benchmarking.
- Saved artifacts are intended to support future pretraining and curation decisions, not to serve as final biological labels.
- Expensive tokenization-comparison stages may run on different user-selected scopes across notebook executions, so outputs must record the chosen scope for each run.
- The declared baseline notebook configuration uses `SAMPLE_MODE="all"`, but expensive tokenization-comparison stages may be explicitly overridden to another scope and must record that chosen scope for each run.
- Large sequence-level outputs are expected to be more practical in Parquet than CSV, but the notebook should still emit a lightweight CSV preview where human inspection is useful.

### Scope Boundaries

- In scope: corpus profiling, residue distribution analysis, ambiguity analysis, exact duplicate analysis, tokenization comparison across the four required strategies, sequence-length compatibility analysis under a maximum length of 512, sliding-window implications, metadata preservation, exploratory header curation hints, and evidence-based recommendations for pretraining preparation.
- Out of scope: actual BERT training, external supervision, downstream structural tasks, antimicrobial-resistance label generation, and final functionality classification workflows.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: A full notebook run accounts for 100% of discoverable current `.faa` files under the configured root and reports the resulting total file, assembly, and sequence counts.
- **SC-002**: The notebook produces comparable summary outputs for all four required tokenization strategies, including vocabulary size and fraction of sequences exceeding a token length of 512 for each strategy.
- **SC-003**: The notebook generates all required visual outputs in a single run, including raw-length, residue-frequency, tokenized-length, vocabulary-size, and duplicate-rate views.
- **SC-004**: 100% of parsed protein records retained in the analysis preserve source provenance fields and full FASTA header text in the main exploratory dataset or exported preview artifacts.
- **SC-004a**: The notebook reports how tokenization conclusions change, if at all, under the primary ambiguous-residue policy versus the sensitivity-comparison policies.
- **SC-004b**: The notebook emits at least one comparative table or plot showing the effect of alternative residue-handling policies on the recommendation path for subsequent pretraining work.
- **SC-005**: The final recommendation section names one recommended default tokenization strategy and one recommended residue-handling policy for the current corpus, and each recommendation is justified by at least three observed findings from the notebook analysis.
- **SC-006**: The notebook exports at least four reusable analysis artifacts covering sequence statistics, tokenization comparison, duplicate summary, and metadata preview for downstream work.
- **SC-007**: The notebook exports both a provenance-preserving raw sequence view and a deduplicated candidate view suitable for pretraining planning, and the relationship between the two views is clearly documented in displayed outputs or saved artifacts.
- **SC-008**: Every saved tokenization-comparison artifact records the user-selected runtime scope used for that analysis so later reviewers can distinguish full-corpus conclusions from limited-scope runs.
- **SC-009**: Every large saved table intended for downstream reuse is available in Parquet format, and every such table that benefits from quick human inspection also has a corresponding lightweight CSV preview.
- **SC-010**: Metadata outputs preserve 100% of raw FASTA header text while also extracting structured header fields for all well-formed records and reporting any malformed header records.
- **SC-011**: The notebook clearly reports when a run uses the baseline `SAMPLE_MODE="all"` configuration versus an explicit override for expensive tokenization comparisons.
