from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import exsclaim
import exsclaim.api
import pytest


@pytest.mark.asyncio
async def test_orm(db: AsyncSession):
	# Insert test data

	async with db:
		results = await db.execute(select(exsclaim.Article))
		articles = results.scalars().fetchall()
		assert len(articles) > 0, "There are no articles in the database to test"

		article = articles[0]
		assert isinstance(article, exsclaim.Article), f"The first returned value was not an exsclaim.Article, instead it was {type(article).__name__}"

		authors = article.authors
		assert len(authors) > 0, f"There are no authors for article {article.id} to test."
		author = authors[0]
		assert isinstance(author, exsclaim.Author), f"The first author was was not an exsclaim.Author, instead it was {type(author).__name__}."

		# Just making sure this doesn't crash
		await author.articles

		figures = await article.figures
		figure = figures[0]
		assert isinstance(figure, exsclaim.Figure), f"The first figure was not an exsclaim.Figure, instead it was {type(figure).__name__}."

		runs = await article.runs
		run = runs[0]
		assert isinstance(run, exsclaim.Run), f"The first run was not an exsclaim.Results, instead it was {type(run).__name__}."

		user = run.owner
		assert isinstance(user, exsclaim.User), f"The owner was not an exsclaim.User, instead it was {type(run).__name__}: {run!r}."

		user_runs = await user.runs
		assert len(user_runs) > 0, f"There are no runs for user {user.id} to test, even though this user was found from a run."


async def main():
	async with exsclaim.get_db_session() as db:
		await test_orm(db)


if __name__ == "__main__":
	import asyncio
	asyncio.run(main())
