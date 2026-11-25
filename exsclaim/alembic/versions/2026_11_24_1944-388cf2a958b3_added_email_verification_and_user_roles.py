"""Added email verification and user roles.

Revision ID: 388cf2a958b3
Revises: c2fc8367b354
Create Date: 2026-11-24 19:44:49.020101

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '388cf2a958b3'
down_revision: Union[str, Sequence[str], None] = 'c2fc8367b354'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('email_verification',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('code_hash', sa.TEXT(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.users.id'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('code_hash'),
        sa.UniqueConstraint('user_id'),
        schema='users'
    )
    with op.batch_alter_table('users', schema='users') as batch_op:
        batch_op.add_column(
            sa.Column('roles', sa.INTEGER, server_default=sa.text('1'), nullable=False)
        )
        batch_op.add_column(
            sa.Column('email_verified', sa.Boolean, nullable=True)
        )
        batch_op.create_check_constraint(
            "check_user_email_verified",
            "(email IS NULL AND email_verified IS NULL) OR (email IS NOT NULL AND email_verified IS NOT NULL)"
        )

    op.execute("UPDATE users.users SET email_verified = FALSE WHERE email IS NOT NULL;")
    op.execute("UPDATE users.users SET email_verified = NULL WHERE email IS NULL;")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema='users') as batch_op:
        batch_op.drop_constraint('check_user_email_verified', type_='check')
        batch_op.drop_column('email_verified')
        batch_op.drop_column('roles')

    op.drop_table('email_verification', schema='users')
