from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

import exsclaim
import pytest_asyncio


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def db():
	async_engine = create_async_engine(
		exsclaim.db.postgres.PostgresSettings().connection_string,
		echo=False,
	)
	await exsclaim.Database().initialize_database()

	async with AsyncSession(async_engine) as session:
		yield session
