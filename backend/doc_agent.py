# backend/doc_agent.py
from __future__ import annotations
import os
from typing import Dict, Any, List
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set")

client = OpenAI(api_key=api_key)

ADR_SYSTEM = (
  "You generate engineering docs (ADR, runbook, changelog) from context. "
  "Be precise, terse, and follow conventional sections."
)

def draft_adr(title: str, context: str, options: List[str], decision: str, consequences: List[str]) -> str:
    msg = f"""
Title: {title}
Context: {context}
Options: {options}
Decision: {decision}
Consequences: {consequences}

Return a Markdown ADR with sections: Title, Status, Context, Decision, Consequences, References.
"""
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
        messages=[{"role":"system","content":ADR_SYSTEM},{"role":"user","content":msg}],
        temperature=0.2,
        max_tokens=800
    )
    content = resp.choices[0].message.content or ""
    return content.strip()

def draft_runbook(service: str, incidents: List[str], commands: List[str], dashboards: List[str]) -> str:
    msg = f"""
Service: {service}
Incidents: {incidents}
Commands: {commands}
Dashboards: {dashboards}

Return a Markdown runbook with sections: Overview, Symptoms, Diagnosis, Mitigation, Rollback, Command Reference, Dashboards.
"""
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
        messages=[{"role":"system","content":ADR_SYSTEM},{"role":"user","content":msg}],
        temperature=0.2,
        max_tokens=900
    )
    content = resp.choices[0].message.content or ""
    return content.strip()

def draft_changelog(repo: str, merged_prs: List[Dict[str,Any]]) -> str:
    lines = [f"- {pr.get('title','')} (#{pr.get('number')}) by {pr.get('user',{}).get('login','')}" for pr in merged_prs]
    msg = "Repo: " + repo + "\nMerged PRs:\n" + "\n".join(lines)
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
        messages=[{"role":"system","content":ADR_SYSTEM},{"role":"user","content":msg}],
        temperature=0.3,
        max_tokens=600
    )
    content = resp.choices[0].message.content or ""
    return content.strip()
