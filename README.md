# GCP BigQuery Logs Desktop App

This repository contains a local desktop app for downloading, filtering, and anonymizing Google Cloud BigQuery audit logs from a user's computer.

## What the app does

- Authenticates with GCP using gcloud Application Default Credentials or a service account JSON file.
- Discovers the active GCP projects visible to the authenticated identity.
- Lets the user select one or more projects from a multi-selection project list.
- Downloads BigQuery `jobservice.jobcompleted` log entries from the selected GCP projects.
- Uses the following Cloud Logging API filter: last 30 days, BigQuery resources, `INFO` severity, and completed BigQuery jobs.
- Flattens BigQuery audit-log fields including user, method, query, job statistics, and referenced tables.
- Anonymizes `principalEmail` with a deterministic SHA-256 hex digest.
- Optionally hashes SQL query string literals and email-like values before export so repeated values can still be identified without exposing the raw values.
- Exports results to local `.csv` or `.parquet` files.

## Install

### Prerequisites

- Python 3.10 or later.
- Google Cloud CLI (`gcloud`). The app uses it to launch the Application Default Credentials browser sign-in flow automatically.
- If using a service account, the file with the secrets for authentication. That account must have the permissions described in the permissions section. 

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
4. Choose where the exported `.csv` or `.parquet` file should be stored.

The log query is intentionally not configurable in the GUI to capture bigquery jobs executions information:

```text
timestamp >= "<30 days ago>" AND resource.type="bigquery_resource" AND severity=INFO AND protoPayload.methodName="jobservice.jobcompleted"
```

## Output

The exported file includes flattened fields such as `timestamp`, `insertId`, `principalEmail`, `methodName`, `statementType`, `query`, `jobStatistics`, and `referencedTables`.

The app automatically appends the extraction date and time to the selected output filename, for example `bq_logs_20260516_131045.csv` or `bq_logs_20260516_131045.parquet`.

By default, email anonymization and query literal hashing are enabled.

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
