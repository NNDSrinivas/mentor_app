from __future__ import annotations
from typing import Dict, Any

IC_LEVEL_GUIDANCE = {
    "IC4": "mid-senior individual contributor; clear code, pragmatic trade-offs, solid testing, basic reliability concerns",
    "IC5": "senior engineer; deep design, scalability, reliability, cost, observability, oncall readiness",
    "IC6": "staff engineer; cross-team architecture, multi-service trade-offs, migrations, multi-region, SLO/error budgets",
    "IC7": "principal; org-wide impact, long-term architecture strategy, platform thinking, compliance/security at scale",
    "E5": "senior SWE; Meta-style system design and coding rigor; data structures, APIs, perf, product sense",
    "E6": "staff SWE; Meta-scale systems, incident prevention, cross-org influence, production excellence",
    "E7": "principal SWE; long-range technical vision, complex org execution, privacy/security/regulatory constraints"
}

def build_answer_prompt(transcript: str, profile: Dict[str, Any], ic_level: str, context_snippets: str) -> str:
    level = IC_LEVEL_GUIDANCE.get(ic_level, IC_LEVEL_GUIDANCE['IC5'])
    exp = profile.get('personal', {}).get('currentRole', '') + ' at ' + profile.get('personal', {}).get('currentCompany','')
    projects = profile.get('experience', {}).get('keyProjects', '')
    ach = profile.get('experience', {}).get('achievements', '')

    return f"""You are a {level} answering LIVE during a meeting. 
Use STAR where appropriate. Be concise, senior, and hands-on. Ground answers in the user's real experience.

User context:
- Role/company: {exp}
- Projects: {projects}
- Achievements: {ach}

Meeting question (complete): {transcript}

Helpful context from code/docs/tickets:
{context_snippets}

Output as a short, bullet-first answer the user can read aloud. 
Include one optional follow-up question the user can ask. 
Avoid revealing you are an AI. 
"""
