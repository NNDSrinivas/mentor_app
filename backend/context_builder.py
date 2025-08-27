from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any, Dict, List


@dataclass
class Document:
    """Simple representation of a stored document."""

    text: str
    doc_type: str
    created_at: datetime
    metadata: Dict[str, Any]
    score: float = 1.0


def count_tokens(text: str) -> int:
    """Very small token estimator used for budgeting."""

    return len(text.split())


class ContextBuilder:
    """Aggregates user context from a vector store with prioritisation.

    The builder fetches documents for the user from a Chroma-like client and
    orders them by document type priority and recency.  A token budget is
    enforced so that lower priority documents are truncated first.
    """

    PRIORITY = {"jira": 3, "meeting": 2, "repo": 1}

    def __init__(self, chroma_client, token_budget: int = 8000, top_k: int = 5, decay: float = 0.01) -> None:
        self.chroma = chroma_client
        self.token_budget = token_budget
        self.top_k = top_k
        self.decay = decay

    def _retrieve(self, user_id: str, doc_type: str) -> List[Document]:
        results = self.chroma.query(user_id=user_id, doc_type=doc_type, top_k=self.top_k)
        docs: List[Document] = []
        for r in results:
            docs.append(
                Document(
                    text=r["text"],
                    doc_type=doc_type,
                    created_at=r["created_at"],
                    metadata=r.get("metadata", {}),
                    score=r.get("score", 1.0),
                )
            )
        return docs

    def build(self, user_id: str) -> Dict[str, Any]:
        profile_docs = self._retrieve(user_id, "profile")
        profile = profile_docs[0] if profile_docs else None

        docs: List[Document] = []
        for doc_type in ("jira", "meeting", "repo"):
            docs.extend(self._retrieve(user_id, doc_type))

        now = datetime.utcnow()
        for d in docs:
            age_days = (now - d.created_at).total_seconds() / (3600 * 24)
            d.score = d.score * math.exp(-self.decay * age_days)

        docs.sort(key=lambda d: (self.PRIORITY[d.doc_type], d.score), reverse=True)

        context: Dict[str, Any] = {
            "profile": profile.text if profile else "",
            "level": profile.metadata.get("level") if profile else "",
            "jira": [],
            "meetings": [],
            "repo": [],
            "ordered": [],
        }

        total_tokens = count_tokens(context["profile"])

        for d in docs:
            tokens = count_tokens(d.text)
            if total_tokens + tokens > self.token_budget:
                continue
            total_tokens += tokens
            if d.doc_type == "jira":
                context["jira"].append(d.text)
            elif d.doc_type == "meeting":
                context["meetings"].append(d.text)
            else:
                context["repo"].append(d.text)
            context["ordered"].append((d.doc_type, d.text))

        context["token_count"] = total_tokens
        return context
