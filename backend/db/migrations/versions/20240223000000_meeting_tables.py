from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20240223000000"
down_revision = None
branch_labels = None
depends_on = None


def _jsonb_type():
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    return jsonb.with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    jsonb = _jsonb_type()

    op.create_table(
        "meeting",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("participants", jsonb, nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_table(
        "transcript_segment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meeting.id"), nullable=False),
        sa.Column("ts_start_ms", sa.Integer(), nullable=False),
        sa.Column("ts_end_ms", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
    )

    op.create_table(
        "meeting_summary",
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meeting.id"), primary_key=True, nullable=False),
        sa.Column("bullets", jsonb, nullable=True),
        sa.Column("decisions", jsonb, nullable=True),
        sa.Column("risks", jsonb, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "action_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meeting.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("assignee", sa.String(length=255), nullable=True),
        sa.Column("due_hint", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("source_segment", postgresql.UUID(as_uuid=True), sa.ForeignKey("transcript_segment.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("action_item")
    op.drop_table("meeting_summary")
    op.drop_table("transcript_segment")
    op.drop_table("meeting")
