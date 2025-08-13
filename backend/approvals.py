# backend/approvals.py
from __future__ import annotations
import time, threading, queue
from typing import Dict, Any, Optional

from backend.integrations.github_manager import GitHubManager
from backend.integrations.jira_manager import JiraManager
from backend.pr_auto_reply import suggest_replies_and_patch

class ApprovalItem:
    def __init__(self, action: str, payload: Dict[str, Any]):
        self.id = f"{action}-{int(time.time()*1000)}"
        self.action = action
        self.payload = payload
        self.created_at = time.time()
        self.status = "pending"  # pending|approved|rejected
        self.result: Optional[Dict[str, Any]] = None

class ApprovalsQueue:
    def __init__(self, maxsize=200):
        self.q: "queue.Queue[ApprovalItem]" = queue.Queue(maxsize=maxsize)
        self._items: Dict[str, ApprovalItem] = {}
        self._lock = threading.Lock()

    def submit(self, action: str, payload: Dict[str, Any]) -> ApprovalItem:
        item = ApprovalItem(action, payload)
        with self._lock:
            self._items[item.id] = item
        self.q.put(item)
        return item

    def list(self):
        with self._lock:
            return [vars(x) for x in self._items.values() if x.status == "pending"]

    def get(self, item_id: str) -> Optional[ApprovalItem]:
        with self._lock:
            return self._items.get(item_id)

    def resolve(self, item_id: str, decision: str, result: Optional[Dict[str, Any]]=None):
        with self._lock:
            item = self._items[item_id]
            item.status = "approved" if decision == "approve" else "rejected"
            item.result = result or {}
        return vars(item)

approvals = ApprovalsQueue()

# Expose integration managers for convenience across the backend
github = GitHubManager(dry_run=True)
jira = JiraManager(dry_run=True)

def request_pr_auto_reply(owner: str, repo: str, pr_number: int, jira_issue: Optional[str] = None):
    """Generate auto-reply suggestions for a PR and enqueue for approval.

    If a Jira issue key is provided, a comment is added noting that suggestions
    were generated for the related pull request.
    """
    pr = github.get_pr(owner, repo, pr_number)
    files = github.get_pr_files(owner, repo, pr_number)
    comments = github.get_pr_comments(owner, repo, pr_number)
    suggestions = suggest_replies_and_patch(
        pr.get("title", ""),
        pr.get("body", "") or "",
        files,
        comments,
    )

    item = approvals.submit(
        "github.pr_auto_reply",
        {
            "owner": owner,
            "repo": repo,
            "pr_number": pr_number,
            "suggestions_json": suggestions["raw"],
        },
    )

    if jira_issue:
        jira.add_comment(jira_issue, f"Auto-reply suggestions queued for PR #{pr_number}")

    return item

def sync_jira_pr_status(owner: str, repo: str, pr_number: int, jira_issue: str):
    """Update Jira issue based on the current status of a pull request."""
    pr = github.get_pr(owner, repo, pr_number)
    state = pr.get("state")
    merged = bool(pr.get("merged_at"))

    if merged:
        jira.add_comment(jira_issue, f"PR #{pr_number} was merged")
    else:
        jira.add_comment(jira_issue, f"PR #{pr_number} state: {state}")

    return {"state": state, "merged": merged}
