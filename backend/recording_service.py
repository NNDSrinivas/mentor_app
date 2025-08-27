"""Recording service for streaming capture chunks, encryption, and metadata persistence.

This service is responsible for receiving streaming chunks from the capture
modules (``app.screen_record`` or ``app.capture``), encrypting each chunk
before storing it on disk, and persisting metadata about the recording to the
``production_realtime.db`` database.

The implementation uses symmetric encryption with ``cryptography.Fernet``. If
``cryptography`` is not available, a no-op cipher is used so that the service
still functions (unencrypted) in development environments.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Iterable, Optional, Dict

try:  # pragma: no cover - fallback if cryptography is unavailable
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover - library optional
    class Fernet:  # type: ignore
        def __init__(self, key: bytes):
            self.key = key
        def encrypt(self, data: bytes) -> bytes:
            return data

import logging

log = logging.getLogger(__name__)


class RecordingService:
    """Service for streaming and storing encrypted recording chunks."""

    def __init__(self,
                 db_path: str = "production_realtime.db",
                 storage_dir: str = "data/recordings",
                 encryption_key: Optional[bytes] = None) -> None:
        self.db_path = db_path
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

        key = encryption_key or os.getenv("ENCRYPTION_KEY")
        if key is None:
            key = Fernet.generate_key() if hasattr(Fernet, "generate_key") else b"noop"
            log.warning("ENCRYPTION_KEY not set; using ephemeral key")
        self.cipher = Fernet(key if isinstance(key, bytes) else key.encode())

        self._init_db()

    # ------------------------------------------------------------------
    # Database helpers
    def _init_db(self) -> None:
        """Ensure the recordings table exists."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def _persist_metadata(self, session_id: str, filename: str, chunk_index: int,
                           metadata: Optional[Dict] = None) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO recordings (session_id, filename, chunk_index, metadata) VALUES (?, ?, ?, ?)",
            (session_id, filename, chunk_index, None if metadata is None else str(metadata)),
        )
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Chunk handling
    def save_chunk(self, session_id: str, chunk: bytes, chunk_index: int,
                   metadata: Optional[Dict] = None) -> tuple[str, bool]:
        """Encrypt and store a single chunk.

        Returns a tuple ``(path, stored)`` where ``stored`` indicates whether the
        chunk was newly written. If the chunk already exists, ``stored`` is
        ``False`` and the file on disk is left untouched.
        """
        filename = f"{session_id}_{chunk_index:06d}.enc"
        path = os.path.join(self.storage_dir, filename)
        if os.path.exists(path):
            log.debug("Chunk %s already exists, skipping write", filename)
            return path, False

        encrypted = self.cipher.encrypt(chunk)
        with open(path, "wb") as f:
            f.write(encrypted)
        self._persist_metadata(session_id, filename, chunk_index, metadata)
        return path, True

    def stream(self, session_id: str, chunks: Iterable[bytes]) -> None:
        """Stream an iterable of chunks and store them sequentially.

        The ``chunks`` iterable can be produced by ``app.capture`` or
        ``app.screen_record`` modules which yield raw byte strings. Each chunk
        is encrypted and saved to disk.
        """
        for index, chunk in enumerate(chunks):
            try:
                self.save_chunk(session_id, chunk, index)
            except Exception as exc:  # pragma: no cover - logging only
                log.error("Failed to store chunk %s: %s", index, exc)
                break
