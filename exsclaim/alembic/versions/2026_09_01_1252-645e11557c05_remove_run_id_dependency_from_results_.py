"""Remove Run ID dependency from results.article.

Revision ID: 645e11557c05
Revises: 751d7ac35cd2
Create Date: 2026-09-17 12:52:44.317458
Original Implementation Date: 2026-09-01
"""
from typing import Sequence, Union

from alembic import op

import asyncio
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '645e11557c05'
down_revision: Union[str, Sequence[str], None] = '751d7ac35cd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Creates a temporary table holding all information from the articles, as well as the start date for the run
    op.execute("""CREATE TEMP TABLE temp_articles AS
                    SELECT r.start_time, a.* FROM results.article a
                    INNER JOIN results.results r on a.run_id = r.id;
               """)

    # Deletes the duplicate ids so only the run that started most recently can keep the article id
    op.execute("""DELETE FROM temp_articles a
                    USING temp_articles b
                    WHERE a.id = b.id AND a.start_time > b.start_time;""")

    # Delete the run_id and start_time from the temporary articles table
    op.execute("""ALTER TABLE temp_articles
                    DROP COLUMN run_id,
                    DROP COLUMN start_time;
               """)

    # Create a new permanent table from the temporary data
    op.execute("CREATE TABLE results.article2 AS SELECT * FROM temp_articles;")

    # Sets the primary key as the id only
    op.execute("ALTER TABLE results.article2 ADD PRIMARY KEY (id);")

    # Creates a table mapping runs to their articles
    op.execute("""CREATE TABLE results.run_articles(
                    run_id UUID REFERENCES results.results(id) ON UPDATE CASCADE ON DELETE CASCADE,
                    article_id TEXT REFERENCES results.article2(id) ON UPDATE CASCADE ON DELETE CASCADE,
                    article_order INT NOT NULL,
                    PRIMARY KEY (run_id, article_id)
                  );""")

    # Insert the article mapping
    op.execute("""INSERT INTO results.run_articles
                    SELECT run_id, id, ROW_NUMBER() OVER (PARTITION BY run_id ORDER BY run_id DESC) AS order_number FROM results.article
                    ORDER BY run_id DESC;
               """)

    # Creates the new table for holding author information
    op.execute(r"""CREATE TABLE results.authors
                  (
                      id UUID NOT NULL PRIMARY KEY DEFAULT uuidv7(),
                      name VARCHAR NOT NULL,
                      orcid CHAR(19) UNIQUE CHECK ( orcid ~ '([\dX]{4}-[\dX]{4}-[\dX]{4}-[\dX]{4})'::TEXT )
                  );
               """)

    # Upload the authors from the articles table to the author table
    op.execute("""INSERT INTO results.authors(name)
                      SELECT DISTINCT(UNNEST(authors)) FROM results.article2;
               """)

    # Creates the table mapping each article to their authors (in order)
    op.execute("""
               CREATE TABLE results.article_authors
               (
                   article_id   TEXT NOT NULL REFERENCES results.article2(id)
                           ON UPDATE CASCADE ON DELETE CASCADE,
                   author_id    UUID NOT NULL REFERENCES results.authors(id)
                           ON UPDATE CASCADE ON DELETE CASCADE,
                   author_order SMALLINT,
                   PRIMARY KEY (article_id, author_id)
               );""")

    # Upload the authors
    op.execute("""INSERT INTO results.article_authors
                  SELECT a.id, i.id, ROW_NUMBER() OVER (PARTITION BY a.id ORDER BY a.id DESC) AS author_number FROM
                          (SELECT id, UNNEST(authors) AS author FROM results.article2) a
                              INNER JOIN results.authors i ON i.name = a.author
                  ORDER BY a.id, author_number;
               """)

    # Upload remove old constraints so they can be updated
    op.execute("""ALTER TABLE results.subfigurelabel
                    DROP CONSTRAINT subfigurelabel_run_id_subfigure_id_fkey,
                    DROP CONSTRAINT subfigurelabel_pkey;
               """)

    op.execute("""ALTER TABLE results.scalelabel
                    DROP CONSTRAINT scalelabel_run_id_scale_bar_id_fkey,
                    DROP CONSTRAINT scalelabel_pkey;
               """)

    op.execute("""ALTER TABLE results.scale
                    DROP CONSTRAINT scale_run_id_subfigure_id_fkey,
                    DROP CONSTRAINT scale_pkey;
               """)

    op.execute("""ALTER TABLE results.subfigure
                    DROP CONSTRAINT subfigure_run_id_figure_id_fkey,
                    DROP CONSTRAINT subfigure_pkey;
               """)

    # Remove duplicates from figure
    op.execute("""CREATE TEMPORARY TABLE temp_figure AS
                    SELECT f.*, r.start_time FROM results.figure f
                    INNER JOIN results.results r ON r.id = f.run_id;
               """)

    op.execute("""DELETE FROM temp_figure a
                    USING temp_figure b
                    WHERE a.id = b.id AND a.start_time > b.start_time;""")

    op.execute("""DELETE FROM results.figure;""")

    op.execute("ALTER TABLE temp_figure DROP COLUMN start_time;")

    op.execute("INSERT INTO results.figure SELECT * FROM temp_figure;")

    # Add new foreign key restraints
    op.execute("""ALTER TABLE results.figure
                    DROP CONSTRAINT figure_run_id_article_id_fkey,
                    ADD CONSTRAINT figure_run_id_articles_id_fkey FOREIGN KEY (article_id) REFERENCES results.article2(id),
                    ADD PRIMARY KEY (id),
                    DROP COLUMN run_id;
               """)

    op.execute("""ALTER TABLE results.subfigure
                    ADD CONSTRAINT subfigure_figure_id_figure_id_fkey FOREIGN KEY (figure_id) REFERENCES results.figure(id),
                    ADD CONSTRAINT subfigure_run_id_figure_id_fkey FOREIGN KEY (run_id) REFERENCES results.results(id),
                    ADD PRIMARY KEY (run_id, id);
               """)

    op.execute("""ALTER TABLE results.scale
                    ADD CONSTRAINT scale_scale_bar_id_scale_id_fkey FOREIGN KEY (run_id, subfigure_id) REFERENCES results.subfigure(run_id, id),
                    ADD PRIMARY KEY (run_id, id);
               """)

    op.execute("""ALTER TABLE results.scalelabel
                    ADD CONSTRAINT scalelabel_scale_bar_id_scale_id_fkey FOREIGN KEY (run_id, scale_bar_id) REFERENCES results.scale(run_id, id),
                    ADD PRIMARY KEY (run_id, scale_bar_id);""")

    op.execute("""ALTER TABLE results.subfigurelabel
        ADD CONSTRAINT subfigurelabel_subfigure_id_subfigure_id_fkey FOREIGN KEY (run_id, subfigure_id) REFERENCES results.subfigure(run_id, id),
        ADD PRIMARY KEY (run_id, subfigure_id);""")

    # Clean up temporary tables
    op.execute("DROP TABLE results.article;")

    op.execute("ALTER TABLE results.article2 RENAME TO article;")

    op.execute("ALTER TABLE results.article DROP COLUMN authors;")

    op.execute("ALTER TABLE results.results RENAME TO runs;")

    try:
        loop = asyncio.get_running_loop()
        if loop is not None and loop.is_running():
            loop.create_task(update_articles_data())
        else:
            asyncio.run(update_articles_data())
    except RuntimeError:
        asyncio.run(update_articles_data())


