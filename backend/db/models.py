from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.types import JSON, TypeDecorator

from .base import Base

class GUID(TypeDecorator):
    impl = UUID
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value if dialect.name == "postgresql" else str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


UUID_TYPE = GUID()


def _jsonb_column(name: str):
    jsonb_type = JSONB(astext_type=Text()).with_variant(JSON(), "sqlite")
    return Column(name, jsonb_type)


def _text_array_column(name: str, nullable: bool = True):
    array_type = ARRAY(Text()).with_variant(JSON(), "sqlite")
    return Column(name, array_type, nullable=nullable)


class Meeting(Base):
    __tablename__ = "meeting"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID_TYPE, unique=True, nullable=False)
    title = Column(Text)
    provider = Column(String(100))
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    participants = _jsonb_column("participants")
    org_id = Column(UUID_TYPE, nullable=True)


class TranscriptSegment(Base):
    __tablename__ = "transcript_segment"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID_TYPE, ForeignKey("meeting.id"), nullable=False)
    ts_start_ms = Column(Integer, nullable=False)
    ts_end_ms = Column(Integer, nullable=False)
    speaker = Column(String(255))
    text = Column(Text, nullable=False)


class MeetingSummary(Base):
    __tablename__ = "meeting_summary"

    meeting_id = Column(UUID_TYPE, ForeignKey("meeting.id"), primary_key=True)
    bullets = _jsonb_column("bullets")
    decisions = _jsonb_column("decisions")
    risks = _jsonb_column("risks")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ActionItem(Base):
    __tablename__ = "action_item"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID_TYPE, ForeignKey("meeting.id"), nullable=False)
    title = Column(Text, nullable=False)
    assignee = Column(String(255))
    due_hint = Column(String(255))
    confidence = Column(Numeric)
    source_segment = Column(UUID_TYPE, ForeignKey("transcript_segment.id"), nullable=True)


class JiraConnection(Base):
    __tablename__ = "jira_connection"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID_TYPE, nullable=False)
    user_id = Column(UUID_TYPE, nullable=False)
    cloud_base_url = Column(Text, nullable=False)
    client_id = Column(Text, nullable=False)
    token_type = Column(Text, nullable=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = _text_array_column("scopes", nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class JiraProjectConfig(Base):
    __tablename__ = "jira_project_config"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID_TYPE, nullable=False)
    connection_id = Column(UUID_TYPE, ForeignKey("jira_connection.id"), nullable=False)
    project_keys = _text_array_column("project_keys", nullable=False)
    board_ids = _text_array_column("board_ids", nullable=True)
    default_jql = Column(Text, nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)


class JiraIssue(Base):
    __tablename__ = "jira_issue"
    __table_args__ = (UniqueConstraint("connection_id", "issue_key", name="uq_jira_issue_connection_issue"),)

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID_TYPE, ForeignKey("jira_connection.id"), nullable=False)
    project_key = Column(Text, nullable=False)
    issue_key = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(Text, nullable=True)
    priority = Column(Text, nullable=True)
    assignee = Column(Text, nullable=True)
    reporter = Column(Text, nullable=True)
    labels = _text_array_column("labels", nullable=True)
    epic_key = Column(Text, nullable=True)
    sprint = Column(Text, nullable=True)
    updated = Column(DateTime(timezone=True), nullable=True)
    url = Column(Text, nullable=True)
    raw = _jsonb_column("raw")
    indexed_at = Column(DateTime(timezone=True), nullable=True)
