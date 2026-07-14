"""
  # === Migrations === #
  users.updated_at + rename role_enum -> user_role, username VARCHAR(30)->(50)

  Revision ID: 0002_users_updated_at
  Revises: 0001_initial_schema
  Create Date: 2026-07-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_users_updated_at"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Alinea el nombre del tipo ENUM con el SQL de referencia (user_role, no role_enum).
    op.execute("ALTER TYPE role_enum RENAME TO user_role")
    op.alter_column("users", "username", type_=sa.String(length=50))


def downgrade() -> None:
    op.alter_column("users", "username", type_=sa.String(length=30))
    op.execute("ALTER TYPE user_role RENAME TO role_enum")
    op.drop_column("users", "updated_at")