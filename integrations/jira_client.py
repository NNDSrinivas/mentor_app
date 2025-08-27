from __future__ import annotations
import os, base64, requests
from typing import Dict, Any, Optional

class JiraClient:
    """Minimal Jira client used by approvals worker."""

    def __init__(self, dry_run: Optional[bool] = None):
        self.base = os.getenv("JIRA_BASE_URL", "")
        self.user = os.getenv("JIRA_USER", "")
        self.token = os.getenv("JIRA_TOKEN", "")
        if dry_run is None:
            self.dry_run = os.getenv("APP_ENV", "").lower() != "prod"
        else:
            self.dry_run = dry_run

    def _headers(self) -> Dict[str, str]:
        raw = f"{self.user}:{self.token}".encode()
        encoded = base64.b64encode(raw).decode()
        return {"Authorization": "Basic " + encoded, "Content-Type": "application/json"}

    def create_issue(self, project_key: str, summary: str, description: str, issue_type: str = "Task") -> Dict[str, Any]:
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
                "description": description,
            }
        }
        if self.dry_run:
            return {"dry_run": True, "payload": payload}
        r = requests.post(f"{self.base}/rest/api/3/issue", headers=self._headers(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def update_issue(self, key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        if self.dry_run:
            return {"dry_run": True, "key": key, "fields": fields}
        r = requests.put(f"{self.base}/rest/api/3/issue/{key}", headers=self._headers(), json={"fields": fields}, timeout=30)
        r.raise_for_status()
        return r.json()

    def search(self, jql: str, max_results: int = 50) -> Dict[str, Any]:
        if self.dry_run:
            return {"dry_run": True, "jql": jql, "issues": []}
        params = {"jql": jql, "maxResults": max_results}
        r = requests.get(f"{self.base}/rest/api/3/search", headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def add_comment(self, key: str, comment: str) -> Dict[str, Any]:
        if self.dry_run:
            return {"dry_run": True, "key": key, "comment": comment}
        r = requests.post(f"{self.base}/rest/api/3/issue/{key}/comment", headers=self._headers(), json={"body": comment}, timeout=30)
        r.raise_for_status()
        return r.json()

    def transition_issue(self, key: str, transition_id: str, comment: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"transition": {"id": transition_id}}
        if comment:
            payload["update"] = {"comment": [{"add": {"body": comment}}]}
        if self.dry_run:
            return {"dry_run": True, "key": key, "transition_id": transition_id, "comment": comment}
        r = requests.post(f"{self.base}/rest/api/3/issue/{key}/transitions", headers=self._headers(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