def downgrade() -> None:
    """Downgrade schema."""
    ...


def test_downgrade() -> None:
    """Testing out if this properly downgrades the schema."""
    op.execute("ALTER TABLE results.runs RENAME TO results;")

    op.execute("""ALTER TABLE results.article
                    ADD COLUMN authors TEXT[],
                    ADD COLUMN run_id UUID REFERENCES results.results(id),
                    ADD PRIMARY KEY (run_id, id)
    ;""")

    # TODO: Insert the runs for each article, before removing NOT NULL from run_id

    op.execute("""ALTER TABLE results.subfigure
                    DROP CONSTRAINT subfigure_figure_id_figure_id_fkey,
                    DROP CONSTRAINT subfigure_run_id_figure_id_fkey,
                    DROP CONSTRAINT subfigure_pkey;
               """)

    op.execute("""ALTER TABLE results.figure
                    DROP CONSTRAINT figure_run_id_article_id_fkey,
                    DROP CONSTRAINT figure_pkey,
                    ADD COLUMN run_id UUID NOT NULL,
                    ADD FOREIGN KEY (run_id, article_id) REFERENCES results.article(run_id, id),
                    ADD PRIMARY KEY (run_id, id)
               """)

    op.execute("DROP TABLE results.article_authors")

    op.execute("DROP TABLE results.authors")


