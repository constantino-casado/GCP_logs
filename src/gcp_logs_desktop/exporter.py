from __future__ import annotations

import csv
from datetime import datetime
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Callable

from .processor import EXPORT_FIELDS

ProgressCallback = Callable[[int], None]


def export_rows(
    rows: Iterable[dict[str, Any]],
    output_path: Path,
    output_format: str,
    progress_callback: ProgressCallback | None = None,
) -> int:
    if output_format == "csv":
        return _export_csv(rows, output_path, progress_callback)
    if output_format == "parquet":
        return _export_parquet(rows, output_path, progress_callback)
    raise ValueError("Output format must be 'csv' or 'parquet'.")


def timestamped_output_path(
    output_path: Path,
    output_format: str,
    extraction_time: datetime | None = None,
) -> Path:
    extraction_time = extraction_time or datetime.now()
    suffix = f".{output_format}"
    path = output_path if output_path.suffix.lower() == suffix else output_path.with_suffix(suffix)
    timestamp = extraction_time.strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.stem}_{timestamp}{path.suffix}")


def _export_csv(rows: Iterable[dict[str, Any]], output_path: Path, progress_callback: ProgressCallback | None) -> int:
    count = 0
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
            if progress_callback is not None:
                progress_callback(count)
    return count


def _export_parquet(rows: Iterable[dict[str, Any]], output_path: Path, progress_callback: ProgressCallback | None) -> int:
    import pyarrow as pa
    import pyarrow.parquet as pq

    count = 0
    schema = pa.schema([(field, pa.string()) for field in EXPORT_FIELDS])
    writer: pq.ParquetWriter | None = None
    batch: list[dict[str, str]] = []
    try:
        for row in rows:
            batch.append(_stringify_row(row))
            count += 1
            if progress_callback is not None:
                progress_callback(count)
            if len(batch) >= 1000:
                writer = _write_parquet_batch(batch, output_path, schema, writer)
                batch = []
        if batch or writer is None:
            writer = _write_parquet_batch(batch, output_path, schema, writer)
    finally:
        if writer is not None:
            writer.close()
    return count


def _write_parquet_batch(
    rows: list[dict[str, str]],
    output_path: Path,
    schema: Any,
    writer: Any,
) -> Any:
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.Table.from_pylist(rows, schema=schema)
    if writer is None:
        writer = pq.ParquetWriter(output_path, schema)
    writer.write_table(table)
    return writer


def _stringify_row(row: dict[str, Any]) -> dict[str, str]:
    return {field: "" if row.get(field) is None else str(row.get(field, "")) for field in EXPORT_FIELDS}
