from __future__ import annotations

from datetime import datetime, timedelta, timezone


def normalize_project_names(projects: list[str]) -> list[str]:
    normalized: list[str] = []
    for project in projects:
        value = project.strip()
        if not value:
            continue
        normalized.append(value if value.startswith("projects/") else f"projects/{value}")
    return normalized


def parse_projects(projects_text: str) -> list[str]:
    raw = projects_text.replace("\n", ",").split(",")
    return normalize_project_names(raw)


def rfc3339_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_bigquery_log_filter() -> str:
    start_time = datetime.now(timezone.utc) - timedelta(days=30)
    parts = [
        f'timestamp >= "{rfc3339_utc(start_time)}"',
        'resource.type="bigquery_resource"',
        "severity=INFO",
        'protoPayload.methodName="jobservice.jobcompleted"',
    ]
    return " AND ".join(parts)
