# webhook_jira.py
from __future__ import annotations
from typing import Dict, Any, Optional
from backend.memory_service import MemoryService

mem = MemoryService()
local_tasks: Dict[str, Dict[str, Any]] = {}

def handle_jira_webhook(payload: Dict[str, Any], mem_service: Optional[MemoryService] = None):
    """Handle Jira webhook events and keep local task state in sync."""
    mem_service = mem_service or mem
    issue = payload.get("issue", {})
    key = issue.get("key")
    fields = issue.get("fields", {})
    status = (fields.get("status") or {}).get("name", "")
    summary = fields.get("summary", "")
    assignee = (fields.get("assignee") or {}).get("displayName", "")
    project = (fields.get("project") or {}).get("key", "")
    event_type = payload.get("webhookEvent", "")

    if not key:
        return

    if event_type == "jira:issue_deleted":
        local_tasks.pop(key, None)
        return

    text = f"[{key}] {summary} — status: {status} — assignee: {assignee}"

    metadata = {
        "project": project,
        "status": status,
        "assignee": assignee,
        "event_type": event_type,
        "jira_key": key,
        "last_updated": payload.get("timestamp", "")
    }

    changelog = payload.get("changelog", {})
    for item in changelog.get("items", []):
        if item.get("field") == "status":
            metadata["prev_status"] = item.get("fromString", "")
            break

    mem_service.add_task(key, text, metadata=metadata)
    local_tasks[key] = {
        "summary": summary,
        "status": status,
        "assignee": assignee,
        "project": project,
    }
    return local_tasks[key]

