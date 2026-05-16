from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CaptureConfig:
    auth_mode: str
    projects: list[str]
    output_path: Path
    output_format: str = "csv"
    service_account_file: Path | None = None
    anonymize_email: bool = True
    hash_query_text: bool = True

    def validate(self) -> None:
        if self.auth_mode not in {"adc", "service_account"}:
            raise ValueError("Authentication mode must be 'adc' or 'service_account'.")
        if self.auth_mode == "service_account":
            if self.service_account_file is None:
                raise ValueError("A service account JSON file is required.")
            if not self.service_account_file.exists():
                raise ValueError(f"Service account file does not exist: {self.service_account_file}")
        if not self.projects:
            raise ValueError("At least one GCP project is required.")
        if self.output_format not in {"csv", "parquet"}:
            raise ValueError("Output format must be 'csv' or 'parquet'.")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
