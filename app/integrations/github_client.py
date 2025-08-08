from __future__ import annotations
import os, requests
from typing import Optional, Dict, Any

GITHUB_API = os.getenv('GITHUB_API', 'https://api.github.com')

class GitHubClient:
    def __init__(self, token_env: str = 'GITHUB_TOKEN', dry_run: Optional[bool] = None):
        self.token = os.getenv(token_env, '')
        if dry_run is None:
            dry_run = os.getenv('GITHUB_DRY_RUN', 'true').lower() != 'false'
        self.dry_run = dry_run

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github+json'
        }

    def create_pr(self, owner: str, repo: str, head: str, base: str, title: str, body: str) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'title': title, 'head': head, 'base': base}
        url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
        r = requests.post(url, headers=self._headers(), json={'title': title, 'head': head, 'base': base, 'body': body})
        r.raise_for_status()
        return r.json()

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'issue': issue_number}
        url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}"
        r = requests.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def update_issue_status(self, owner: str, repo: str, issue_number: int, state: str) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'issue': issue_number, 'state': state}
        url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}"
        r = requests.patch(url, headers=self._headers(), json={'state': state})
        r.raise_for_status()
        return r.json()

    def get_pr_comments(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'pr': pr_number}
        url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        r = requests.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def post_pr_comment(self, owner: str, repo: str, pr_number: int, body: str) -> Dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'pr': pr_number, 'body': body}
        url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        r = requests.post(url, headers=self._headers(), json={'body': body})
        r.raise_for_status()
        return r.json()
