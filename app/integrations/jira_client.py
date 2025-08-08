from __future__ import annotations

import base64
import os
from typing import Any, Dict, List

import requests


class JiraClient:
    """Simple JIRA REST API client."""

    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        token: str | None = None,
        dry_run: bool = True,
    ) -> None:
        self.base = base_url or os.getenv("JIRA_BASE_URL", "")
        # Support legacy environment variable names
        self.email = email or os.getenv("JIRA_EMAIL", os.getenv("JIRA_USER", ""))
        self.token = token or os.getenv("JIRA_API_TOKEN", os.getenv("JIRA_TOKEN", ""))
        self.dry_run = dry_run

    def _headers(self) -> Dict[str, str]:
        auth = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_assigned_issues(self) -> List[Dict[str, Any]]:
        """Fetch issues assigned to the current user."""
        url = f"{self.base}/rest/api/3/search"
        params = {
            "jql": "assignee=currentUser() AND statusCategory != Done ORDER BY created DESC"
        }
        r = requests.get(url, headers=self._headers(), params=params)
        r.raise_for_status()
        return r.json().get("issues", [])

    def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an issue."""
        if self.dry_run:
            return {"dry_run": True, "issue": issue_key, "comment": comment}
        url = f"{self.base}/rest/api/3/issue/{issue_key}/comment"
        payload = {"body": comment}
        r = requests.post(url, headers=self._headers(), json=payload)
        r.raise_for_status()
        return r.json()

    def transition_issue(self, issue_key: str, transition_id: str) -> Dict[str, Any]:
        """Transition an issue to a new status."""
        if self.dry_run:
            return {"dry_run": True, "issue": issue_key, "transition": transition_id}
        url = f"{self.base}/rest/api/3/issue/{issue_key}/transitions"
        payload = {"transition": {"id": transition_id}}
        r = requests.post(url, headers=self._headers(), json=payload)
        r.raise_for_status()
        return r.json()

    def create_issue(
        self, project_key: str, summary: str, description: str
    ) -> Dict[str, Any]:
        """Create a new task issue."""
        if self.dry_run:
            return {"dry_run": True, "project": project_key, "summary": summary}
        url = f"{self.base}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": "Task"},
                "description": description,
            }
        }
        r = requests.post(url, headers=self._headers(), json=payload)
        r.raise_for_status()
        return r.json()
