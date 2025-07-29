"""Functions for interacting with postgres database"""
from .models import *

from asyncpg.exceptions import FeatureNotSupportedError
from configparser import ConfigParser, NoSectionError
from logging import exception
from os import PathLike, getenv
from pathlib import Path
from shutil import copy
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Any
from uuid import UUID


__all__ = ["async_engine", "modify_database_configuration", "get_database_connection_string", "Database"]


def get_database_connection_string(configuration_file:PathLike[str] = None, section:str = "Postgres", password_file:PathLike[str]=None) -> str:
	"""
	Creates a Postgres database connection string from a configuration file.
	:param PathLike[str] configuration_file:
	:param str section:
	:raises configparser.NoSectionError: If the provided configuration file does not contain a section with the name provided in the section parameter.
	:raises FileNotFoundError: If the provided password file does not exist.
	:rtype: str
	"""
	def get_value(environment_name:str, default_value:str, ini_params:dict[str, str], ini_name:str=None) -> str:
		value = getenv(environment_name, default_value)
		value = ini_params.get(ini_name, value)
		return value

	ini_params = {}
	if configuration_file is not None:
		parser = ConfigParser()
		parser.read(configuration_file)

		if not parser.has_section(section):
			raise NoSectionError(section)

		ini_params = {key: value for key, value in parser.items(section)}

	username = get_value("POSTGRES_USER", "exsclaim", ini_params, "user")
	port = get_value("POSTGRES_PORT", "5432", ini_params, "port")
	database_name = get_value("POSTGRES_DB", "exsclaim", ini_params, "database")
	host = get_value("POSTGRES_HOST", "localhost", ini_params, "host")

	password_file = password_file or getenv("POSTGRES_PASSWORD_FILE", "/run/secrets/db_password")
	try:
		if not (Path(password_file).exists() and Path(password_file).is_file()):
			raise FileNotFoundError(f"Password file \"{password_file}\" does not exist.")

		with open(password_file, "r") as f:
			password = f.read().strip()
	except FileNotFoundError as e:
		password = ""
		print(e)

	# db is one of the aliases given through Docker Compose
	url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database_name}"
	return url


def modify_database_configuration(config_path:str):
	"""Alter database.ini to store configuration for future runs

	Args:
		config_path (str): path to .ini file
	Modifies:
		database.ini
	"""
	current_file = Path(__file__).resolve()
	database_ini = current_file.parent / "database.ini"
	config_path = Path(config_path)
	copy(config_path, database_ini)


async_engine = create_async_engine(
	get_database_connection_string(),
	echo=False,
)


class Database:
	def __init__(self, name="exsclaim", configuration_file=None):
		db_url = get_database_connection_string(configuration_file, name)

		self.async_engine = create_async_engine(
			db_url,
			echo=True,
			future=True,
		)

	async def ensure_connection(self):
		async with self.async_engine.connect() as connection:
			print(f"Connection successful.")

	async def upload(self, csv_info: dict[str, list[Any]], run_id:UUID):
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
					except IntegrityError as e:
						if "duplicate key value" in str(e):
							exception("Attempted to add duplicate primary keys to the database.")
							await session.rollback()
							continue
						else:
							exception(f"SQLAlchemy error found when uploading the results.")
							await session.rollback()
							break
					except SQLAlchemyError:
						exception(f"SQLAlchemy error found when uploading the results.")
						await session.rollback()
						break
					except BaseException:
						exception(f"Non-SQLAlchemy error found when uploading the results.")
						await session.rollback()
						break

	async def initialize_database(self, ignore_uuid7: bool = True):
		from sqlalchemy.schema import CreateSchema
		from sqlalchemy.sql import text, select
		from ..api.models import Results

		async with self.async_engine.begin() as conn:
			try:
				await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pg_uuidv7\";"))
			except SQLAlchemyError as e:
				if not ignore_uuid7:
					raise FeatureNotSupportedError("Please add UUIDv7 support for Postgres. https://pgxn.org/dist/pg_uuidv7/") from e
				await conn.rollback()

		async with self.async_engine.begin() as conn:
			await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))

			await conn.execute(CreateSchema("results", if_not_exists=True))
			await conn.run_sync(SQLModel.metadata.create_all, checkfirst=True)

		classification_codes = (
			ClassificationCodes(code="MC", name="microscopy"),
			ClassificationCodes(code="DF", name="diffraction"),
			ClassificationCodes(code="GR", name="graph"),
			ClassificationCodes(code="PH", name="basic_photo"),
			ClassificationCodes(code="IL", name="illustration"),
			ClassificationCodes(code="UN", name="unclear"),
			ClassificationCodes(code="PT", name="parent"),
			ClassificationCodes(code="SB", name="subfigure"),
		)

		async with AsyncSession(self.async_engine) as session:
			existing_codes = await session.exec(select(ClassificationCodes))
			existing_codes = existing_codes.all()

			if not len(existing_codes):
				session.add_all(classification_codes)
				await session.commit()
