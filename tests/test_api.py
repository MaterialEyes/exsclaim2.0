from faker import Faker
from itertools import pairwise
from starlette.testclient import TestClient
from sqlalchemy import MetaData, text
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

import asyncio
import pytest
import pytest_asyncio
import httpx


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


@pytest_asyncio.fixture(scope="session")
async def client():
	from exsclaim.api import get_app
	from exsclaim.db import get_db_session, Database, async_engine

	await Database().initialize_database()
	app = get_app()
	with TestClient(app, client=("127.0.0.1", 80), base_url="https://localhost") as test_client:
		yield test_client

	# async with async_engine.begin() as conn:
	# 	metadata = MetaData()
	# 	await conn.run_sync(lambda conn: metadata.reflect(bind=conn, resolve_fks=False))
	# 	await conn.run_sync(metadata.drop_all)


# @pytest.fixture(scope="session")
# async def initialize_test_database():
# 	async with get_db_session() as session:
# 		yield session


def test_healthcheck(client: TestClient):
	response = client.get("/healthcheck")
	assert response.status_code == 200, response.text


# def test_v1_articles(client: TestClient):
# 	response = client.get("/v1/articles")
# 	assert response.status_code == 200, response.text


def test_incorrect_journal_family(client: TestClient):
	query = get_valid_query()
	query["journal_family"] = "I don't exist"
	response = client.post("/query", data=query)
	assert response.status_code == 422, response.text


def test_incorrect_llm(client: TestClient):
	query = get_valid_query()
	query["llm"] = "I don't exist"
	response = client.post("/query", data=query)
	assert response.status_code == 422, response.text


def set_cookies(client: TestClient, response: Response):
	raw_cookie_headers = response.headers.get_list("set-cookie")
	for raw in raw_cookie_headers:
		name, _, rest = raw.partition("=")
		value, _, _ = rest.partition(";")

		name, value = name.strip(), value.strip()
		if not value or value == '""':
			client.cookies.delete(name)
		else:
			client.cookies.set(name, value)


def has_cookie(client: TestClient, response: Response, cookie: str) -> bool:
	return response.cookies.get(cookie, None) is not None or client.cookies.get(cookie, None) is not None


def check_username(response: Response, expected_username: str) -> bool:
	return expected_username == response.json()["username"]


def test_user_methods(client: TestClient, name: str = None, email: str = None, password: str = None):
	Faker.seed(1111)
	faker = Faker()

	name = name or faker.name()
	new_username = faker.name()
	email = email or faker.email()
	password = password or faker.password()

	response = client.get("/healthcheck")
	assert response.status_code == 200, f"Healthcheck was not successful: {response.text}."

	# Create account
	create_user_info = dict(username=name, email=email, password=password)
	response = client.post("/user/create_user", json=create_user_info)
	assert response.status_code == 201, f"Account not properly created: {response.text}"

	# The client has reported issues with setting the cookies, so it needs to be done manually
	set_cookies(client, response)

	assert has_cookie(client, response, "access_token"), "Access token was not provided when user was created."
	assert has_cookie(client, response, "refresh_token"), "Refresh token was not provided when user was created."

	# Make sure that refreshing the access_token works
	response = client.get("/user/remaining_access")
	assert response.status_code == 200, f"Could not check how long the access token exists for: {response.text}"

	response = client.post("/user/refresh")
	set_cookies(client, response)
	assert has_cookie(client, response, "access_token"), "Access token was not provided when refreshed."

	# Logout
	response = client.get("/user/logout")
	assert response.status_code == 200, f"Logout was not successful: {response.text}"
	set_cookies(client, response)
	assert not has_cookie(client, response, "access_token"), "Access token is still here even after logging out."
	assert not has_cookie(client, response, "refresh_token"), "Refresh token is still here even after logging out."

	# Logout when not logged in
	response = client.get("/user/logout")
	assert response.status_code == 401, f"Logout when not logged in did not work as expected: {response.text}"

	# Get guest name
	response = client.get("/user/username")
	assert response.status_code == 202, f"Could not get \"not logged in\" message: {response.text}"
	assert check_username(response, "Not Logged In."), f"Username {name} is not correct."

	# Login
	response = client.post("/user/login", json=dict(email=email, password=password))
	assert response.status_code == 200, "Login was not successful."
	set_cookies(client, response)
	assert has_cookie(client, response, "access_token"), f"Logging in did not provide the access token: {response.text}"
	assert has_cookie(client, response, "refresh_token"), f"Logging in did not provide the refresh token: {response.text}"

	# Get username
	response = client.get("/user/username")
	assert response.status_code == 200, f"Could not get username: {response.text}"
	assert check_username(response, name), f"Username {name} is not correct."

	# Change username
	response = client.patch("/user/username", content=new_username)
	assert response.status_code == 200, f"Could not get username: {response.json()}"

	response = client.get("/user/username")
	assert response.status_code == 200, f"Could not get username: {response.text}"
	assert check_username(response, new_username), f"Updating the username didn't work"

	# Create account with previously used email
	response = client.post("/user/create_user", json=create_user_info)
	assert response.status_code == 409, f"Creating an account that already exists did not respond as expected: {response.text}"

	# Delete the account
	response = client.delete("/user/remove-user")
	assert response.status_code == 200, f"Could not properly delete account: {response.text}"


@pytest.mark.asyncio
async def test_middleware_bans_paths(client: TestClient):
	from exsclaim import async_engine
	from warnings import warn

	response = client.get("/healthcheck")
	assert response.status_code == 200, f"Healthcheck was not successful: {response.text}."

	for path, next_path in pairwise((".git", ".env", None)):
		response = client.get(path)
		assert response.status_code == 404, f"Client was able to go to {path} uncontested"

		# Removes the ban to make sure that every path is checked. If it's the last path, leave the ban in place to make sure that no other requests work
		if next_path is not None:
			try:
				async with async_engine.begin() as conn:
					await conn.execute(text("DELETE FROM settings.banned_ips WHERE address = '127.0.0.1'"))
					await conn.commit()
			except RuntimeError as e:
				await conn.rollback()
				warn(f"Could not delete 127.0.0.1 from the banned ips when testing {path}: {e}")

	# Ensure that the IP is banned
	response = client.get("/healthcheck")
	assert response.status_code == 404, f"IP was still able to get to the healthcheck when it should have been banned: {response.text}"


async def main():
	await initialize_test_database()
	await test_healthcheck()
	await test_user_methods()
	# await test_v1_articles()
	# test_incorrect_journal_family()
	# test_incorrect_llm()


if __name__ == "__main__":
	asyncio.run(main())
