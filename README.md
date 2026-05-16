# GCP BigQuery Logs Desktop App

This repository contains a local desktop app for downloading, filtering, and anonymizing Google Cloud BigQuery audit logs from a user's computer.

The implementation is based on the Fabric notebook **Full process**. The notebook used Spark to transform and export the data; this desktop version keeps the same overall flow but replaces Spark with standard local Python processing and streaming CSV/JSONL exports.

## What the app does

- Authenticates with GCP using gcloud Application Default Credentials or a service account JSON file.
- Discovers the active GCP projects visible to the authenticated identity.
- Lets the user select one or more projects from a multi-selection project list.
- Downloads BigQuery `jobservice.jobcompleted` log entries from the selected GCP projects.
- Uses the same Cloud Logging API filter as the Fabric notebook: last 30 days, BigQuery resources, `INFO` severity, and completed BigQuery jobs.
- Flattens the same BigQuery audit-log fields used by the notebook, including user, method, query, job statistics, and referenced tables.
- Anonymizes `principalEmail` with the same SHA-256 hex digest behavior as Spark `sha2(value, 256)`.
- Optionally hashes SQL query string literals and email-like values before export so repeated values can still be identified without exposing the raw values.
- Streams results to local `.csv` or `.jsonl` files without requiring Spark, Fabric, Delta Lake, or a Lakehouse.

## Install

### Prerequisites

- Python 3.10 or later.
- Google Cloud CLI (`gcloud`). The app uses it to launch the Application Default Credentials browser sign-in flow automatically.

On Windows, install Google Cloud CLI with:

```powershell
winget install --id Google.CloudSDK --exact
```

If administrator installation is not available, install the Google Cloud CLI zip package into a user-local folder and add `google-cloud-sdk\bin` to `PATH`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

## Run

```powershell
gcp-bigquery-logs
```

Alternatively:

```powershell
python run_app.py
```

## GCP permissions

The authenticated user or service account needs permission to list visible projects and read Cloud Logging entries for the target projects. The app requests these scopes:

```text
https://www.googleapis.com/auth/cloud-platform
https://www.googleapis.com/auth/logging.read
https://www.googleapis.com/auth/cloud-platform.read-only
```

Project discovery uses the Cloud Resource Manager API. If authentication succeeds but no projects are shown, verify that the API is enabled and that the identity has permission to list projects.

## Authentication options

The recommended local sign-in option is **Automatic browser sign-in with gcloud**. The app checks for existing Application Default Credentials and, if they are missing or expired, runs the Google Cloud CLI sign-in flow automatically with the required scopes. Users do not need to run a separate terminal command.

This option requires the Google Cloud CLI to be installed and available as `gcloud`.

For service account authentication, select a service account JSON key with permissions to list projects and read logs.

## GUI flow

1. Start the app and authenticate with GCP.
2. After authentication, select one or more projects from the discovered project list.
3. Click **Execute log capture...**.
4. Choose where the exported `.csv` or `.jsonl` file should be stored.

The log query is intentionally not configurable in the GUI so it stays aligned with the source notebook:

```text
timestamp >= "<30 days ago>" AND resource.type="bigquery_resource" AND severity=INFO AND protoPayload.methodName="jobservice.jobcompleted"
```

## Output

The exported file includes flattened fields such as `timestamp`, `insertId`, `principalEmail`, `methodName`, `statementType`, `query`, `jobStatistics`, and `referencedTables`.

By default, email anonymization and query literal hashing are enabled.
