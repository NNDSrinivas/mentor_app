from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20240315000000"
down_revision = "20240223000000"
branch_labels = None
depends_on = None


def _jsonb_type():
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    return jsonb.with_variant(sa.JSON(), "sqlite")


def _text_array():
    array = postgresql.ARRAY(sa.Text())
    return array.with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    jsonb = _jsonb_type()
    text_array = _text_array()

    op.create_table(
        "jira_connection",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cloud_base_url", sa.Text(), nullable=False),
        sa.Column("client_id", sa.Text(), nullable=False),
        sa.Column("token_type", sa.Text(), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", text_array, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "jira_project_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jira_connection.id"), nullable=False),
        sa.Column("project_keys", text_array, nullable=False),
        sa.Column("board_ids", text_array, nullable=True),
        sa.Column("default_jql", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "jira_issue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jira_connection.id"), nullable=False),
        sa.Column("project_key", sa.Text(), nullable=False),
        sa.Column("issue_key", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("priority", sa.Text(), nullable=True),
        sa.Column("assignee", sa.Text(), nullable=True),
        sa.Column("reporter", sa.Text(), nullable=True),
        sa.Column("labels", text_array, nullable=True),
        sa.Column("epic_key", sa.Text(), nullable=True),
        sa.Column("sprint", sa.Text(), nullable=True),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("raw", jsonb, nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("connection_id", "issue_key", name="uq_jira_issue_connection_issue"),
    )


def downgrade() -> None:
    op.drop_table("jira_issue")
    op.drop_table("jira_project_config")
    op.drop_table("jira_connection")
