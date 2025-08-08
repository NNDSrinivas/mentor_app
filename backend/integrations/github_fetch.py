# backend/integrations/github_fetch.py
from __future__ import annotations
import os, requests
from typing import Dict, Any, List

GITHUB_API = os.getenv("GITHUB_API", "https://api.github.com")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN","")

def _h():
    return {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

def get_pr(owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
    r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}", headers=_h(), timeout=30)
    r.raise_for_status(); return r.json()

def get_pr_files(owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
    r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files", headers=_h(), timeout=30)
    r.raise_for_status(); return r.json()

def get_pr_comments(owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
    r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments", headers=_h(), timeout=30)
    r.raise_for_status(); return r.json()
