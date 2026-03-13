from __future__ import annotations

from collections import Counter
from typing import Iterable

VALID_STRATEGIES = {"single", "3-mer", "5-mer", "BPE"}
VALID_AMBIGUOUS_RESIDUE_MODES = {
    "keep",
    "replace_with_unk",
    "normalize_selected",
    "drop_sequence",
}
VALID_RARE_RESIDUE_POLICIES = {
    "keep",
    "replace_with_unk",
    "normalize_selected",
    "drop_sequence",
}
NORMALIZATION_MAP = {
    "U": "C",
    "O": "K",
}
CANONICAL_RESIDUES = set("ACDEFGHIKLMNPQRSTVWY")
UNK_TOKEN = "[UNK]"


def validate_config(
    tokenization_strategies: Iterable[str],
    ambiguous_residue_mode: str,
    rare_residue_policy: str,
) -> None:
    invalid_strategies = [strategy for strategy in tokenization_strategies if strategy not in VALID_STRATEGIES]
    if invalid_strategies:
        raise ValueError(f"Invalid tokenization strategies: {invalid_strategies}")
    if ambiguous_residue_mode not in VALID_AMBIGUOUS_RESIDUE_MODES:
        raise ValueError(f"Invalid AMBIGUOUS_RESIDUE_MODE: {ambiguous_residue_mode}")
    if rare_residue_policy not in VALID_RARE_RESIDUE_POLICIES:
        raise ValueError(f"Invalid RARE_RESIDUE_POLICY: {rare_residue_policy}")


def normalize_sequence(sequence: str) -> str:
    residues: list[str] = []
    for residue in sequence:
        residues.append(NORMALIZATION_MAP.get(residue.upper(), residue.upper()))
    return "".join(residues)


def apply_residue_policy(sequence: str, ambiguous_residue_mode: str, rare_residue_policy: str) -> str | None:
    processed = normalize_sequence(sequence) if ambiguous_residue_mode == "normalize_selected" else sequence.upper()
    output_tokens: list[str] = []
    for residue in processed:
        is_canonical = residue in CANONICAL_RESIDUES
        if is_canonical:
            output_tokens.append(residue)
            continue
        policy = ambiguous_residue_mode
        if residue in NORMALIZATION_MAP:
            policy = rare_residue_policy
        if policy == "keep":
            output_tokens.append(residue)
        elif policy == "replace_with_unk":
            output_tokens.append(UNK_TOKEN)
        elif policy == "normalize_selected":
            normalized = NORMALIZATION_MAP.get(residue)
            if normalized is None:
                output_tokens.append(UNK_TOKEN)
            else:
                output_tokens.append(normalized)
        elif policy == "drop_sequence":
            return None
    return "".join(output_tokens)


def tokenize_single(sequence: str) -> list[str]:
    return list(sequence)


def tokenize_overlapping_kmers(sequence: str, kmer_size: int) -> list[str]:
    if len(sequence) < kmer_size:
        return []
    return [sequence[index : index + kmer_size] for index in range(0, len(sequence) - kmer_size + 1)]


def summarize_token_frequencies(token_sequences: Iterable[list[str]]) -> Counter[str]:
    frequency_counter: Counter[str] = Counter()
    for token_sequence in token_sequences:
        frequency_counter.update(token_sequence)
    return frequency_counter
