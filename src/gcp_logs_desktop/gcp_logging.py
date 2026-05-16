from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Callable

from .filters import build_bigquery_log_filter, normalize_project_names

EntryCallback = Callable[[int], None]


def iter_bigquery_log_entries(
    credentials: Any,
    projects: list[str],
    progress_callback: EntryCallback | None = None,
) -> Iterator[dict[str, Any]]:
    from google.cloud import logging_v2

    resource_names = normalize_project_names(projects)
    if not resource_names:
        raise ValueError("At least one GCP project is required.")
    client_project = resource_names[0].split("/", 1)[1]
    client = logging_v2.Client(project=client_project, credentials=credentials)
    log_filter = build_bigquery_log_filter()
    entries = client.list_entries(
        resource_names=resource_names,
        filter_=log_filter,
        order_by="timestamp desc",
        page_size=1000,
    )

    for count, entry in enumerate(entries, start=1):
        yield entry.to_api_repr()
        if progress_callback is not None:
            progress_callback(count)