async def update_articles_data():
    from pathlib import Path
    from tempfile import TemporaryDirectory

    import exsclaim

    async with exsclaim.get_db_session() as session:
        await session.execute(sa.text("DELETE FROM results.article_authors"))
        results = await session.execute(sa.select(exsclaim.Author))
        all_authors = results.scalars().all()
        authors_lookup = {author.name: author for author in all_authors}
        orcid_lookup = {author.orcid: author.id for author in all_authors if author.orcid is not None}

        with TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            for i, (name, cls) in enumerate(exsclaim.JournalFamily):
                new_name = f"{name}_{i}"
                journal = cls({
                    "name": new_name,
                    "results_dir": results_dir / new_name
                })
                results = await session.execute(sa.select(exsclaim.Article).where(exsclaim.Article.url.startswith(journal.domain)))
                articles = results.scalars().all()

                async with journal:
                    for article_num, article in enumerate(articles):
                        print(f"Processing article {article_num + 1:}/{len(articles):,}: {article.url}")
                        try:
                            article_dict = await journal.get_article_figures(article.url, None, save_html=False)
                        except BaseException as e:
                            print(f"An error occurred while processing article {article.url}: {e}")
                            continue

                        updated_article = dict(
                            title=article_dict["title"],
                            license=article_dict["license"],
                            open=article_dict["open"],
                            abstract=article_dict.get("abstract"),
                            article_id=article.id
                        )

                        await session.execute(
                            sa.text("UPDATE results.article SET title = :title, license = :license, open = :open, abstract = :abstract WHERE id = :article_id"),
                            updated_article
                        )

                        for author_num, author in enumerate(article_dict["authors"]):
                            if author.orcid is not None:
                                cached_author = orcid_lookup.get(author.orcid)
                            else:
                                cached_author = authors_lookup.get(author.name)

                            if cached_author is None:
                                # Upload author to the database
                                results = await session.execute(
                                    sa.text("INSERT INTO results.authors(name, orcid) VALUES(:name, :orcid) RETURNING id"),
                                    dict(name=author.name, orcid=author.orcid)
                                )
                                author_id = results.scalar_one()
                            else:
                                author_id = cached_author.id

                            await session.execute(
                                sa.text("INSERT INTO results.article_authors(article_id, author_id, author_order) VALUES(:article_id, :author_id, :author_order)"),
                                dict(
                                    article_id=article.id,
                                    author_id=author_id,
                                    author_order=author_num,
                                )
                            )

                        results = await session.execute(sa.text("SELECT id FROM results.figure WHERE article_id = :article_id"),
                                                        dict(article_id=article.id))
                        figure_ids = {row[0] for row in results.all()}

                        # Update the figures
                        for figure_id, figure in article_dict["figures"].items(): # Create a set of figure_ids that are in the database, insert if it's not th
                            figure_id = '.'.join(figure_id.split(".")[:-1]).replace("_", "-")
                            if figure_id in figure_ids:
                                await session.execute(
                                    sa.text("UPDATE results.figure SET caption = :caption, url = :url WHERE id = :id"),
                                    dict(
                                        caption=figure["full_caption"],
                                        url=figure["image_url"],
                                        id=figure_id
                                    )
                                )
                            else:
                                await session.execute(
                                    sa.text("INSERT INTO results.figure(id, caption, url, figure_path, article_id) VALUES(:id, :caption, :url, :figure_path, :article_id)"),
                                    dict(
                                        id=figure_id,
                                        caption=figure["full_caption"],
                                        url=figure["image_url"],
                                        figure_path=figure["figure_path"],
                                        article_id=article.id
                                    )
                                )

                    await session.commit()

        await session.execute(sa.text("DELETE FROM results.authors a WHERE a.id NOT IN (SELECT DISTINCT (author_id) FROM results.article_authors);"))
        await session.commit()


if __name__ == "__main__":
    asyncio.run(update_articles_data())
