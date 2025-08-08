# backend/integrations/jira_manager.py
from __future__ import annotations
import os, base64, requests
from typing import Dict, Any, Optional

JIRA_BASE = os.getenv("JIRA_BASE_URL", "")
JIRA_USER = os.getenv("JIRA_USER", "")
JIRA_TOKEN = os.getenv("JIRA_TOKEN", "")

def _auth():
    raw = f"{JIRA_USER}:{JIRA_TOKEN}".encode()
    return {"Authorization": "Basic " + base64.b64encode(raw).decode(), "Content-Type":"application/json"}

class JiraManager:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run

    def create_issue(self, project_key: str, summary: str, description: str, issue_type="Task") -> Dict[str, Any]:
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
                "description": description
            }
        }
        if self.dry_run:
            return {"dry_run": True, "payload": payload}

        r = requests.post(f"{JIRA_BASE}/rest/api/3/issue", headers=_auth(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def update_issue(self, key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        if self.dry_run:
            return {"dry_run": True, "key": key, "fields": fields}
        r = requests.put(f"{JIRA_BASE}/rest/api/3/issue/{key}", headers=_auth(), json={"fields": fields}, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_issue(self, key: str) -> Dict[str, Any]:
        """Get issue details (read-only, no approval needed)"""
        if self.dry_run:
            return {"dry_run": True, "key": key, "mock_data": {"key": key, "fields": {"summary": "Mock issue"}}}
        
        r = requests.get(f"{JIRA_BASE}/rest/api/3/issue/{key}", headers=_auth(), timeout=30)
        r.raise_for_status()
        return r.json()

    def search_issues(self, jql: str, max_results: int = 50) -> Dict[str, Any]:
        """Search issues (read-only, no approval needed)"""
        if self.dry_run:
            return {"dry_run": True, "jql": jql, "issues": []}
        
        params = {"jql": jql, "maxResults": max_results}
        r = requests.get(f"{JIRA_BASE}/rest/api/3/search", headers=_auth(), params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def add_comment(self, key: str, comment: str) -> Dict[str, Any]:
        """Add comment to issue"""
        payload = {"body": comment}
        if self.dry_run:
            return {"dry_run": True, "key": key, "comment": comment}

        r = requests.post(f"{JIRA_BASE}/rest/api/3/issue/{key}/comment", headers=_auth(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def transition_issue(self, key: str, transition_id: str, comment: Optional[str] = None) -> Dict[str, Any]:
        """Transition issue status (move through workflow)"""
        payload = {"transition": {"id": transition_id}}
        if comment:
            payload["update"] = {"comment": [{"add": {"body": comment}}]}
        
        if self.dry_run:
            return {"dry_run": True, "key": key, "transition_id": transition_id, "comment": comment}

        r = requests.post(f"{JIRA_BASE}/rest/api/3/issue/{key}/transitions", headers=_auth(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_transitions(self, key: str) -> Dict[str, Any]:
        """Get available transitions for an issue (read-only)"""
        if self.dry_run:
            return {"dry_run": True, "key": key, "transitions": [{"id": "1", "name": "In Progress"}, {"id": "2", "name": "Done"}]}
        
        r = requests.get(f"{JIRA_BASE}/rest/api/3/issue/{key}/transitions", headers=_auth(), timeout=30)
        r.raise_for_status()
        return r.json()
