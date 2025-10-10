"""create jira integration tables

Revision ID: 20240501000001
Revises: 20240223000000
Create Date: 2024-05-01 00:00:01.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20240501000001"
down_revision = "20240223000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    text_array = postgresql.ARRAY(sa.Text()).with_variant(sa.JSON(), "sqlite")
    uuid_type = postgresql.UUID(as_uuid=True).with_variant(sa.String(length=36), "sqlite")

    op.create_table(
        "jira_connection",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("org_id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("cloud_base_url", sa.Text(), nullable=False),
        sa.Column("client_id", sa.Text(), nullable=False),
        sa.Column("token_type", sa.Text(), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", text_array, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "jira_project_config",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("org_id", uuid_type, nullable=False),
        sa.Column("connection_id", uuid_type, sa.ForeignKey("jira_connection.id"), nullable=False),
        sa.Column("project_keys", text_array, nullable=False),
        sa.Column("board_ids", text_array, nullable=True),
        sa.Column("default_jql", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "jira_issue",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("connection_id", uuid_type, sa.ForeignKey("jira_connection.id"), nullable=False),
        sa.Column("project_key", sa.Text(), nullable=False),
        sa.Column("issue_key", sa.Text(), unique=True, nullable=False),
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
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("jira_issue")
    op.drop_table("jira_project_config")
    op.drop_table("jira_connection")

