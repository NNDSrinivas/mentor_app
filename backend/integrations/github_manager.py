# backend/integrations/github_manager.py
from __future__ import annotations
import os, base64, requests, json
from typing import Dict, Any, Optional, List, cast

GITHUB_API = os.getenv("GITHUB_API", "https://api.github.com")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

def _h():
    return {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

class GitHubManager:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run

    def create_branch(self, owner: str, repo: str, base_branch: str, new_branch: str) -> Dict[str, Any]:
        """Create a new branch from base branch"""
        if self.dry_run:
            return {"dry_run": True, "owner":owner,"repo":repo,"base":base_branch,"new":new_branch}
        
        # Get SHA of base branch
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{base_branch}", headers=_h())
        r.raise_for_status()
        sha = r.json()["object"]["sha"]
        
        # Create new branch
        r = requests.post(f"{GITHUB_API}/repos/{owner}/{repo}/git/refs", headers=_h(),
                          json={"ref": f"refs/heads/{new_branch}", "sha": sha})
        r.raise_for_status()
        return r.json()

    def commit_file(self, owner: str, repo: str, branch: str, path: str, content_bytes: bytes, message: str) -> Dict[str, Any]:
        """Create or update a file with a commit"""
        if self.dry_run:
            return {"dry_run": True, "path": path, "branch": branch, "message": message}
        
        b64 = base64.b64encode(content_bytes).decode()
        payload = {"message": message, "content": b64, "branch": branch}
        
        # Check if file exists to get SHA for updates
        try:
            r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}?ref={branch}", headers=_h())
            if r.status_code == 200:
                payload["sha"] = r.json()["sha"]
        except:
            pass  # File doesn't exist, create new
        
        r = requests.put(f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}", headers=_h(), json=payload)
        r.raise_for_status()
        return r.json()

    def create_pr(self, owner: str, repo: str, head: str, base: str, title: str, body: str = "") -> Dict[str, Any]:
        """Create a pull request"""
        if self.dry_run:
            return {"dry_run": True, "title": title, "head": head, "base": base}
        
        r = requests.post(f"{GITHUB_API}/repos/{owner}/{repo}/pulls", headers=_h(),
                          json={"title": title, "head": head, "base": base, "body": body})
        r.raise_for_status()
        return r.json()

    def comment_pr(self, owner: str, repo: str, pr_number: int, body: str) -> Dict[str, Any]:
        """Add comment to pull request"""
        if self.dry_run:
            return {"dry_run": True, "pr": pr_number, "body": body}
        
        r = requests.post(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments", headers=_h(),
                          json={"body": body})
        r.raise_for_status()
        return r.json()

    def get_pr(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get pull request details (read-only)"""
        if self.dry_run:
            return {"dry_run": True, "pr": pr_number, "mock_data": {"number": pr_number, "title": "Mock PR"}}
        
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}", headers=_h())
        r.raise_for_status()
        return r.json()

    def list_prs(self, owner: str, repo: str, state: str = "open", base: Optional[str] = None) -> Dict[str, Any]:
        """List pull requests (read-only)"""
        if self.dry_run:
            return {"dry_run": True, "state": state, "prs": []}
        
        params = {"state": state}
        if base:
            params["base"] = base
        
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls", headers=_h(), params=params)
        r.raise_for_status()
        return r.json()

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get files changed in PR (read-only)"""
        if self.dry_run:
            return {"dry_run": True, "pr": pr_number, "files": []}
        
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files", headers=_h())
        r.raise_for_status()
        return r.json()

    def get_pr_comments(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get PR comments (read-only)"""
        if self.dry_run:
            return {"dry_run": True, "pr": pr_number, "comments": []}

        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments", headers=_h())
        r.raise_for_status()
        return r.json()

    def get_review_comments(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get code review comments for a PR (read-only)"""
        if self.dry_run:
            return {"dry_run": True, "pr": pr_number, "comments": []}

        r = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/comments",
            headers=_h(),
        )
        r.raise_for_status()
        return r.json()

    def merge_pr(self, owner: str, repo: str, pr_number: int, commit_title: str = "", commit_message: str = "", merge_method: str = "merge") -> Dict[str, Any]:
        """Merge a pull request"""
        if self.dry_run:
            return {"dry_run": True, "pr": pr_number, "method": merge_method}
        
        payload = {"merge_method": merge_method}
        if commit_title:
            payload["commit_title"] = commit_title
        if commit_message:
            payload["commit_message"] = commit_message
        
        r = requests.put(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/merge", headers=_h(), json=payload)
        r.raise_for_status()
        return r.json()

    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information (read-only)"""
        if self.dry_run:
            return {"dry_run": True, "owner": owner, "repo": repo}
        
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=_h())
        r.raise_for_status()
        return r.json()

    def get_check_runs(self, owner: str, repo: str, ref: str) -> Dict[str, Any]:
        """Get check runs for a ref (read-only)"""
        if self.dry_run:
            return {"dry_run": True, "ref": ref, "check_runs": []}
        
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/commits/{ref}/check-runs", headers=_h())
        r.raise_for_status()
        return r.json()

    def create_issue(self, owner: str, repo: str, title: str, body: str = "", labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a GitHub issue"""
        if self.dry_run:
            return {"dry_run": True, "title": title, "body": body}
        
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            cast(Any, payload)["labels"] = labels
        
        r = requests.post(f"{GITHUB_API}/repos/{owner}/{repo}/issues", headers=_h(), json=payload)
        r.raise_for_status()
        return r.json()

    def comment_issue(self, owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        """Add comment to an issue"""
        if self.dry_run:
            return {"dry_run": True, "issue": issue_number, "body": body}
        
        r = requests.post(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/comments", headers=_h(),
                          json={"body": body})
        r.raise_for_status()
        return r.json()
