"""Store LLM token info for subfigures.

Revision ID: cb4427d95375
Revises: 751d7ac35cd2
Create Date: 2026-09-17 12:48:04.913445
Original Implementation Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb4427d95375'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""ALTER TABLE results.article
					ADD CONSTRAINT results_article_id
						FOREIGN KEY (run_id)
							REFERENCES results.results(id)
							ON UPDATE CASCADE
							ON DELETE CASCADE;
               """)

    op.execute("ALTER TABLE results.figure DROP COLUMN caption_delimiter;")

    op.execute("""ALTER TABLE results.subfigure
					ADD COLUMN caption_input_tokens INT DEFAULT NULL,
					ADD COLUMN caption_output_tokens INT DEFAULT NULL;
               """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE results.article DROP CONSTRAINT results_article_id;")

    op.execute("ALTER TABLE results.figure ADD COLUMN caption_delimiter VARCHAR(12) DEFAULT NULL;")

    op.execute("""ALTER TABLE results.subfigure
					DROP COLUMN caption_input_tokens,
					DROP COLUMN caption_output_tokens;
               """)
