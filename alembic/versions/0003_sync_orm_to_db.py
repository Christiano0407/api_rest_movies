"""
  # === Migrations === #
  Sync ORM model to database:
  - users: password_hash -> hashed_password, update_at -> updated_at, add is_verified
  - tmdb_sessions: tmdb_session_id -> session_id, tmdb_account_id -> account_id,
                   add access_token, add expires_at
  - Create token_blocklist table

  Revision ID: 0003_sync_orm_to_db
  Revises: 0002_users_updated_at
  Create Date: 2026-07-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_sync_orm_to_db"
down_revision: Union[str, None] = "0002_users_updated_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === users === #
    op.alter_column("users", "password_hash", new_column_name="hashed_password")
    op.alter_column("users", "update_at", new_column_name="updated_at")
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column(
        "users", "role",
        type_=sa.String(20),
        postgresql_using="role::text",
    )

    # === tmdb_sessions === #
    op.alter_column("tmdb_sessions", "tmdb_session_id", new_column_name="session_id")

    op.add_column(
        "tmdb_sessions",
        sa.Column("account_id", sa.Integer(), nullable=True),
    )
    op.drop_column("tmdb_sessions", "tmdb_account_id")

    op.add_column(
        "tmdb_sessions",
        sa.Column("access_token", sa.String(500), nullable=True),
    )
    op.add_column(
        "tmdb_sessions",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # === token_blocklist === #
    op.create_table(
        "token_blocklist",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("jti", sa.String(length=255), nullable=False),
        sa.Column("token_type", sa.String(length=20), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_token_blocklist_jti", "token_blocklist", ["jti"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_token_blocklist_jti", table_name="token_blocklist")
    op.drop_table("token_blocklist")

    op.drop_column("tmdb_sessions", "expires_at")
    op.drop_column("tmdb_sessions", "access_token")
    op.add_column(
        "tmdb_sessions",
        sa.Column("tmdb_account_id", sa.String(length=100), nullable=False, server_default=""),
    )
    op.drop_column("tmdb_sessions", "account_id")
    op.alter_column("tmdb_sessions", "session_id", new_column_name="tmdb_session_id")

    op.drop_column("users", "is_verified")
    op.alter_column("users", "updated_at", new_column_name="update_at")
    op.alter_column("users", "hashed_password", new_column_name="password_hash")
    op.execute("DROP TYPE IF EXISTS user_role CASCADE")
    op.execute("CREATE TYPE user_role AS ENUM ('Admin', 'Manager', 'Editor', 'Moderator', 'Premium', 'User')")
    op.alter_column(
        "users", "role",
        type_=sa.Enum("Admin", "Manager", "Editor", "Moderator", "Premium", "User", name="user_role"),
        postgresql_using="role::user_role",
    )
