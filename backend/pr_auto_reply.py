# backend/pr_auto_reply.py
from __future__ import annotations
import os
from typing import Dict, Any, List
from openai import OpenAI

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
    data = resp.choices[0].message.content
    # let the server validate JSON before acting
    return {"raw": data}
