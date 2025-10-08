"""add cloud id to jira connection

Revision ID: 20240501000002
Revises: 20240501000001
Create Date: 2024-05-01 00:00:02.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240501000002"
down_revision = "20240501000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jira_connection", sa.Column("cloud_id", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("jira_connection", "cloud_id")
