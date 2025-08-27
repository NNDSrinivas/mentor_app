import hmac
import hashlib
import os
import sys

sys.path.append(os.getcwd())


def test_verify_github_signature():
    import backend.webhook_signatures as sig

    sig.GITHUB_SECRET = "secret"
    sig.JIRA_SECRET = "secret"
    body = b"{}"
    good_sig = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    assert sig.verify_github(good_sig, body)
    assert not sig.verify_github("sha256=bad", body)
