from __future__ import annotations
import os, requests
from typing import Dict, Any, Optional

class JiraClient:
    def __init__(self, dry_run: Optional[bool] = None):
        self.base = os.getenv('JIRA_BASE_URL', '')
        self.user = os.getenv('JIRA_USER', '')
        self.token = os.getenv('JIRA_TOKEN', '')
        if dry_run is None:
            dry_run = os.getenv('JIRA_DRY_RUN', 'true').lower() != 'false'
        self.dry_run = dry_run

    def _headers(self):
        return {'Authorization': f'Basic {self.user}:{self.token}', 'Content-Type': 'application/json'}

    def create_issue(self, project_key: str, summary: str, description: str) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'project': project_key, 'summary': summary}
        url = f"{self.base}/rest/api/3/issue"
        payload = {'fields': {'project': {'key': project_key}, 'summary': summary, 'issuetype': {'name': 'Task'}, 'description': description}}
        r = requests.post(url, headers=self._headers(), json=payload)
        r.raise_for_status()
        return r.json()

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'issue': issue_key}
        url = f"{self.base}/rest/api/3/issue/{issue_key}"
        r = requests.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def transition_issue(self, issue_key: str, transition_id: str) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'issue': issue_key, 'transition': transition_id}
        url = f"{self.base}/rest/api/3/issue/{issue_key}/transitions"
        r = requests.post(url, headers=self._headers(), json={'transition': {'id': transition_id}})
        r.raise_for_status()
        return r.json()
