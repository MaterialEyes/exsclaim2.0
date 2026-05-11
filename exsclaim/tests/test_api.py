from exsclaim.api import get_app
from exsclaim.db import async_engine, Database

import pytest

from asyncio import run
from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from httpx import ASGITransport, AsyncClient

from fastapi.testclient import TestClient
client = TestClient(get_app())


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


# @pytest.mark.anyio
# async def initialize_test_database():
# 	await Database().initialize_database()
# 	# TODO: Run EXSCLAIM on one of the EXSCLAIM papers and hard code those Models into this code so it can initialize a test db


def test_healthcheck():
	response = client.get("/healthcheck")
	assert response.status_code == 200, response.text


def test_v1_articles():
	response = client.get("/v1/articles")
	assert response.status_code == 200, response.text


def test_incorrect_journal_family():
	query = get_valid_query()
	query["journal_family"] = "I don't exist"
	response = client.post("/query", data=query)
	assert response.status_code == 422, response.text


def test_incorrect_llm():
	query = get_valid_query()
	query["llm"] = "I don't exist"
	response = client.post("/query", data=query)
	assert response.status_code == 422, response.text


@pytest.mark.anyio
async def test_user_methods(name: str = None, email: str = None, password: str = None):
	from faker import Faker

	fake = Faker()
	name = name or fake.name()
	email = email or fake.email()
	password = password or fake.password()

	async with AsyncClient(transport=ASGITransport(app=get_app()), base_url="http://dev.exsclaim.local:8000") as client:
		response = await client.get("/healthcheck")
		assert response.status_code == 200, f"Healthcheck was not successful: {response.text}."

		# Create account
		response = await client.post("/user/create_user", json=dict(name=name, email=email, password=password))
		assert response.status_code == 201, "Account not properly created."

		# Create account with previously used email
		response = await client.post("/user/create_user", json=dict(name=name, email=email, password=password))
		assert response.status_code == 409, "Creating an account that already exists did not respond as expected."

		# Login
		assert response.cookies.get("session_id", None) is None, "There was already a login cookie provided."
		response = await client.post("/user/login", json=dict(email=email, password=password))
		assert response.status_code == 200, "Login was not successful."
		cookie = response.cookies.get("session_id", None)
		assert cookie is not None, "Logging in did not provide the cookie."

		# Logout
		response = await client.post("/user/logout")
		assert response.status_code == 200, f"Logout was not successful: {response.text}"

		# Logout when not logged in
		response = await client.post("/user/logout")
		assert response.status_code == 202, f"Logout when not logged in did not work as expected: {response.text}"


async def main():
	await client.wait_startup()
	# await initialize_test_database()
	test_healthcheck()
	await test_user_methods()
	# await test_v1_articles()
	# test_incorrect_journal_family()
	# test_incorrect_llm()


if __name__ == "__main__":
	run(main())
