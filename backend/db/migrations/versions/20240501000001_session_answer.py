"""add session answer table

Revision ID: 20240501000001
Revises: 20240223000000
Create Date: 2024-05-01 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20240501000001"
down_revision = "20240223000000"
branch_labels = None
depends_on = None


def _jsonb_type():
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    return jsonb.with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    jsonb = _jsonb_type()

    op.create_table(
        "session_answer",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("citations", jsonb, nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_session_answer_session_created",
        "session_answer",
        ["session_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_session_answer_session_created", table_name="session_answer")
    op.drop_table("session_answer")
