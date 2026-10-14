"""Switch email to username for local auth

Revision ID: 0003_username_auth
Revises: 0002_password_auth
Create Date: 2026-06-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_username_auth"
down_revision = "0002_password_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing index and unique constraint
    op.drop_index("ix_users_email", table_name="users")
    op.drop_constraint("uq_users_email", table_name="users", type_="unique")

    # Rename column email to username
    op.alter_column("users", "email", new_column_name="username")

    # Create new unique constraint and index
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_index("ix_users_username", "users", ["username"])


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_constraint("uq_users_username", table_name="users", type_="unique")

    op.alter_column("users", "username", new_column_name="email")

    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])
