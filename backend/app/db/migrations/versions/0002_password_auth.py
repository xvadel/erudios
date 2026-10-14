"""Switch users from OAuth to password auth

Revision ID: 0002_password_auth
Revises: 0001_initial
Create Date: 2026-06-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_password_auth"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password_hash column (nullable so existing rows are unaffected)
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))

    # Drop the OAuth columns — they're no longer needed
    op.drop_column("users", "oauth_provider")
    op.drop_column("users", "oauth_id")


def downgrade() -> None:
    op.add_column("users", sa.Column("oauth_provider", sa.String(50), nullable=True, server_default="github"))
    op.add_column("users", sa.Column("oauth_id", sa.String(255), nullable=True, server_default=""))
    op.drop_column("users", "password_hash")
