from exsclaim.api import app
from exsclaim.db import async_engine, Database

import pytest

from asyncio import run
from contextlib import contextmanager
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession


client = TestClient(app)


def get_valid_query() -> dict:
	return dict(
		name="api_test",
		journal_family="Nature",
		maximum_scraped=7,
		sortby="relevant",
		term="electronic polymers",
		synonyms=[],
		llm="llama3.2",
		open_access=True,
		save_format=["boxes", "save_subfigures", "postgres"],
		logging=["print", "exsclaim.log"]
	)


@contextmanager
async def db(): # TODO: Get the session working here
	async_session = sessionmaker(
		bind=async_engine, class_=AsyncSession, expire_on_commit=False
	)

	async with async_session() as session:
		yield session


@pytest.mark.asyncio
async def initialize_test_database():
	await Database().initialize_database()
	# TODO: Run EXSCLAIM on one of the EXSCLAIM papers and hard code those Models into this code so it can initialize a test db


def test_healthcheck():
	response = client.get("/healthcheck")
	assert response.status_code == 200


def test_v1_articles():
	response = client.get("/v1/articles")
	assert response.status_code == 200


def test_incorrect_journal_family():
	query = get_valid_query()
	query["journal_family"] = "I don't exist"
	response = client.post("/query", data=query)
	assert response.status_code == 422


def test_incorrect_llm():
	query = get_valid_query()
	query["llm"] = "I don't exist either"
	response = client.post("/query", data=query)
	assert response.status_code == 422


async def main():
	await initialize_test_database()
	test_healthcheck()
	await test_v1_articles()
	test_incorrect_journal_family()
	test_incorrect_llm()


if __name__ == "__main__":
	run(main())
