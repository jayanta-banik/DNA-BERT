from __future__ import annotations

from protein_fasta_io import extract_header_fields


def summarize_header_metadata(raw_header: str) -> dict[str, object]:
    header_fields, header_is_malformed = extract_header_fields(raw_header)
    return {
        "raw_header": raw_header,
        "header_fields": header_fields,
        "header_is_malformed": header_is_malformed,
    }
