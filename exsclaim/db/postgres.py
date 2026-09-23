"""Functions for interacting with postgres database"""
from .models import Author, ClassificationCodes, ArticleAuthor, Figure, Subfigure, SubfigureLabel, Scale, ScaleLabel

from contextlib import asynccontextmanager
from pathlib import Path
from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select, text, insert
from typing import Any, AsyncGenerator, Optional
from uuid import UUID, uuid4

import logging
import sqlalchemy
import sqlalchemy.exc as sql_exc
import sqlalchemy.ext.asyncio as sql_async
import sqlalchemy.dialects.postgresql as sa_psql


__all__ = ["async_engine", "Database", "get_db_session", "PostgresSettings"]


class PostgresSettings(BaseSettings):
	"""Gets access to the environment variables for the PostgreSQL database."""
	model_config = SettingsConfigDict(
		env_prefix="POSTGRES_",
		secrets_dir=("/run/secrets/", "/var/run"),
		secrets_dir_missing="ok"
	)

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

		connection = f"postgresql+asyncpg://{self.USER}:{password}@{self.HOST}:{self.PORT}/{self.DB}"
		return connection


_postgres_settings = PostgresSettings()
async_engine = sql_async.create_async_engine(
	_postgres_settings.connection_string,
	echo=False,
)


@sqlalchemy.event.listens_for(async_engine.sync_engine, "connect")
def register_uuid_codec(dbapi_connection: sa_psql.asyncpg.AsyncAdapt_asyncpg_connection, connection_record: sqlalchemy.pool.base._ConnectionRecord):
	dbapi_connection.run_async(
		lambda connection: connection.set_type_codec(
			"uuid",
			schema="pg_catalog",
			encoder=str,
			decoder=UUID,
			format="text"
		)
	)


@asynccontextmanager
async def get_db_session(logger: Optional[logging.Logger] = None, **kwargs) -> AsyncGenerator[sql_async.AsyncSession, None]:
	async with sql_async.AsyncSession(async_engine, **kwargs) as session:
		try:
			yield session
		except sql_exc.SQLAlchemyError as e:
			await session.rollback()
			if logger is not None:
				logger.critical("An error occurred with a database transaction.", exc_info=e)
			else:
				raise e


