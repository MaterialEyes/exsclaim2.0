"""Add DOI column to the articles table.

Revision ID: 289193e21c9c
Revises: 3924f9a632d1
Create Date: 2026-10-02 15:26:27.172763

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '289193e21c9c'
down_revision: Union[str, Sequence[str], None] = '3924f9a632d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('sessions', schema='users', if_exists=True)
    with op.batch_alter_table('article', schema='results') as batch_op:
        batch_op.add_column(sa.Column('doi', sa.TEXT(), nullable=True))
        batch_op.create_unique_constraint("article_doi_key", ['doi'])
        batch_op.create_unique_constraint("article_url_key", ['url'])

    with op.batch_alter_table('figure', schema='results') as batch_op:
        batch_op.drop_column('caption_input_tokens')
        batch_op.drop_column('caption_output_tokens')


def downgrade() -> None:
    with op.batch_alter_table('figure', schema='results') as batch_op:
        batch_op.add_column(sa.Column('caption_output_tokens', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('caption_input_tokens', sa.INTEGER(), autoincrement=False, nullable=True))

    with op.batch_alter_table('article', schema='results') as batch_op:
        batch_op.drop_constraint("article_url_key", type_='unique')
        batch_op.drop_constraint("article_doi_key", type_='unique')
        batch_op.drop_column('doi')