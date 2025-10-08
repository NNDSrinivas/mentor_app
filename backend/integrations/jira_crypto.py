from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover - optional dependency fallback
    Fernet = None  # type: ignore


class JiraTokenCipher:
    """Encrypt and decrypt Jira OAuth tokens using Fernet when available."""

    def __init__(self, key: Optional[str] = None) -> None:
        provided = key or os.getenv("JIRA_ENCRYPTION_KEY") or os.getenv("ENCRYPTION_KEY")
        self._fernet = self._build_fernet(provided)

    @staticmethod
    def _build_fernet(key: Optional[str]) -> Optional[Fernet]:
        if not key or Fernet is None:
            return None
        key_bytes = key.encode()
        if len(key_bytes) == 44 and key.endswith("="):
            candidate = key_bytes
        else:
            digest = hashlib.sha256(key_bytes).digest()
            candidate = base64.urlsafe_b64encode(digest)
        try:
            return Fernet(candidate)
        except (ValueError, TypeError):  # pragma: no cover - invalid key fallback
            return None

    def encrypt(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if self._fernet is None:
            return value
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if self._fernet is None:
            return value
        return self._fernet.decrypt(value.encode()).decode()


__all__ = ["JiraTokenCipher"]
