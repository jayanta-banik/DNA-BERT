<!--
Sync Impact Report
- Version change: 1.3.0 -> 1.4.0
- Modified principles:
	- V. Security, Dependency Hygiene, and Mandatory Preflight ->
	  V. Security, Dependency Hygiene, Mandatory Preflight, and Naming Discipline
- Added sections:
	- Operational Constraints: Naming, JSON Key, Import, and Function Signature Rules
- Removed sections:
	- None
- Templates requiring updates:
	- .specify/templates/plan-template.md: ✅ updated
	- .specify/templates/spec-template.md: ✅ updated
	- .specify/templates/tasks-template.md: ✅ updated
	- .specify/templates/commands/*.md: ⚠ pending (directory not present)
- Runtime guidance checked:
	- README.md: no governance references to update
- Deferred TODOs:
	- TODO(RATIFICATION_DATE): Set when approved by human maintainer
-->

# DNA-BERT Constitution

## Core Principles

### I. Semantic Integrity and Source-of-Truth Behavior

- Agents MUST preserve semantic behavior unless the approved spec explicitly changes it.
- Agents MUST NOT guess genomic domain logic. When behavior is unclear, agents MUST
  either locate source-of-truth behavior in the repository or stop and ask a human for
  clarification before changing code.

Rationale: In genomic data processing, almost-correct behavior is unsafe and can create
invalid downstream analyses.

### II. Minimal Diffs (No Drive-by Refactors)

Agents MUST keep changes small, reviewable, and directly tied to the requested scope.
Agents MUST avoid unrelated renames, formatting sweeps, or architectural reshuffles.
Agents MUST reuse existing utilities, error handling, and project patterns where possible.
Agents SHOULD fix only the root cause within the touched area. Agents MAY propose
follow-up work as TODOs, but MUST NOT bundle unrelated work in the same change set.

Rationale: Small diffs reduce risk and make scientific workflow validation easier.

### III. Incremental Migrations (Feature-by-Feature)

Large changes MUST be executed incrementally, module-by-module and feature-slice by
feature-slice. Agents MUST begin with an inventory of modules, call paths, and contracts.
Agents MUST keep API and data semantics stable during each slice and keep the repository
runnable at every step. Agents SHOULD leave explicit migration checkpoints for review and
rollback.

Rationale: Incremental delivery reduces blast radius in mixed Node.js and Python stacks.

### IV. Prefer Existing Patterns Over New Architecture

Agents MUST follow established patterns in each subproject unless an approved spec
explicitly requires a new approach. This includes script structure, data access patterns,
error-handling style, and module boundaries in Node.js crawlers, Python analysis code,
and model training/inference components.
Agents SHOULD avoid introducing new frameworks or architectural layers. Agents MAY refactor
toward consistency only inside the feature boundary and only when it reduces risk.

Rationale: Consistency is a safety mechanism in multi-language repositories.

### V. Security, Dependency Hygiene, Mandatory Preflight, and Naming Discipline

Secrets MUST be provided via environment variables or secret managers and MUST NEVER be
committed. Any discovered secret in the repository MUST be treated as compromised and MUST
be removed/redacted in the same change or escalated immediately.
Agents MUST avoid adding dependencies unless required by spec. If dependencies are added,
agents MUST justify necessity and prefer actively maintained packages.
Before modifying code, agents MUST complete preflight: identify target project, read this
constitution and local rules, read `.specify/memory/LEARNINGS.md` if present, locate
entrypoints via repo search, and copy the closest existing pattern.
Before generating any spec, plan, tasks, or implementation, agents MUST read and apply all
files in `.specify/memory/`, including `UI_BEHAVIOR_STANDARDS.md` and `LEARNINGS.md` when
present.

Rationale: Security and disciplined preflight prevent avoidable production and compliance
failures.

## Operational Constraints

Agents are allowed to implement scoped feature changes, add or adjust tests and docs needed
to ship safely, and fix bugs in the touched area when they are the direct root cause.

Agents are NOT allowed to perform broad refactors or cross-cutting rewrites without a
migration spec. Agents are NOT allowed to implement feature or refactor work without a
written spec (spec file, issue, or approved design note) unless explicitly instructed by a
human to perform exploratory work.

Repo navigation rule: agents MUST NOT assume file locations and MUST use repository search.

Naming and interface conventions (mandatory):

- Python variable names MUST use `snake_case`.
- Node.js variable names MUST use `camelCase`.
- DataFrame column names and database-related naming (tables, columns, keys, persisted
  schema fields) MUST use `snake_case`.
- Constants and enum members MUST use `UPPER_SNAKE_CASE`.
- JSON keys for message passing MUST follow runtime language conventions:
  - Node.js message payload keys MUST use `camelCase`.
  - Python message payload keys MUST use `snake_case`.
- JSON keys saved to files (`.json`, `.jsonl`) MUST use `snake_case` regardless of runtime
  language.
- JavaScript functions MUST use an object parameter signature with a default empty object (for example, `function fn({ a, b } = {})`).
- Relative imports SHOULD be avoided. Prefer absolute imports or configured path aliases.

Boundary exception rule:

- When integrating with external contracts that require a specific key or naming format,
  agents MUST preserve the external contract at the boundary and map internally to the
  required naming convention for this repository.

When in doubt, agents MUST stop and ask a human.

## Workflow Compliance Requirements

Generated specifications MUST include a `Compliance Notes` section that summarizes:

- relevant constitution principles,
- applied UI behavior standards,
- cross-feature learnings used,
- and any conflicts plus the safest compliant resolution.

If a requested change conflicts with UI behavior standards or established learnings, agents
MUST explicitly call out the conflict and propose a compliant alternative.

## Governance

This constitution supersedes local conventions when they conflict.

Amendments:

- Any change to this document MUST be reviewed by a human maintainer.
- Amendment PRs MUST include the reason for change, compatibility impact, and any required
  follow-up migrations.

Versioning policy (semantic):

- MAJOR: backward-incompatible governance changes or principle removals.
- MINOR: new principle/section added or materially expanded guidance.
- PATCH: clarifications, wording, or typo fixes.

Compliance expectations:

- Every PR review MUST explicitly check Security and Secrets rules.
- If a change touches deployment or environment configuration, sensitive genomic data
  handling, or patient/clinical workflows, escalation to a human reviewer is mandatory.

Escalation triggers (agents MUST stop and ask a human):

- Any uncertainty about clinical meaning, units, interpretation, or data retention.
- Any need to change serverless/IAM/stage/environment/deployment behavior.
- Any request that might expose PHI/PII or other protected genomic/health-linked data.

**Version**: 1.4.0 | **Ratified**: TODO(RATIFICATION_DATE): Set when approved by human maintainer | **Last Amended**: 2026-03-04
