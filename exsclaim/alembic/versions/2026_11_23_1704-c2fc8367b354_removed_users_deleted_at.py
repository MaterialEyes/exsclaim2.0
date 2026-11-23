"""Removed users.deleted_at.

Revision ID: c2fc8367b354
Revises: 581ca3d69c77
Create Date: 2026-11-23 17:04:46.738995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2fc8367b354'
down_revision: Union[str, Sequence[str], None] = '581ca3d69c77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("DROP VIEW IF EXISTS users.active_users;")
    op.drop_column("users", "deleted_at", schema="users")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "deleted_at",
            sa.types.DateTime(timezone=True),
            nullable=True,
            default=None
        ),
        schema="users",
    )
    op.execute("CREATE VIEW users.active_users AS SELECT * FROM users.users WHERE deleted_at IS NULL;")
