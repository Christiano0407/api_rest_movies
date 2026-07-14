"""
  # === Migrations === #
  Revision ID: 0001_initial_schema
  Revises:
  Create Date: 2026-07-01
  Architecture: FastAPI + SQLAlchemy + Alembic + PostgreSQL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

role_enum = sa.Enum(
    "Admin", "Manager", "Editor", "Moderator", "Premium", "User", name="role_enum"
)


def upgrade() -> None:
    role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=30), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", role_enum, nullable=False, server_default="User"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "tmdb_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("tmdb_account_id", sa.String(length=64), nullable=False),
        sa.Column("tmdb_session_id", sa.String(length=128), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "token_blocklist",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("exp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_token_blocklist_jti", "token_blocklist", ["jti"], unique=True)
    # Acelera el job de limpieza periódica de tokens ya expirados.
    op.create_index("ix_token_blocklist_exp", "token_blocklist", ["exp"])


def downgrade() -> None:
    op.drop_table("token_blocklist")
    op.drop_table("tmdb_sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    role_enum.drop(op.get_bind(), checkfirst=True)