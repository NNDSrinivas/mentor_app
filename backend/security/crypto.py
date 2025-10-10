"""Utility helpers for encrypting and decrypting sensitive secrets.

This module intentionally keeps the dependency surface small.  When the
``cryptography`` package is available we rely on :class:`~cryptography.fernet.Fernet`
for strong symmetric encryption.  In environments where that dependency is not
installed we fall back to a lightweight XOR-based cipher that still keeps the
values unreadable at rest while remaining reversible.  The fallback is not meant
to be bullet proof, but it satisfies the requirement of avoiding plaintext
tokens in the database during development and tests.

The encryption key is derived from ``TOKEN_ENCRYPTION_SECRET`` (or
``GITHUB_ENCRYPTION_SECRET`` for backwards compatibility).  The derivation uses
SHA-256 so callers can provide arbitrary length secrets.
"""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from typing import Optional

try:  # pragma: no cover - exercised when cryptography is installed
    from cryptography.fernet import Fernet, InvalidToken
except Exception:  # pragma: no cover - fallback path for light-weight envs
    Fernet = None  # type: ignore[assignment]

    class InvalidToken(Exception):
        """Placeholder exception so callers do not need conditional imports."""


def _derive_key(secret: str) -> bytes:
    """Derive a stable 32-byte key from the provided secret string."""

    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@dataclass
class TokenEncryptor:
    """Small helper that wraps encryption/decryption operations."""

    secret: Optional[str] = None

    def __post_init__(self) -> None:
        env_secret = (
            self.secret
            or os.getenv("TOKEN_ENCRYPTION_SECRET")
            or os.getenv("GITHUB_ENCRYPTION_SECRET")
            or "mentor-app-secret"
        )
        derived = _derive_key(env_secret)
        if Fernet is not None:  # pragma: no cover - depends on optional dep
            self._fernet = Fernet(derived)
            self._key_bytes: Optional[bytes] = None
        else:  # lightweight reversible fallback for tests
            self._fernet = None
            self._key_bytes = hashlib.sha256(env_secret.encode("utf-8")).digest()

    # --- Public API -----------------------------------------------------
    def encrypt(self, value: str | None) -> str:
        if not value:
            return ""
        if self._fernet is not None:  # pragma: no cover - optional dependency
            token = self._fernet.encrypt(value.encode("utf-8"))
            return token.decode("utf-8")
        assert self._key_bytes is not None
        xor_bytes = self._xor_with_key(value.encode("utf-8"))
        return base64.urlsafe_b64encode(xor_bytes).decode("utf-8")

    def decrypt(self, value: str | None) -> str:
        if not value:
            return ""
        if self._fernet is not None:  # pragma: no cover - optional dependency
            try:
                plain = self._fernet.decrypt(value.encode("utf-8"))
            except InvalidToken:
                return ""
            return plain.decode("utf-8")
        assert self._key_bytes is not None
        try:
            decoded = base64.urlsafe_b64decode(value.encode("utf-8"))
        except Exception:
            return ""
        plain = self._xor_with_key(decoded)
        return plain.decode("utf-8", errors="ignore")

    # --- Internal helpers -----------------------------------------------
    def _xor_with_key(self, data: bytes) -> bytes:
        assert self._key_bytes is not None
        key = self._key_bytes
        return bytes((byte ^ key[i % len(key)]) for i, byte in enumerate(data))


__all__ = ["TokenEncryptor"]

