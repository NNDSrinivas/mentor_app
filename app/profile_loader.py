from __future__ import annotations
import json, os
from typing import Dict, Any, Optional

def load_profile(path: Optional[str] = None) -> Dict[str, Any]:
    """Load the user's parsed profile/resume JSON."""
    candidates = [path] if path else [
        os.getenv("PROFILE_JSON"),
        "data/profile.json",
        "profile.json",
        "app/data/profile.json",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    return {
        "personal": {"currentRole": "Senior Software Engineer", "currentCompany": "Acme Corp"},
        "experience": {"keyProjects": "", "achievements": ""}
    }
