"""Added column to users recording when they request to delete their account.

Revision ID: 58f3da095550
Revises: 289193e21c9c
Create Date: 2026-10-16 17:25:13.645996

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '58f3da095550'
down_revision: Union[str, Sequence[str], None] = '289193e21c9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
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


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP VIEW IF EXISTS users.active_users;")
    op.drop_column("users", "deleted_at", schema="users")
