# backend/approvals.py
from __future__ import annotations
import time, threading, queue
from typing import Dict, Any, Optional

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
