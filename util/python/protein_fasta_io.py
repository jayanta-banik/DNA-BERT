from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from Bio import SeqIO
from tqdm.auto import tqdm

FASTA_FILE_NAME = "protein.faa"


@dataclass(slots=True)
class FastaRecord:
    assembly_id: str
    file_path: str
    sequence_id: str
    raw_header: str
    header_fields: dict[str, object]
    sequence: str
    sequence_length: int
    contains_ambiguous_residue: bool
    header_is_malformed: bool
    parse_status: str


@dataclass(slots=True)
class ParseIssue:
    file_path: str
    assembly_id: str | None
    issue_type: str
    issue_message: str
    record_identifier: str | None = None


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


def contains_ambiguous_residue(sequence: str) -> bool:
    canonical = set("ACDEFGHIKLMNPQRSTVWY")
    return any(residue.upper() not in canonical for residue in sequence)


def parse_fasta_file(file_path: str | Path) -> tuple[list[FastaRecord], list[ParseIssue]]:
    parsed_records: list[FastaRecord] = []
    parse_issues: list[ParseIssue] = []
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
        header_fields, header_is_malformed = extract_header_fields(raw_header)
        sequence_id = str(entry.id or header_fields.get("sequence_id_token") or "")
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

        parse_status = "parsed"
        if header_is_malformed:
            parse_status = "malformed_header"
            parse_issues.append(
                ParseIssue(
                    file_path=str(file_path),
                    assembly_id=assembly_id,
                    issue_type="malformed_header",
                    issue_message="Header does not match expected parseable structure",
                    record_identifier=sequence_id or None,
                )
            )

        parsed_records.append(
            FastaRecord(
                assembly_id=assembly_id,
                file_path=str(file_path),
                sequence_id=sequence_id or raw_header,
                raw_header=raw_header,
                header_fields=header_fields,
                sequence=sequence,
                sequence_length=len(sequence),
                contains_ambiguous_residue=contains_ambiguous_residue(sequence),
                header_is_malformed=header_is_malformed,
                parse_status=parse_status,
            )
        )

    return parsed_records, parse_issues


def parse_fasta_corpus(data_root: str | Path) -> tuple[list[FastaRecord], list[ParseIssue], list[Path]]:
    fasta_files = discover_fasta_files(data_root)
    all_records: list[FastaRecord] = []
    all_issues: list[ParseIssue] = []

    for fasta_file in tqdm(fasta_files, desc="Parsing FASTA files"):
        parsed_records, parse_issues = parse_fasta_file(fasta_file)
        all_records.extend(parsed_records)
        all_issues.extend(parse_issues)

    return all_records, all_issues, fasta_files
