from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Any

LOGGING_READ_SCOPE = "https://www.googleapis.com/auth/logging.read"
PROJECTS_READ_SCOPE = "https://www.googleapis.com/auth/cloud-platform.read-only"
CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
GCP_AUTH_SCOPES = [CLOUD_PLATFORM_SCOPE, LOGGING_READ_SCOPE, PROJECTS_READ_SCOPE]


def load_credentials(
    auth_mode: str,
    service_account_file: Path | None = None,
) -> Any:
    if auth_mode == "adc":
        return _load_application_default_credentials()

    if auth_mode == "service_account":
        if service_account_file is None:
            raise ValueError("A service account JSON file is required.")

        from google.oauth2 import service_account

        return service_account.Credentials.from_service_account_file(
            str(service_account_file),
            scopes=GCP_AUTH_SCOPES,
        )

    raise ValueError("Authentication mode must be 'adc' or 'service_account'.")


def _load_application_default_credentials() -> Any:
    from google.auth.exceptions import DefaultCredentialsError, RefreshError

    try:
        return _load_existing_application_default_credentials()
    except (DefaultCredentialsError, RefreshError):
        _run_gcloud_application_default_login()
        return _load_existing_application_default_credentials()


def _load_existing_application_default_credentials() -> Any:
    import google.auth
    from google.auth.transport.requests import Request

    credentials, _project = google.auth.default(scopes=GCP_AUTH_SCOPES)
    if not credentials.valid:
        credentials.refresh(Request())
    return credentials


def _run_gcloud_application_default_login() -> None:
    gcloud = _find_gcloud_command()
    if gcloud is None:
        raise RuntimeError(
            "gcloud is required for automatic Application Default Credentials sign-in. "
            "Install the Google Cloud CLI, then restart the app."
        )

    command = [
        gcloud,
        "auth",
        "application-default",
        "login",
        f"--scopes={','.join(GCP_AUTH_SCOPES)}",
        "--quiet",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        if details:
            raise RuntimeError(f"gcloud authentication failed: {details}")
        raise RuntimeError("gcloud authentication failed.")


def _find_gcloud_command() -> str | None:
    gcloud = shutil.which("gcloud")
    if gcloud is not None:
        return gcloud

    local_app_data = Path.home() / "AppData" / "Local"
    candidates = [
        local_app_data / "Google" / "CloudSDK" / "google-cloud-sdk" / "bin" / "gcloud.cmd",
        Path("C:/Program Files (x86)/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"),
        Path("C:/Program Files/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None
