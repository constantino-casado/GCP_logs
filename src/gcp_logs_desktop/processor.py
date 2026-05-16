from __future__ import annotations

import hashlib
import json
import re
from typing import Any

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
STRING_LITERAL_PATTERN = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"")

EXPORT_FIELDS = [
    "timestamp",
    "logName",
    "insertId",
    "severity",
    "resource_type",
    "resource_labels",
    "principalEmail",
    "methodName",
    "callerSuppliedUserAgent",
    "resourceName",
    "serviceName",
    "statementType",
    "query",
    "jobName",
    "projectId",
    "location",
    "totalBilledBytes",
    "totalProcessedBytes",
    "totalSlotMs",
    "billingTier",
    "cacheHit",
    "referencedTables",
    "jobConfiguration",
    "jobStatistics",
]


def safe_get(value: dict[str, Any] | None, path: list[str], default: Any = None) -> Any:
    current: Any = value
    for part in path:
        if not isinstance(current, dict):
            return default
        current = current.get(part)
        if current is None:
            return default
    return current


def spark_sha2_256(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_query_literals(query: str | None) -> str | None:
    if query is None:
        return None
    literals_hashed = STRING_LITERAL_PATTERN.sub(lambda match: _hashed_literal(match.group(0)), query)
    return EMAIL_PATTERN.sub(lambda match: _hashed_placeholder(match.group(0), "email"), literals_hashed)


def _hashed_literal(raw_literal: str) -> str:
    quote = raw_literal[0]
    value = raw_literal[1:-1]
    if quote == "'":
        value = value.replace("''", "'")
    elif quote == '"':
        value = value.replace('""', '"')
    return f"'{_hash_value(value)}'"


def _hashed_placeholder(value: str, prefix: str) -> str:
    return f"<{prefix}:{_hash_value(value)}>"


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def json_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def flatten_bigquery_log_entry(
    api_entry: dict[str, Any],
    anonymize_email: bool = True,
    hash_query_text: bool = True,
) -> dict[str, Any]:
    proto = api_entry.get("protoPayload") or {}
    resource = api_entry.get("resource") or {}
    service_data = proto.get("serviceData") or {}
    job = safe_get(service_data, ["jobCompletedEvent", "job"], {}) or {}
    job_config = job.get("jobConfiguration") or {}
    query_config = job_config.get("query") or {}
    job_stats = job.get("jobStatistics") or {}
    job_name = job.get("jobName") or {}

    principal_email = safe_get(proto, ["authenticationInfo", "principalEmail"])
    query = query_config.get("query")

    row = {
        "timestamp": api_entry.get("timestamp"),
        "logName": api_entry.get("logName"),
        "insertId": api_entry.get("insertId"),
        "severity": api_entry.get("severity"),
        "resource_type": resource.get("type"),
        "resource_labels": json_value(resource.get("labels")),
        "principalEmail": spark_sha2_256(principal_email) if anonymize_email else principal_email,
        "methodName": proto.get("methodName") or proto.get("methodname"),
        "callerSuppliedUserAgent": safe_get(proto, ["requestMetadata", "callerSuppliedUserAgent"]),
        "resourceName": proto.get("resourceName"),
        "serviceName": proto.get("serviceName"),
        "statementType": query_config.get("statementType"),
        "query": hash_query_literals(query) if hash_query_text else query,
        "jobName": json_value(job_name),
        "projectId": job_name.get("projectId") if isinstance(job_name, dict) else None,
        "location": job_name.get("location") if isinstance(job_name, dict) else None,
        "totalBilledBytes": job_stats.get("totalBilledBytes"),
        "totalProcessedBytes": job_stats.get("totalProcessedBytes"),
        "totalSlotMs": job_stats.get("totalSlotMs"),
        "billingTier": job_stats.get("billingTier"),
        "cacheHit": job_stats.get("cacheHit") or query_config.get("cacheHit"),
        "referencedTables": json_value(job_stats.get("referencedTables") or query_config.get("referencedTables")),
        "jobConfiguration": json_value(job_config),
        "jobStatistics": json_value(job_stats),
    }
    return {field: row.get(field, "") for field in EXPORT_FIELDS}
