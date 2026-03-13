from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PREVIEW_ROW_LIMIT = 5000


def ensure_output_directories(*paths: str | Path) -> None:
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def write_table_outputs(
    dataframe: pd.DataFrame,
    parquet_path: str | Path,
    csv_preview_path: str | Path,
    preview_row_limit: int = PREVIEW_ROW_LIMIT,
) -> list[dict[str, object]]:
    parquet_path = Path(parquet_path)
    csv_preview_path = Path(csv_preview_path)
    dataframe.to_parquet(parquet_path, index=False)
    dataframe.head(preview_row_limit).to_csv(csv_preview_path, index=False)
    return [
        {
            "artifact_name": parquet_path.stem,
            "artifact_role": "table",
            "storage_format": "parquet",
            "path": str(parquet_path),
            "analysis_scope": "configured",
            "source_view": None,
            "is_preview": False,
        },
        {
            "artifact_name": csv_preview_path.stem,
            "artifact_role": "table",
            "storage_format": "csv",
            "path": str(csv_preview_path),
            "analysis_scope": "configured",
            "source_view": None,
            "is_preview": True,
        },
    ]


def write_manifest(manifest: dict[str, object], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
