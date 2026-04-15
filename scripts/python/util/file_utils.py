from __future__ import annotations

import json
from pathlib import Path

import pyarrow.dataset as ds
from tqdm.auto import tqdm

PREVIEW_ROW_LIMIT = 100


def ensure_exists(path, label):
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")


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


def find_project_root(start):
    for candidate in [start] + list(start.parents):
        if (candidate / "package.json").exists() and (candidate / "results").exists():
            return candidate
    raise FileNotFoundError("Could not locate the repository root from the current notebook working directory.")


def parquet_to_txt(parquet_path, output_txt_path, column="sequence", batch_size=100_000):
    dataset = ds.dataset(parquet_path, format="parquet")

    with open(output_txt_path, "w") as f:
        for batch in iter_dataset(dataset, batch_size=batch_size, desc="Converting parquet to txt"):
            arr = batch[column]

            # convert to python list (only this batch in memory)
            values = arr.to_pylist()

            for v in values:
                if v is not None:
                    f.write(v)
                    f.write("\n")
