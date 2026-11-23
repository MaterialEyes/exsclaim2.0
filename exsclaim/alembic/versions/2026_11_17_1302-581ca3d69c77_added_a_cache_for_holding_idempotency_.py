"""Added a cache for holding idempotency keys for query requests.

Revision ID: 581ca3d69c77
Revises: 58f3da095550
Create Date: 2026-11-17 13:02:28.583900

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '581ca3d69c77'
down_revision: Union[str, Sequence[str], None] = '58f3da095550'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('query_cache',
        sa.Column("run_id", postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("created_at", sa.sql.sqltypes.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
        prefixes=["UNLOGGED"],
        schema='results'
    )

    op.execute("""
       CREATE OR REPLACE PROCEDURE results.expire_query_cache() AS $$
       BEGIN
           DELETE FROM results.query_cache WHERE created_at > (NOW() + INTERVAL '4 hours');
       END;
       $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP PROCEDURE IF EXISTS query_cache")
    op.drop_table("query_cache", schema="results")
