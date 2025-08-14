from __future__ import annotations
import os, base64, requests, threading
from typing import Dict, Any, Callable, Optional

from backend.memory_service import MemoryService

class JiraClient:
    def __init__(self, dry_run: Optional[bool] = None):
        self.base = os.getenv('JIRA_BASE_URL', '')
        self.user = os.getenv('JIRA_USER', '')
        self.token = os.getenv('JIRA_TOKEN', '')
        if dry_run is None:
            self.dry_run = os.getenv('JIRA_DRY_RUN', 'false').lower() == 'true'
        else:
            self.dry_run = dry_run
        self.memory = MemoryService()
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _headers(self):
        encoded = base64.b64encode(f"{self.user}:{self.token}".encode()).decode()
        return {'Authorization': f'Basic {encoded}', 'Content-Type': 'application/json'}

    def create_issue(self, project_key: str, summary: str, description: str) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'project': project_key, 'summary': summary}
        url = f"{self.base}/rest/api/3/issue"
        payload = {'fields': {'project': {'key': project_key}, 'summary': summary, 'issuetype': {'name': 'Task'}, 'description': description}}
        r = requests.post(url, headers=self._headers(), json=payload)
        r.raise_for_status()
        return r.json()

    def get_assigned_issues(self, assignee: str, max_results: int = 50) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'assignee': assignee, 'issues': []}
        url = f"{self.base}/rest/api/3/search"
        params = {'jql': f'assignee = "{assignee}" AND statusCategory != Done', 'maxResults': max_results}
        r = requests.get(url, headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        for issue in data.get('issues', []):
            key = issue.get('key')
            fields = issue.get('fields', {})
            summary = fields.get('summary', '')
            status = (fields.get('status') or {}).get('name', '')
            assignee_name = (fields.get('assignee') or {}).get('displayName', '')
            project = (fields.get('project') or {}).get('key', '')
            text = f"[{key}] {summary} — status: {status} — assignee: {assignee_name}"
            metadata = {
                'project': project,
                'status': status,
                'assignee': assignee_name,
                'jira_key': key,
            }
            self.memory.add_task(key, text, metadata=metadata)
        return data

    def start_polling_assigned(self, assignee: str, interval: int, callback: Callable[[Dict[str, Any]], None]):
        """Poll assigned issues on a schedule and invoke callback with results."""
        if self._poll_thread and self._poll_thread.is_alive():
            return

        self._stop_event.clear()

        def _poll():
            while not self._stop_event.is_set():
                issues = self.get_assigned_issues(assignee)
                try:
                    callback(issues)
                finally:
                    self._stop_event.wait(interval)

        self._poll_thread = threading.Thread(target=_poll, daemon=True)
        self._poll_thread.start()

    def stop_polling(self):
        if self._poll_thread:
            self._stop_event.set()
            if threading.current_thread() != self._poll_thread:
                self._poll_thread.join(timeout=0.1)
            self._poll_thread = None
