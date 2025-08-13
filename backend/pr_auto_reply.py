# backend/pr_auto_reply.py
from __future__ import annotations
import os
from typing import Dict, Any, List, Optional
from openai import OpenAI

from backend.integrations.github_manager import GitHubManager

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM = (
  "You are a senior/staff engineer reviewing a Pull Request. "
  "Propose concise, actionable review comments and, when possible, a minimal patch diff. "
  "Prefer small targeted patches; preserve author style; include trade-offs briefly."
)

def suggest_replies_and_patch(pr_title: str, pr_desc: str, files_changed: List[Dict[str, Any]], comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    files_changed: [{filename, patch}]  -- patch is unified diff
    comments: [{author, body, file, line}]
    """
    prompt = {
        "title": pr_title,
        "description": pr_desc,
        "files": [{"filename": f["filename"], "patch": f.get("patch","")} for f in files_changed[:20]],
        "comments": comments[-50:]
    }
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Context:\n{prompt}\n\nReturn JSON with keys: replies[], proposed_patch (unified diff or empty)."}
        ],
        temperature=0.2,
        response_format={"type":"json_object"}
    )
    data = resp.choices[0].message.content or ""
    # let the server validate JSON before acting
    return {"raw": data}


def fetch_pr_context(owner: str, repo: str, pr_number: int, mgr: Optional[GitHubManager] = None) -> Dict[str, Any]:
    """Fetch PR details, changed files and review comments."""
    mgr = mgr or GitHubManager(dry_run=True)
    pr = mgr.get_pr(owner, repo, pr_number)
    files = mgr.get_pr_files(owner, repo, pr_number)
    comments = mgr.get_review_comments(owner, repo, pr_number)
    return {"pr": pr, "files": files, "comments": comments}


def parse_comment_action(body: str) -> Optional[str]:
    """Return requested action from a comment if present."""
    text = body.strip().lower()
    if text.startswith("/apply") or text.startswith("@bot apply"):
        return "apply"
    return None


def relay_comment_actions(owner: str, repo: str, pr_number: int, comments: List[Dict[str, Any]]) -> None:
    """Relay actionable comments to approval worker for processing."""
    try:
        from backend.approval_worker import handle_comment_action
    except Exception:
        return

    for c in comments:
        action = parse_comment_action(c.get("body", ""))
        if action == "apply":
            handle_comment_action(owner, repo, pr_number, c)


def suggest_replies_for_pr(owner: str, repo: str, pr_number: int, mgr: Optional[GitHubManager] = None) -> Dict[str, Any]:
    """Fetch PR context, relay actions and produce auto-replies."""
    ctx = fetch_pr_context(owner, repo, pr_number, mgr)
    pr = ctx.get("pr", {})
    files = ctx.get("files", [])
    comments_raw = ctx.get("comments", [])
    comments = comments_raw if isinstance(comments_raw, list) else comments_raw.get("comments", [])
    relay_comment_actions(owner, repo, pr_number, comments)
    return suggest_replies_and_patch(pr.get("title", ""), pr.get("body", ""), files, comments)