class Database:
	def __init__(self):
		self.async_engine = sql_async.create_async_engine(
			_postgres_settings.connection_string,
			echo=True,
			future=True,
		)

	async def ensure_connection(self):
		async with self.async_engine.connect():
			print("Connection successful.")

	async def upload(self, exsclaim_json: dict[str, dict[str, Any]], run_id: UUID, logger: logging.Logger):
		async with sql_async.AsyncSession(self.async_engine) as session:
			results = await session.execute(select(ClassificationCodes))
			codes = results.scalars().all()
			codes = {code.name.upper(): code.code.upper() for code in codes}
			await session.commit()

			for article_num, (article_id, article_json) in enumerate(exsclaim_json.items()):
				async with session.begin():
					results = await session.execute(
						text("SELECT EXISTS (SELECT 1 FROM results.article WHERE id=:id)"),
						dict(id=article_id)
					)
					article_in_database: bool = results.scalar()

					if not article_in_database:
						authors: tuple[Author] = article_json["authors"]
						author_ids = [None] * len(authors)
						for i, author in enumerate(authors):
							if isinstance(author, dict):
								author = Author.model_validate({**author, "id": uuid4()})
							if author.orcid is not None:
								results = await session.execute(
									text("SELECT id FROM results.authors WHERE orcid=:orcid"),
									dict(orcid=author.orcid)
								)
								author_id: Optional[UUID] = results.scalar_one_or_none()

								if author_id is not None:
									author_ids[i] = author_id
									continue

							results = await session.execute(
								text("INSERT INTO results.authors(name, orcid) VALUES(:name, :orcid) RETURNING id"),
								dict(name=author.name, orcid=author.orcid)
							)
							author_id = results.scalar_one_or_none()
							author_ids[i] = author_id

						# Upload the article json
						await session.execute(
							text("INSERT INTO results.article(id, title, url, license, open) VALUES(:id, :title, :url, :license, :open)"),
							dict(
								id=article_id,
								title=article_json["title"],
								url=article_json["article_url"],
								license=article_json["license"],
								open=article_json["open"],
							)
						)

						# Upload mapping of authors to the article
						author_ids = [
							dict(article_id=article_id, author_id=author_id, author_order=i)
							for i, author_id in enumerate(author_ids)
						]
						await session.execute(insert(ArticleAuthor).values(author_ids))

						# Upload the figure JSONs
						figures = [dict(
							# run_id=run_id,
							caption=figure_json["full_caption"],
							url=figure_json["image_url"],
							figure_path=figure_json["figure_path"],
							article_id=article_id,
							id=figure_id.replace("_", "-").split(".")[0]
						) for figure_id, figure_json in article_json["figures"].items()]

						if len(figures) > 0:
							await session.execute(insert(Figure).values(figures))

					# Upload mapping of article to run id
					await session.execute(
						text("INSERT INTO results.run_articles(run_id, article_id, article_order) VALUES(:run_id, :article_id, :order)"),
						dict(run_id=run_id, article_id=article_id, order=article_num)
					)

					# Upload the subfigures (these vary per run because of the caption that's generating the caption)
					subfigures = []
					subfigure_labels = []
					scales = []
					scale_labels = []

					for figure_id, figure_json in article_json["figures"].items():
						figure_id = figure_id.replace("_", "-").split(".")[0]
						for subfigure in figure_json["master_images"]:
							subfigure_label = subfigure["subfigure_label"]
							scale_bars = subfigure.get("scale_bars", ())
							subfigure_id = f"{figure_id}-{subfigure_label["text"]}"

							geometry = subfigure["geometry"]
							subfigures.append(
								dict(
									classification_code=codes[subfigure["classification"].upper()],
									classification_confidence=subfigure["classification_confidence"],
									confidence=subfigure["confidence"],
									height=subfigure["height"],
									width=subfigure["width"],
									nm_height=subfigure.get("nm_height"),
									nm_width=subfigure.get("nm_width"),
									x1=geometry["x0"],
									y1=geometry["y0"],
									x2=geometry["x1"],
									y2=geometry["y1"],
									caption=subfigure.get("caption"),
									keywords=subfigure.get("keywords", list()),
									figure_id=figure_id,
									caption_input_tokens=subfigure.get("caption_input_tokens"),
									caption_output_tokens=subfigure.get("caption_output_tokens"),
									id=subfigure_id,
									run_id=run_id,
								)
							)

							label_geometry = subfigure["geometry"]
							subfigure_labels.append(dict(
								text=subfigure_label["text"],
								x1=label_geometry["x0"],
								y1=label_geometry["y0"],
								x2=label_geometry["x1"],
								y2=label_geometry["y1"],
								label_confidence=subfigure_label.get("label_confidence"),
								box_confidence=subfigure_label.get("box_confidence"),
								run_id=run_id,
								subfigure_id=subfigure_id,
							))

							for i, scale_bar in enumerate(scale_bars):
								scale_bar_id = f"{subfigure_id}-{i}"
								scale_geometry = scale_bar["geometry"]
								scales.append(dict(
									x1=scale_geometry["x0"],
									y1=scale_geometry["y0"],
									x2=scale_geometry["x1"],
									y2=scale_geometry["y1"],
									length=scale_bar["length"],
									label_line_distance=scale_bar["label_line_distance"],
									confidence=scale_bar["confidence"],
									subfigure_id=subfigure_id,
									run_id=run_id,
									id=scale_bar_id,
								))

								scale_label = scale_bar["label"]
								label_geometry = scale_label["geometry"]
								scale_labels.append(dict(
									text=scale_label["text"],
									x1=label_geometry["x0"],
									y1=label_geometry["y0"],
									x2=label_geometry["x1"],
									y2=label_geometry["y1"],
									label_confidence=scale_label["label_confidence"],
									box_confidence=scale_label["box_confidence"],
									nm=scale_label["nm"],
									run_id=run_id,
									scale_bar_id=scale_bar_id,
								))

					for cls, values in (
						(Subfigure, subfigures),
						(SubfigureLabel, subfigure_labels),
						(Scale, scales),
						(ScaleLabel, scale_labels),
					):
						if len(values) > 0:
							await session.execute(insert(cls).values(values))

					try:
						# session.add_all(objects)
						await session.commit()
					except (sql_exc.IntegrityError, sa_psql.asyncpg.AsyncAdapt_asyncpg_dbapi.IntegrityError) as e:
						if "duplicate key value" in str(e):
							logger.exception("Attempted to add duplicate primary keys to the database.", exc_info=e)
							await session.rollback()
							continue
						else:
							logger.exception("SQLAlchemy error found when uploading the results.", exc_info=e)
							await session.rollback()
							break
					except sql_exc.SQLAlchemyError as e:
						logger.exception("SQLAlchemy error found when uploading the results.", exc_info=e)
						await session.rollback()
						break
					except BaseException as e:
						logger.exception("Non-SQLAlchemy error found when uploading the results.", exc_info=e)
						await session.rollback()
						break

	async def initialize_database(self):
		from sqlalchemy.schema import CreateSchema
		from ..api.models import Run, User, get_guest_uuid # These models need to be imported before SQLModel.metadata.create_all
		from ..api.db import initialize_db as api_db

		import sqlmodel

		async with self.async_engine.begin() as conn:
			await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))

			for schema in ("results", "users"):
				await conn.execute(CreateSchema(schema, if_not_exists=True))
			await conn.run_sync(sqlmodel.SQLModel.metadata.create_all, checkfirst=True)

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

		async with sql_async.AsyncSession(self.async_engine) as session:
			existing_codes = await session.execute(select(ClassificationCodes))
			existing_codes = existing_codes.all()

			if not len(existing_codes):
				session.add_all(classification_codes)
				await session.commit()

	@staticmethod
	def run_alembic():
		from ..version import Version

		from alembic import command
		from alembic.config import Config
		from itertools import pairwise

		current_version = Version()

		alembic_revision_loopkup: dict[Version, str] = {
			Version("2.5.3"): "3924f9a632d1"
		}

		directory = Path(__file__).parent.parent.resolve()
		alembic_cfg = Config(directory / "alembic.ini")
		alembic_cfg.set_main_option("sqlalchemy.url", PostgresSettings().connection_string)

		keys = tuple(alembic_revision_loopkup.keys())
		for version1, version2 in pairwise(keys):
			if version1 <= current_version < version2:
				command.upgrade(alembic_cfg, alembic_revision_loopkup[version1])
				break
		else:
			command.upgrade(alembic_cfg, alembic_revision_loopkup[keys[-1]])
