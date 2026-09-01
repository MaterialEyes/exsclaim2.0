"""Functions for interacting with postgres database"""
from .models import *

from contextlib import asynccontextmanager
from pathlib import Path
from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.dialects.postgresql.asyncpg import AsyncAdapt_asyncpg_dbapi
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlmodel import SQLModel
from typing import Any, AsyncGenerator, Optional
from uuid import UUID

import logging
import sqlalchemy.exc as sql_exc

__all__ = ["async_engine", "Database", "get_db_session"]


class PostgresSettings(BaseSettings):
	"""Gets access to the environment variables for the PostgreSQL database."""
	model_config = SettingsConfigDict(env_prefix="POSTGRES_", secrets_dir=("/run/secrets/", "/var/run"))

	USER: str = Field(
		default="exsclaim"
	)

	PORT: int = Field(
		default=5432
	)

	DB: str = Field(
		default="exsclaim"
	)

	HOST: str = Field(
		default="localhost"
	)

	PASSWORD: Optional[str] = Field(
		default=None
	)

	PASSWORD_FILE: Optional[Path] = Field(
		default=None,
	)

	@field_validator("PASSWORD_FILE")
	@classmethod
	def check_if_password_file_exists(cls, file: Optional[Path]) -> Optional[Path]:
		if file is None:
			return file

		if not file.is_file():
			raise ValueError(f"Given Postgres password file: \"{file}\" is not a file.")

		return file.resolve()

	@computed_field
	@property
	def connection_string(self) -> str:
		if self.PASSWORD is not None:
			password = self.PASSWORD.strip()
		elif self.PASSWORD_FILE is not None:
			with open(self.PASSWORD_FILE, "r") as f:
				password = f.read().strip()
		else:
			raise ValueError("A password for Postgres must be provided either through \"POSTGRES_PASSWORD\" or \"POSTGRES_PASSWORD_FILE\".")

		return f"postgresql+asyncpg://{self.USER}:{password}@{self.HOST}:{self.PORT}/{self.DB}"


_postgres_settings = PostgresSettings()
async_engine = create_async_engine(
	_postgres_settings.connection_string,
	echo=False,
)


@asynccontextmanager
async def get_db_session(logger: Optional[logging.Logger] = None, **kwargs) -> AsyncGenerator[AsyncSession, None]:
	async with AsyncSession(async_engine, **kwargs) as session:
		try:
			yield session
		except sql_exc.SQLAlchemyError as e:
			await session.rollback()
			if logger is not None:
				logger.critical("An error occurred with a database transaction.", exc_info=e)
			else:
				raise e


class Database:
	def __init__(self, name="exsclaim", configuration_file=None):
		self.async_engine = create_async_engine(
			_postgres_settings.connection_string,
			echo=True,
			future=True,
		)

	async def ensure_connection(self):
		async with self.async_engine.connect() as _:
			print(f"Connection successful.")

	async def upload(self, csv_info: dict[str, list[Any]], run_id: UUID, logger: logging.Logger):
		cls_mapping = dict(
			article=Article,
			figure=Figure,
			subfigure=Subfigure,
			scale=Scale,
			scale_label=ScaleLabel,
			subfigure_label=SubfigureLabel
		)

		async with AsyncSession(self.async_engine) as session:
			for _type, cls in cls_mapping.items():
				rows = csv_info[_type]
				# Converts each of the objects from JSON form into their respective SQLModel classes, dynamically mapping each attribute to the given value
				objects = (
					cls(run_id=run_id, **dict(zip(tuple(cls.model_fields.keys())[1:], row)))
					for row in rows
				)

				async with session.begin():
					try:
						session.add_all(objects)
						await session.commit()
					except (sql_exc.IntegrityError, AsyncAdapt_asyncpg_dbapi.IntegrityError) as e:
						if "duplicate key value" in str(e):
							logger.exception("Attempted to add duplicate primary keys to the database.", exc_info=e)
							await session.rollback()
							continue
						else:
							logger.exception(f"SQLAlchemy error found when uploading the results.", exc_info=e)
							await session.rollback()
							break
					except sql_exc.SQLAlchemyError as e:
						logger.exception(f"SQLAlchemy error found when uploading the results.", exc_info=e)
						await session.rollback()
						break
					except BaseException as e:
						logger.exception(f"Non-SQLAlchemy error found when uploading the results.", exc_info=e)
						await session.rollback()
						break

	async def initialize_database(self):
		from sqlalchemy.schema import CreateSchema
		from sqlalchemy.sql import text, select, insert
		from ..api.models import Results, User, get_guest_uuid
		from ..api.db import initialize_db as api_db

		async with self.async_engine.begin() as conn:
			await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))

			for schema in ("results", "users"):
				await conn.execute(CreateSchema(schema, if_not_exists=True))
			await conn.run_sync(SQLModel.metadata.create_all, checkfirst=True)

			result = await conn.execute(text("SELECT COUNT(id) FROM users.users WHERE email IS NULL;"))
			if not result.fetchone()[0]:
				await conn.execute(insert(User).values(id=get_guest_uuid(), name="Default User"))

			await api_db(conn)

		# Insert classification codes into the database
		classification_codes = (
			ClassificationCodes(code="MC", name="Microscopy"),
			ClassificationCodes(code="DF", name="Diffraction"),
			ClassificationCodes(code="GR", name="Graph"),
			ClassificationCodes(code="PH", name="Basic Photo"),
			ClassificationCodes(code="IL", name="Illustration"),
			ClassificationCodes(code="UN", name="Unclear"),
			ClassificationCodes(code="PT", name="Parent"),
			ClassificationCodes(code="SB", name="Subfigure"),
		)

		async with AsyncSession(self.async_engine) as session:
			existing_codes = await session.execute(select(ClassificationCodes))
			existing_codes = existing_codes.all()

			if not len(existing_codes):
				session.add_all(classification_codes)
				await session.commit()
