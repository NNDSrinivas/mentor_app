from __future__ import annotations
import os
import time
import logging
from typing import Dict, Any

import requests
from requests import RequestException

log = logging.getLogger(__name__)

class JiraClient:
    def __init__(self):
        self.base = os.getenv('JIRA_BASE_URL', '')
        self.user = os.getenv('JIRA_USER', '')
        self.token = os.getenv('JIRA_TOKEN', '')
        self.dry_run = True  # flip when approved

    def _headers(self):
        return {'Authorization': f'Basic {self.user}:{self.token}', 'Content-Type': 'application/json'}

    def _request(self, method: str, url: str, retries: int = 3, **kwargs) -> requests.Response:
        """Perform HTTP request with simple retries and error handling."""
        for attempt in range(1, retries + 1):
            try:
                response = requests.request(method, url, headers=self._headers(), **kwargs)
                response.raise_for_status()
                return response
            except RequestException as e:
                log.error("Jira API request failed (attempt %s/%s): %s", attempt, retries, e)
                if attempt == retries:
                    raise RuntimeError(f"Jira API request failed: {e}") from e
                time.sleep(2 * attempt)

    def create_issue(self, project_key: str, summary: str, description: str) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'project': project_key, 'summary': summary}
        url = f"{self.base}/rest/api/3/issue"
        payload = {
            'fields': {
                'project': {'key': project_key},
                'summary': summary,
                'issuetype': {'name': 'Task'},
                'description': description,
            }
        }
        response = self._request('post', url, json=payload)
        return response.json()
