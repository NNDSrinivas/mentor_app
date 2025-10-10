from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import JSON

from .base import Base


def _jsonb_column(name: str):
    jsonb_type = JSONB(astext_type=Text()).with_variant(JSON(), "sqlite")
    return Column(name, jsonb_type)


class Meeting(Base):
    __tablename__ = "meeting"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), unique=True, nullable=False)
    title = Column(Text)
    provider = Column(String(100))
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    participants = _jsonb_column("participants")
    org_id = Column(UUID(as_uuid=True), nullable=True)


class TranscriptSegment(Base):
    __tablename__ = "transcript_segment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meeting.id"), nullable=False)
    ts_start_ms = Column(Integer, nullable=False)
    ts_end_ms = Column(Integer, nullable=False)
    speaker = Column(String(255))
    text = Column(Text, nullable=False)


class MeetingSummary(Base):
    __tablename__ = "meeting_summary"

    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meeting.id"), primary_key=True)
    bullets = _jsonb_column("bullets")
    decisions = _jsonb_column("decisions")
    risks = _jsonb_column("risks")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ActionItem(Base):
    __tablename__ = "action_item"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meeting.id"), nullable=False)
    title = Column(Text, nullable=False)
    assignee = Column(String(255))
    due_hint = Column(String(255))
    confidence = Column(Numeric)
    source_segment = Column(UUID(as_uuid=True), ForeignKey("transcript_segment.id"), nullable=True)


class GHConnection(Base):
    __tablename__ = "gh_connection"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    installation_id = Column(String(255))
    account_login = Column(String(255))
    account_id = Column(String(255))
    encrypted_access_token = Column(Text)
    encrypted_refresh_token = Column(Text)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(Text)
    mock = Column(Boolean, default=False)


class GHRepo(Base):
    __tablename__ = "gh_repo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(
        UUID(as_uuid=True), ForeignKey("gh_connection.id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    full_name = Column(String(512), nullable=False, unique=True)
    default_branch = Column(String(255), nullable=True)
    private = Column(Boolean, default=False)
    url = Column(Text)
    head_sha = Column(String(255))
    last_index_at = Column(DateTime(timezone=True), nullable=True)
    languages = _jsonb_column("languages")
    top_paths = _jsonb_column("top_paths")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class GHFile(Base):
    __tablename__ = "gh_file"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("gh_repo.id"), nullable=False)
    path = Column(Text, nullable=False)
    sha = Column(String(255))
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    snippet = Column(Text, nullable=False)
    embedding_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class GHIssuePR(Base):
    __tablename__ = "gh_issue_pr"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("gh_repo.id"), nullable=False)
    number = Column(Integer, nullable=False)
    type = Column(String(16), nullable=False)
    title = Column(Text, nullable=False)
    state = Column(String(50))
    updated_at = Column(DateTime(timezone=True), nullable=True)
    url = Column(Text)
    snippet = Column(Text)
    embedding_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    ingested_at = Column(DateTime(timezone=True), default=datetime.utcnow)

