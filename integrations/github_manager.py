from __future__ import annotations
import os
import base64
import requests
from typing import Dict, Any, Optional

GITHUB_API = os.getenv("GITHUB_API", "https://api.github.com")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

class GitHubManager:
    """Minimal GitHub client used across backend components."""

    def __init__(self, dry_run: Optional[bool] = None):
        if dry_run is None:
            self.dry_run = os.getenv("APP_ENV", "").lower() != "prod"
        else:
            self.dry_run = dry_run

    # --- Write operations -------------------------------------------------
    def comment_pr(self, owner: str, repo: str, pr_number: int, body: str) -> Dict[str, Any]:
        """Post a comment on a pull request."""
        if self.dry_run:
            return {"dry_run": True, "pr": pr_number, "body": body}
        r = requests.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
            headers=_headers(),
            json={"body": body},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def create_branch(self, owner: str, repo: str, base_branch: str, new_branch: str) -> Dict[str, Any]:
        """Create ``new_branch`` from ``base_branch``."""
        if self.dry_run:
            return {
                "dry_run": True,
                "owner": owner,
                "repo": repo,
                "base": base_branch,
                "new": new_branch,
            }
        r = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{base_branch}",
            headers=_headers(),
            timeout=30,
        )
        r.raise_for_status()
        sha = r.json()["object"]["sha"]
        r = requests.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/refs",
            headers=_headers(),
            json={"ref": f"refs/heads/{new_branch}", "sha": sha},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def commit_file(
        self,
        owner: str,
        repo: str,
        branch: str,
        path: str,
        content_bytes: bytes,
        message: str,
    ) -> Dict[str, Any]:
        """Create or update a file on ``branch``."""
        if self.dry_run:
            return {"dry_run": True, "path": path, "branch": branch}
        b64 = base64.b64encode(content_bytes).decode()
        payload: Dict[str, Any] = {"message": message, "content": b64, "branch": branch}
        try:
            r = requests.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}?ref={branch}",
                headers=_headers(),
                timeout=30,
            )
            if r.status_code == 200:
                payload["sha"] = r.json().get("sha")
        except Exception:
            pass
        r = requests.put(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def create_pr(
        self,
        owner: str,
        repo: str,
        head: str,
        base: str,
        title: str,
        body: str = "",
    ) -> Dict[str, Any]:
        """Open a pull request."""
        if self.dry_run:
            return {"dry_run": True, "title": title, "head": head, "base": base}
        r = requests.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
            headers=_headers(),
            json={"title": title, "head": head, "base": base, "body": body},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
