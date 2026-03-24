from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from Bio import SeqIO
from tqdm.auto import tqdm

FASTA_FILE_NAME = "protein.faa"


@dataclass(slots=True)
class ParseIssue:
    file_path: str
    assembly_id: str | None
    issue_type: str
    issue_message: str
    record_identifier: str | None = None


@dataclass(slots=True)
class FastaRecord:
    assembly_id: str
    sequence_id: str
    ambiguous_residues: str
    # file_path: str
    functional_annotations: str
    raw_header: str
    sequence_length: int
    sequence: str

    def to_dict(self):
        return {slot: getattr(self, slot) for slot in self.__slots__ if getattr(self, slot) is not None}


def discover_fasta_files(data_root: str | Path) -> list[Path]:
    root_path = Path(data_root)
    if not root_path.exists():
        raise FileNotFoundError(f"DATA_ROOT does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"DATA_ROOT is not a directory: {root_path}")
    return sorted(root_path.rglob(FASTA_FILE_NAME))


def infer_assembly_id(file_path: str | Path) -> str:
    path = Path(file_path)
    return path.parent.name


def extract_header_fields(raw_header: str) -> tuple[dict[str, object], bool]:
    header_text = raw_header.strip()
    if not header_text:
        return {"header_remainder": ""}, True

    parts = header_text.split(maxsplit=1)
    if not parts[0]:
        return {"header_remainder": header_text}, True

    fields: dict[str, object] = {
        "sequence_id_token": parts[0],
        "header_remainder": parts[1] if len(parts) > 1 else "",
    }

    bracket_segments: list[str] = []
    remainder = fields["header_remainder"]
    if isinstance(remainder, str):
        start = 0
        while True:
            left = remainder.find("[", start)
            if left == -1:
                break
            right = remainder.find("]", left + 1)
            if right == -1:
                return fields, True
            bracket_segments.append(remainder[left + 1 : right].strip())
            start = right + 1

    if bracket_segments:
        fields["header_annotations"] = bracket_segments

    return fields, False


def extract_ambiguous_residues(sequence: str) -> set[str]:
    canonical = set("ACDEFGHIKLMNPQRSTVWY")
    return set(sequence) - canonical


def extract_functional_annotations(raw_header: str) -> list[str]:
    parts = raw_header.strip().split(" ")
    if len(parts) <= 1:
        return []
    return " ".join(parts[1:]).split("[")[0].strip()


def parse_fasta_file(file_path):
    parsed_records = []
    parse_issues = []
    assembly_id = infer_assembly_id(file_path)

    try:
        with Path(file_path).open("r", encoding="utf-8") as handle:
            entries = list(SeqIO.parse(handle, "fasta"))
    except Exception as exc:
        return [], [
            ParseIssue(
                file_path=str(file_path),
                assembly_id=assembly_id,
                issue_type="read_error",
                issue_message=str(exc),
            )
        ]

    for entry in entries:
        raw_header = str(entry.description).strip()
        sequence = str(entry.seq).strip()
        sequence_id = str(entry.id)
        ambiguous_residues = extract_ambiguous_residues(sequence)

        if not sequence:
            parse_issues.append(
                ParseIssue(
                    file_path=str(file_path),
                    assembly_id=assembly_id,
                    issue_type="empty_sequence",
                    issue_message="FASTA record has no sequence residues",
                    record_identifier=sequence_id or None,
                )
            )
            continue

        parsed_records.append(
            FastaRecord(
                assembly_id=assembly_id,
                sequence_id=sequence_id,
                ambiguous_residues="".join(sorted(ambiguous_residues)) if ambiguous_residues else "",
                # file_path=str(file_path),
                functional_annotations=extract_functional_annotations(raw_header),
                raw_header=raw_header,
                sequence_length=len(sequence),
                sequence=sequence,
            )
        )

    return parsed_records, parse_issues


def parse_fasta_corpus(data_root: str | Path, sample_size: int) -> Iterable[tuple[list[FastaRecord], list[ParseIssue]]]:
    fasta_files = discover_fasta_files(data_root)
    print(f"Discovered {len(fasta_files)} FASTA files in {data_root}")

    if sample_size is not None and sample_size > 0:
        fasta_files = fasta_files[:sample_size]
        print(f"Sampling first {len(fasta_files)} FASTA files for parsing")

    for fasta_file in tqdm(fasta_files, desc="Parsing FASTA files"):
        yield parse_fasta_file(fasta_file)
