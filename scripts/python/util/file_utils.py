from __future__ import annotations

import json
from pathlib import Path

from tqdm.auto import tqdm

PREVIEW_ROW_LIMIT = 100


def ensure_directories(*paths: str | Path) -> None:
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def write_manifest(manifest: dict[str, object], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def iter_dataset(dataset, batch_size, desc="Processing rows"):
    total_rows = dataset.count_rows()
    scanner = dataset.scanner(batch_size=batch_size)

    with tqdm(total=total_rows, desc=desc, unit="rows", unit_scale=True, unit_divisor=1000) as pbar:
        for batch in scanner.to_batches():
            yield batch
            pbar.update(batch.num_rows)
