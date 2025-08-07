from __future__ import annotations
import os, requests
from typing import Optional, Dict, Any

GITHUB_API = os.getenv('GITHUB_API', 'https://api.github.com')

class GitHubClient:
    def __init__(self, token_env: str = 'GITHUB_TOKEN', dry_run: bool = True):
        self.token = os.getenv(token_env, '')
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
