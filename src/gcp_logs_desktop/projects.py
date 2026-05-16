from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode


@dataclass(frozen=True)
class GcpProject:
    project_id: str
    display_name: str
    project_number: str

    @property
    def resource_name(self) -> str:
        return f"projects/{self.project_id}"

    @property
    def label(self) -> str:
        if self.display_name and self.display_name != self.project_id:
            return f"{self.display_name} ({self.project_id})"
        return self.project_id


def list_available_projects(credentials: Any) -> list[GcpProject]:
    from google.auth.transport.requests import AuthorizedSession

    session = AuthorizedSession(credentials)
    projects: list[GcpProject] = []
    page_token = ""

    while True:
        query = {"pageSize": "1000"}
        if page_token:
            query["pageToken"] = page_token
        url = f"https://cloudresourcemanager.googleapis.com/v1/projects?{urlencode(query)}"
        response = session.get(url, timeout=60)
        if response.status_code == 403:
            raise PermissionError(
                "Authenticated successfully, but project discovery was denied. "
                "Enable Cloud Resource Manager API and grant permission to list projects."
            )
        response.raise_for_status()
        payload = response.json()

        for item in payload.get("projects", []):
            if item.get("lifecycleState") != "ACTIVE":
                continue
            project_id = item.get("projectId")
            if not project_id:
                continue
            projects.append(
                GcpProject(
                    project_id=project_id,
                    display_name=item.get("name") or project_id,
                    project_number=str(item.get("projectNumber") or ""),
                )
            )

        page_token = payload.get("nextPageToken") or ""
        if not page_token:
            break

    projects.sort(key=lambda project: project.label.lower())
    return projects
