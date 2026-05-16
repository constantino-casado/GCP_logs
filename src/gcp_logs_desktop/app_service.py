from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from .auth import load_credentials
from .config import CaptureConfig
from .exporter import export_rows
from .gcp_logging import iter_bigquery_log_entries
from .processor import flatten_bigquery_log_entry

StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[int], None]


def capture_logs(
    config: CaptureConfig,
    status_callback: StatusCallback | None = None,
    progress_callback: ProgressCallback | None = None,
    credentials: Any | None = None,
) -> int:
    config.validate()
    if credentials is None:
        _status(status_callback, "Authenticating with Google Cloud...")
        credentials = load_credentials(config.auth_mode, config.service_account_file)

    _status(status_callback, "Downloading and processing BigQuery logs...")
    rows = _iter_processed_rows(config, credentials, progress_callback)
    count = export_rows(rows, config.output_path, config.output_format, progress_callback)
    _status(status_callback, f"Exported {count} rows to {config.output_path}")
    return count


def _iter_processed_rows(
    config: CaptureConfig,
    credentials: Any,
    progress_callback: ProgressCallback | None,
) -> Iterator[dict[str, Any]]:
    for api_entry in iter_bigquery_log_entries(
        credentials=credentials,
        projects=config.projects,
    ):
        yield flatten_bigquery_log_entry(
            api_entry,
            anonymize_email=config.anonymize_email,
            hash_query_text=config.hash_query_text,
        )


def _status(callback: StatusCallback | None, message: str) -> None:
    if callback is not None:
        callback(message)
