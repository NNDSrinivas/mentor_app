from __future__ import annotations
import os, requests
from typing import Optional, Dict, Any, List

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

    def get_pr_reviews(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Return list of reviews for a pull request"""
        if self.dry_run:
            return {"dry_run": True, "pr": pr_number, "reviews": []}
        url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        r = requests.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def get_review_comments(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Return review comments for a pull request"""
        if self.dry_run:
            return {"dry_run": True, "pr": pr_number, "comments": []}
        url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        r = requests.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json()
