from __future__ import annotations
import hmac, hashlib, os

GITHUB_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
JIRA_SECRET = os.getenv("JIRA_WEBHOOK_SECRET", "")

def verify_github(signature_header: str, body: bytes) -> bool:
    # GitHub: X-Hub-Signature-256: sha256=...
    if not GITHUB_SECRET or not signature_header or not signature_header.startswith("sha256="):
        return False
    their_sig = signature_header.split("=",1)[1]
    mac = hmac.new(GITHUB_SECRET.encode(), msg=body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), their_sig)

def verify_jira(signature_header: str, body: bytes) -> bool:
    # If using a shared secret header (e.g., X-Shared-Secret)
    secret = JIRA_SECRET
    if not secret or not signature_header:
        return False
    mac = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256)
    their_sig = signature_header.strip()
    return hmac.compare_digest(mac.hexdigest(), their_sig)
