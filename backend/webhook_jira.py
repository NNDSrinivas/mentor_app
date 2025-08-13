# webhook_jira.py
from __future__ import annotations
from typing import Dict, Any
from backend.memory_service import MemoryService

mem = MemoryService()

def handle_jira_webhook(payload: Dict[str, Any]):
    """Handle Jira webhook events and mirror into memory service"""
    issue = payload.get("issue", {})
    key = issue.get("key")
    fields = issue.get("fields", {})
    status = (fields.get("status") or {}).get("name", "")
    summary = fields.get("summary","")
    assignee = (fields.get("assignee") or {}).get("displayName","")
    project = (fields.get("project") or {}).get("key","")
    event_type = payload.get("webhookEvent", "")

    if not key:
        return

    # mirror into memory
    text = f"[{key}] {summary} — status: {status} — assignee: {assignee}"
    
    metadata = {
        "project": project, 
        "status": status, 
        "assignee": assignee,
        "event_type": event_type,
        "jira_key": key,
        "last_updated": payload.get("timestamp", "")
    }
    
    # Add or update task in memory
    mem.add_task(key, text, metadata=metadata)
