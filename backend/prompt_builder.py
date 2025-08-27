from __future__ import annotations

from typing import Any, Dict, List

from .context_builder import count_tokens


class PromptBuilder:
    """Constructs an LLM prompt using a consistent senior voice."""

    def __init__(self, max_tokens: int = 8000) -> None:
        self.max_tokens = max_tokens

    def _render(self, question: str, context: Dict[str, Any]) -> str:
        voice = f"You are an experienced {context.get('level', 'IC6')} engineer."
        lines: List[str] = [voice, "", "What we know:"]
        if context.get("profile"):
            lines.append(f"- Resume: {context['profile']}")
        if context.get("jira"):
            lines.append(f"- Jira: {' '.join(context['jira'])}")
        if context.get("meetings"):
            lines.append(f"- Meetings: {' '.join(context['meetings'])}")
        if context.get("repo"):
            lines.append(f"- Repo: {' '.join(context['repo'])}")
        lines.extend(["", f"Question: {question}"])
        return "\n".join(lines)

    def build(self, question: str, context: Dict[str, Any]) -> str:
        prompt = self._render(question, context)
        tokens = count_tokens(prompt)
        if tokens <= self.max_tokens:
            return prompt

        # Truncate lower priority sections if we exceed the budget.  We mutate
        # the context lists and re-render until within the limit.
        priority_order = ["repo", "meetings", "jira"]
        while tokens > self.max_tokens:
            for key in priority_order:
                if context.get(key):
                    context[key] = context[key][:-1]
                    break
            prompt = self._render(question, context)
            tokens = count_tokens(prompt)
        return prompt
