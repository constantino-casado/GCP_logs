from __future__ import annotations

import csv
import json
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
    if output_format == "jsonl":
        return _export_jsonl(rows, output_path, progress_callback)
    raise ValueError("Output format must be 'csv' or 'jsonl'.")


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


def _export_jsonl(rows: Iterable[dict[str, Any]], output_path: Path, progress_callback: ProgressCallback | None) -> int:
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")
            count += 1
            if progress_callback is not None:
                progress_callback(count)
    return count
