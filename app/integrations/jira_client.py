from __future__ import annotations
import os, requests
from typing import Dict, Any

class JiraClient:
    def __init__(self):
        self.base = os.getenv('JIRA_BASE_URL', '')
        self.user = os.getenv('JIRA_USER', '')
        self.token = os.getenv('JIRA_TOKEN', '')
        self.dry_run = True  # flip when approved

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
