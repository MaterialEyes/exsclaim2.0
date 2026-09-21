"""Convert VARCHAR columns to TEXT.

Revision ID: 751d7ac35cd2
Revises: 
Create Date: 2026-09-17 12:36:45.565924
Original Implementation Date: 2026-08-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '751d7ac35cd2'
down_revision: Union[str, Sequence[str], None] = 'cb4427d95375'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE settings.banned_ips ALTER COLUMN reason SET DATA TYPE TEXT;")

    op.execute(r"""ALTER TABLE users.users
                        ALTER COLUMN name SET DATA TYPE TEXT,
                        ALTER COLUMN email SET DATA TYPE TEXT,
                        ALTER COLUMN orcid SET DATA TYPE CHAR(19),
                        DROP CONSTRAINT IF EXISTS users_orcid_check,
                        ADD CONSTRAINT users_orcid_check CHECK ( orcid ~ '([\dX]{4}-[\dX]{4}-[\dX]{4}-[\dX]{4})'::TEXT );
               """)

    op.execute("ALTER TABLE users.password_reset ALTER COLUMN email SET DATA TYPE TEXT")

    op.execute("ALTER TABLE public.banner ALTER COLUMN content SET DATA TYPE TEXT;")

    op.execute("""ALTER TABLE results.article
                        ALTER COLUMN title SET DATA TYPE TEXT,
                        ALTER COLUMN license SET DATA TYPE TEXT,
                        ALTER COLUMN abstract SET DATA TYPE TEXT,
                        ALTER COLUMN id SET DATA TYPE TEXT,
                        ALTER COLUMN url SET DATA TYPE TEXT,
                        ALTER COLUMN authors SET DATA TYPE TEXT[];
               """)

    op.execute("""ALTER TABLE results.figure
                        ALTER COLUMN caption SET DATA TYPE TEXT,
                        ALTER COLUMN url SET DATA TYPE TEXT,
                        ALTER COLUMN figure_path SET DATA TYPE TEXT,
                        ALTER COLUMN article_id SET DATA TYPE TEXT,
                        ALTER COLUMN id SET DATA TYPE TEXT;
               """)

    op.execute("ALTER TABLE public.classification_codes ALTER COLUMN name SET DATA TYPE TEXT;")

    op.execute("""ALTER TABLE results.subfigure
                        ALTER COLUMN caption SET DATA TYPE TEXT,
                        ALTER COLUMN figure_id SET DATA TYPE TEXT,
                        ALTER COLUMN id SET DATA TYPE TEXT,
                        ALTER COLUMN keywords SET DATA TYPE TEXT[];
               """)

    op.execute("""ALTER TABLE results.subfigurelabel
                        ALTER COLUMN text SET DATA TYPE TEXT,
                        ALTER COLUMN subfigure_id SET DATA TYPE TEXT;
               """)

    op.execute("""ALTER TABLE results.scale
                        ALTER COLUMN id SET DATA TYPE TEXT,
                        ALTER COLUMN subfigure_id SET DATA TYPE TEXT;
               """)

    op.execute("""ALTER TABLE results.scalelabel
                        ALTER COLUMN text SET DATA TYPE TEXT,
                        ALTER COLUMN scale_bar_id SET DATA TYPE TEXT;
               """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE settings.banned_ips ALTER COLUMN reason SET DATA TYPE VARCHAR;")

    op.execute(r"""ALTER TABLE users.users
                        ALTER COLUMN name SET DATA TYPE VARCHAR,
                        ALTER COLUMN email SET DATA TYPE VARCHAR,
                        ALTER COLUMN orcid SET DATA TYPE CHAR(19),
                        DROP CONSTRAINT users_orcid_check;
               """)

    op.execute("ALTER TABLE users.password_reset ALTER COLUMN email SET DATA TYPE VARCHAR")

    op.execute("ALTER TABLE public.banner ALTER COLUMN content SET DATA TYPE VARCHAR;")

    op.execute("""ALTER TABLE results.article
                        ALTER COLUMN title SET DATA TYPE VARCHAR,
                        ALTER COLUMN license SET DATA TYPE VARCHAR,
                        ALTER COLUMN abstract SET DATA TYPE VARCHAR,
                        ALTER COLUMN id SET DATA TYPE VARCHAR,
                        ALTER COLUMN url SET DATA TYPE VARCHAR,
                        ALTER COLUMN authors SET DATA TYPE VARCHAR[];
               """)

    op.execute("""ALTER TABLE results.figure
                        ALTER COLUMN caption SET DATA TYPE VARCHAR,
                        ALTER COLUMN url SET DATA TYPE VARCHAR,
                        ALTER COLUMN figure_path SET DATA TYPE VARCHAR,
                        ALTER COLUMN article_id SET DATA TYPE VARCHAR,
                        ALTER COLUMN id SET DATA TYPE VARCHAR;
               """)

    op.execute("ALTER TABLE public.classification_codes ALTER COLUMN name SET DATA TYPE VARCHAR;")

    op.execute("""ALTER TABLE results.subfigure
                        ALTER COLUMN caption SET DATA TYPE VARCHAR,
                        ALTER COLUMN figure_id SET DATA TYPE VARCHAR,
                        ALTER COLUMN id SET DATA TYPE VARCHAR,
                        ALTER COLUMN keywords SET DATA TYPE VARCHAR[];
               """)

    op.execute("""ALTER TABLE results.subfigurelabel
                        ALTER COLUMN text SET DATA TYPE VARCHAR,
                        ALTER COLUMN subfigure_id SET DATA TYPE VARCHAR;
               """)

    op.execute("""ALTER TABLE results.scale
                        ALTER COLUMN id SET DATA TYPE VARCHAR,
                        ALTER COLUMN subfigure_id SET DATA TYPE VARCHAR;
               """)

    op.execute("""ALTER TABLE results.scalelabel
                        ALTER COLUMN text SET DATA TYPE VARCHAR,
                        ALTER COLUMN scale_bar_id SET DATA TYPE VARCHAR;
               """)
