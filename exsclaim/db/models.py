import pydantic
import re
import sqlalchemy
import sqlalchemy.dialects.postgresql as sa_psql
import sqlmodel

from datetime import datetime as dt, timezone as tz
from enum import StrEnum
from sqlalchemy.ext.asyncio import AsyncAttrs
from sys import version_info
from typing import Annotated, Optional
from uuid import UUID

__all__ = ["Author", "ORCID_REGEX", "Article", "Figure", "Subfigure", "Scale", "SubfigureLabel", "ScaleLabel",
		   "ClassificationCodes", "User", "Run", "Status", "SaveExtensions", "gen_uuid7", "get_guest_uuid",
		   "ArticleAuthor", "RunArticles", "cryptographic_hash"]

if version_info >= (3, 14):
	def gen_uuid7() -> UUID:
		from uuid import uuid7
		return uuid7()
else:
	def gen_uuid7() -> UUID:
		from uuid_utils import uuid7
		return UUID(str(uuid7()))


def get_guest_uuid() -> UUID:
	# The time value came from when EXSCLAIM's first paper was released on arxiv, which will put the user before every other chronologically
	return UUID("01784c75-cd60-71d1-8988-8f2ebf927b3f")


def generate_salt(length: int = 16) -> bytes:
	from os import urandom # TODO: Generate better salts
	return urandom(length)


def cryptographic_hash(*ingredients: str, salt: bytes, iterations: int = 100_000) -> bytes:
	from functools import reduce
	from hashlib import pbkdf2_hmac
	from operator import add

	# Encode all of the ingredients as bytes then add them together
	value = reduce(add, map(lambda i: i.encode(), ingredients))

	return pbkdf2_hmac("sha256", value, salt, iterations)


class SaveExtensions(StrEnum):
	ZIP = "zip"
	TAR = "tar.gz"
	_7ZIP = "7z"


class Status(StrEnum):
	RUNNING = "Running"
	FINISHED = "Finished"
	ERROR = "Closed due to an error"
	STOPPED = "Stopped"


# language=PythonRegExp
ORCID_REGEX_STRING = r"([\dX]{4}-[\dX]{4}-[\dX]{4}-[\dX]{4})"
ORCID_REGEX = re.compile(ORCID_REGEX_STRING)

ORCID_TYPE = Annotated[Optional[str], pydantic.StringConstraints(pattern=ORCID_REGEX_STRING)]
"""A temporary fix while SQLModel is missing the pattern kwarg."""


class User(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "users"
	__table_args__ = (
		# Checks that the user is the guest login (which shouldn't have any login methods) OR has an attached ORCID OR has an email, password and salt saved
		sqlalchemy.CheckConstraint(f"""id = '{get_guest_uuid()}'::UUID OR
									orcid IS NOT NULL OR
                                    (email IS NOT NULL AND password_hash IS NOT NULL AND salt IS NOT NULL)""",
						name="check_login_methods"),
		dict(schema="users")
	)

	def __repr__(self) -> str:
		return f"User(id={self.id}, name={self.name})"

	def __eq__(self, other) -> bool:
		if isinstance(other, UUID):
			return self.id == other
		elif hasattr(other, "id"):
			return self.id == other.id
		return False

	id: UUID = sqlmodel.Field(
		default_factory=gen_uuid7,
		description="The user's unique ID.",
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			primary_key=True,
			index=True,
			server_default=sqlalchemy.text("uuidv7()"),
			unique=True,
			nullable=False,
		)
	)

	name: str = sqlmodel.Field(
		description="The user's name.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			primary_key=True,
			unique=False,
			nullable=False
		)
	)

	email: Optional[pydantic.EmailStr] = sqlmodel.Field(
		description="The user's email.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			unique=True,
			nullable=True
		)
	)

	orcid: ORCID_TYPE = sqlmodel.Field(
		description="The ORCID id associated with the user's login.",
		regex=ORCID_REGEX,
		# pattern=ORCID_REGEX,
		sa_column=sqlalchemy.Column(
			sa_psql.CHAR(19),
			sqlalchemy.CheckConstraint(f"orcid ~ '{ORCID_REGEX_STRING}'"),
			unique=True,
			nullable=True,
		)
	)

	created: dt = sqlmodel.Field(
		default_factory=lambda: dt.now(tz.utc),
		sa_column=sqlalchemy.Column(
			sqlmodel.DateTime(timezone=True),
			server_default=sqlalchemy.text("NOW()"),
			nullable=False,
		)
	)

	salt: Optional[bytes] = sqlmodel.Field(
		# default_factory=generate_salt,
		description="The salt for the user's password.",
		nullable=True,
		min_length=6,
		max_length=10
	)

	# DO NOT ENTER RAW (CLEARTEXT) PASSWORDS INTO THE DATABASE, ONLY ENCRYPTED HASHES!
	password_hash: Optional[bytes] = sqlmodel.Field(
		description="The user's password as a cryptographic hash.",
		nullable=True
	)

	_runs: list[Run] = sqlmodel.Relationship(
		back_populates="owner",
		sa_relationship_kwargs={
			"collection_class": list
		}
	)

	@property
	async def runs(self) -> list[Run]:
		return await self.awaitable_attrs._runs

	@property
	def jti(self) -> Optional[UUID]:
		if not hasattr(self, "_jti"):
			self._jti = None
		return self._jti

	@jti.setter
	def jti(self, value: Optional[UUID]) -> None:
		self._jti = value

	@jti.deleter
	def jti(self):
		self._jti = None

	@pydantic.field_validator("email", mode="before")
	@classmethod
	def normalize_emails(cls, raw_email: Optional[pydantic.EmailStr]) -> Optional[pydantic.EmailStr]:
		"""Ensures that all emails in the database are lowercase."""
		if raw_email is None:
			return None
		return raw_email.strip().lower()

	@staticmethod
	def generate_salt(*args, **kwargs) -> bytes:
		return generate_salt(*args, **kwargs)

	def verify_password(self, attempted_password: str) -> bool:
		from hmac import compare_digest

		return compare_digest(cryptographic_hash(attempted_password, salt=self.salt), self.password_hash)

	@staticmethod
	def has_permission(viewer: "User | UUID", run: Optional["Run"]) -> bool:
		if run is None:
			return False

		if isinstance(viewer, User):
			viewer = viewer.id

		owner = run.user_id
		return owner == get_guest_uuid() or owner == viewer or run.publicize_results


class ClassificationCodes(sqlmodel.SQLModel, table=True):
	__tablename__ = "classification_codes"

	code: str = sqlmodel.Field(
		description="The abbreviation of the classification code.",
		min_length=2,
		max_length=2,
		sa_column=sqlalchemy.Column(
			sa_psql.CHAR(2),
			primary_key=True,
			nullable=False,
		)
	)
	name: str = sqlmodel.Field(
		description="The name of the classification code.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False
		)
	)

	def __hash__(self) -> int:
		return hash(f"{self.code}:{self.name}")


class ArticleAuthor(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "article_authors"
	__table_args__ = (
		sqlalchemy.ForeignKeyConstraint(["article_id"], ["results.article.id"], ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.ForeignKeyConstraint(["author_id"], ["results.authors.id"], ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.PrimaryKeyConstraint("article_id", "author_id"),
		dict(schema="results")
	)

	article_id: str = sqlmodel.Field(
		description="The ID of the article.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False
		)
	)

	author_id: UUID = sqlmodel.Field(
		description="The ID of the author.",
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			nullable=False,
		)
	)

	author_order: int = sqlmodel.Field(
		description="The order of the author on the paper.",
		sa_column=sqlalchemy.Column(
			sqlmodel.SMALLINT
		)
	)

	_article: "Article" = sqlmodel.Relationship(
		back_populates="_author_links",
		# sa_relationship_kwargs=dict(overlaps="article")
	)

	_author: "Author" = sqlmodel.Relationship(
		back_populates="_article_links",
		# sa_relationship_kwargs=dict(overlaps="author")
	)

	@property
	async def article(self) -> "Article":
		return await self.awaitable_attrs._article

	@property
	async def author(self) -> "Author":
		return await self.awaitable_attrs._author

	# article: "Article" = sqlmodel.Relationship(
	# 	back_populates="_author_links",
	# 	sa_relationship_kwargs={"lazy": "selectin"}
	# )
	#
	# author: "Author" = sqlmodel.Relationship(
	# 	back_populates="_article_links",
	# 	sa_relationship_kwargs={"lazy": "selectin"}
	# )


class Author(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "authors"
	__table_args__ = dict(schema="results")

	id: UUID = sqlmodel.Field(
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			primary_key=True,
			index=True,
			server_default=sqlalchemy.text("uuidv7()"),
			unique=True,
			nullable=False,
		),
		description="The unique ID for an author.",
	)

	name: str = sqlmodel.Field(
		description="The name of the author.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
		)
	)

	orcid: ORCID_TYPE = sqlmodel.Field(
		default=None,
		description="The author's ORCID iD, if available.",
		regex=ORCID_REGEX_STRING,
		# pattern=ORCID_REGEX,
		sa_column=sqlalchemy.Column(
			sa_psql.CHAR(19),
			sqlalchemy.CheckConstraint(f"orcid ~ '{ORCID_REGEX_STRING}'"),
		)
	)

	articles: list["Article"] = sqlmodel.Relationship(
		back_populates="authors",
		link_model=ArticleAuthor,
		sa_relationship_kwargs={
			"overlaps": "articles,_article,_author"
		}
	)

	_article_links: list[ArticleAuthor] = sqlmodel.Relationship(
		back_populates="_author",
		sa_relationship_kwargs={
			"overlaps": "articles"
		}
	)

	# @property
	# async def articles(self) -> list["Article"]:
	# 	return await self.awaitable_attrs._articles

	@property
	async def article_links(self) -> list[ArticleAuthor]:
		return await self.awaitable_attrs._article_links

	def __repr__(self) -> str:
		if self.orcid is None:
			return f"Author({self.name})"
		return f"Author({self.name}, orcid={self.orcid})"

	def __hash__(self) -> int:
		if self.orcid is not None:
			return hash(self.orcid)
		return hash(self.name)

	def __eq__(self, other: object) -> bool:
		if isinstance(other, str):
			return self.name == other
		elif not isinstance(other, self.__class__):
			return False
		if other.orcid is not None:
			return self.orcid == other.orcid
		return self.name == other.name


class Article(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "article"
	__table_args__ = (
		dict(schema="results")
	)

	id: str = sqlmodel.Field(
		description="The id of the article. Typically, its the url path without the domain name.",
		# max_length=32,
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			primary_key=True,
			nullable=False,
		)
	)
	title: str = sqlmodel.Field(
		description="The description of the article.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False,
		)
	)
	url: str = sqlmodel.Field(
		description="The url to reach the article.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			# max_length=200,
			nullable=False,
			unique=True
		)
	)
	license: Optional[str] = sqlmodel.Field(
		description="The article's license url.",
		# max_length=200,
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			default=None,
			nullable=True,
		)
	)
	open: bool = sqlmodel.Field(
		default=False,
		description="If the article is open access."
	)
	abstract: Optional[str] = sqlmodel.Field(
		description="The abstract for the article.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			default=None,
		)
	)
	_figures: list["Figure"] = sqlmodel.Relationship(
		back_populates="_article",
		sa_relationship_kwargs={
			"collection_class": list
		}
	)

	_run_links: list["RunArticles"] = sqlmodel.Relationship(
		back_populates="article",
		sa_relationship_kwargs={"lazy": "selectin"}
	)

	_author_links: list[ArticleAuthor] = sqlmodel.Relationship(
		back_populates="_article",
		sa_relationship_kwargs={
			"overlaps": "authors,_author,articles"
		}
	)

	authors: list[Author] = sqlmodel.Relationship(
		back_populates="articles",
		link_model=ArticleAuthor,
		sa_relationship_kwargs={
			"lazy": "selectin",
			"overlaps": "_article_links,_author,_article"
		}
	)

	@property
	async def figures(self) -> list["Figure"]:
		return await self.awaitable_attrs._figures

	@property
	async def runs(self) -> list["Run"]:
		return [link.run for link in await self.awaitable_attrs._run_links]

	@property
	async def author_links(self):
		return await self.awaitable_attrs._author_links

	@pydantic.model_serializer(mode="wrap")
	def serialize_model(self, handler):
		data = handler(self)
		data["authors"] = [author.name for author in self.authors]
		return data


class Run(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "runs"
	__table_args__ = (
		sqlalchemy.ForeignKeyConstraint(["user_id"], ["users.users.id"], ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.Index("ix_results_runs_user_id_start_time", "user_id", "start_time"),
		dict(schema="results")
	)

	id: UUID = sqlmodel.Field(
		default_factory=gen_uuid7,
		description="The unique run ID",
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			primary_key=True,
			server_default=sqlalchemy.text("uuidv7()"),
			unique=True,
			nullable=False,
		)
	)
	user_id: UUID = sqlmodel.Field(
		default_factory=get_guest_uuid,
		description="The ID of the user that requested this run.",
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			server_default=sqlalchemy.text(f"'{get_guest_uuid()}'::UUID"),
			nullable=False,
		)
	)
	start_time: dt = sqlmodel.Field(
		default_factory=lambda: dt.now(tz.utc),
		sa_column=sqlalchemy.Column(
			sqlmodel.DateTime(timezone=True),
			server_default=sqlalchemy.text("NOW()"),
			nullable=False,
		)
	)
	end_time: Optional[dt] = sqlmodel.Field(
		sa_column=sqlalchemy.Column(
			sqlmodel.DateTime(timezone=True),
			server_default=sqlalchemy.text("NULL"),
			nullable=True,
		)
	)
	search_query: dict = sqlmodel.Field(
		nullable=False,
		sa_type=sa_psql.JSONB
	)
	extension: SaveExtensions = sqlmodel.Field(
		default=SaveExtensions.TAR,
		sa_column=sqlalchemy.Column(
			sqlalchemy.Enum(
				SaveExtensions,
				name="save_extensions",
				create_constraint=True,
				values_callable=lambda x: [i.value for i in x]
			),
			server_default=sqlalchemy.text("'tar.gz'::save_extensions"),
			nullable=False,
		),
	)
	status: Status = sqlmodel.Field(
		default=Status.RUNNING,
		sa_column=sqlalchemy.Column(
			sqlalchemy.Enum(
				Status,
				name="status",
				create_constraint=True,
				values_callable=lambda x: [i.value for i in x]
			),
			server_default=sqlalchemy.text("'Running'::status"),
			nullable=False,
		),
	)
	publicize_results: bool = sqlmodel.Field(
		default=False,
		sa_column_kwargs=dict(
			server_default=sqlalchemy.text("FALSE"),
			nullable=False,
		)
	)

	_article_links: list["RunArticles"] = sqlmodel.Relationship(
		back_populates="run",
	)

	owner: User = sqlmodel.Relationship(
		back_populates="_runs",
		sa_relationship_kwargs={"lazy": "selectin"}
	)

	@property
	async def articles(self) -> list["Article"]:
		return [link.article for link in await self.awaitable_attrs._article_links]


class RunArticles(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "run_articles"
	__table_args__ = (
		sqlalchemy.ForeignKeyConstraint(["run_id"], ["results.runs.id"], ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.ForeignKeyConstraint(["article_id"], ["results.article.id"], ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.PrimaryKeyConstraint("run_id", "article_id"),
		dict(schema="results")
	)

	run_id: UUID = sqlmodel.Field(
		description="The unique run ID that this article is attached to.",
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			nullable=False,
		)
	)

	article_id: str = sqlmodel.Field(
		description="The id of the article. Typically, its the url path without the domain name.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False,
		)
	)

	article_order: int = sqlmodel.Field(
		description="The order that this article was found in the run.",
		nullable=False
	)

	article: Article = sqlmodel.Relationship(
		back_populates="_run_links",
		sa_relationship_kwargs={"lazy": "selectin"}
	)

	run: Run = sqlmodel.Relationship(
		back_populates="_article_links",
		sa_relationship_kwargs={"lazy": "selectin"}
	)


class Figure(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "figure"
	__table_args__ = (
		# sqlalchemy.ForeignKeyConstraint(["run_id"], ["results.runs.id"], ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.ForeignKeyConstraint(["article_id"], ["results.article.id"], ondelete="CASCADE", onupdate="CASCADE"),
		dict(schema="results")
	)

	id: str = sqlmodel.Field(
		description="The id of the figure. Typically, its the id of the article that the figure came from followed by the images number within the article.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			# max_length=40,
			primary_key=True,
			nullable=False,
		)
	)
	caption: str = sqlmodel.Field(
		description="The caption of the figure.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False,
		)
	)
	url: str = sqlmodel.Field(
		description="The url to reach the raw figure.",
		# max_length=200,
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False,
		)
	)
	figure_path: str = sqlmodel.Field(
		description="The path to the figure in the results directory.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			# max_length=100,
			nullable=False,
		)
	)
	article_id: str = sqlmodel.Field(
		description="The id of the article that the figure came from.",
		# max_length=32,
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False,
		)
	)
	_article: Article = sqlmodel.Relationship(
		back_populates="_figures",
	)
	_subfigures: list["Subfigure"] = sqlmodel.Relationship(
		back_populates="_figure",
		sa_relationship_kwargs={
			"collection_class": list
		}
	)

	@property
	async def article(self) -> Article:
		return await self.awaitable_attrs._article

	@property
	async def subfigures(self) -> list["Subfigure"]:
		return await self.awaitable_attrs._subfigures


class Subfigure(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "subfigure"
	__table_args__ = (
		sqlalchemy.ForeignKeyConstraint(["classification_code"], ["classification_codes.code"], ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.ForeignKeyConstraint(["figure_id"], ["results.figure.id"], ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.ForeignKeyConstraint(["run_id"], ["results.runs.id"], ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.PrimaryKeyConstraint("run_id", "id"),
		dict(schema="results")
	)

	run_id: UUID = sqlmodel.Field(
		description="The unique run ID that this article is attached to.",
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			nullable=False,
		)
	)

	id: str = sqlmodel.Field(
		description="The id of the figure. Typically, its the id of the article that the figure came from followed by the images number within the article.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			# max_length=44,
			nullable=False,
		)
	)
	classification_code: str = sqlmodel.Field(
		description="The classification code.",
		min_length=2,
		max_length=2,
		sa_column=sqlalchemy.Column(
			sa_psql.CHAR(2),
			nullable=False
		)
	)
	classification_confidence: Optional[float] = sqlmodel.Field(
		ge=0,
		le=1,
		description="The confidence of the subfigure's classification.",
		nullable=True
	)
	confidence: Optional[float] = sqlmodel.Field(
		ge=0,
		le=1,
		description="The confidence of the subfigure's bounding box.",
		nullable=True
	)
	height: Optional[float]
	width: Optional[float]
	nm_height: Optional[float]
	nm_width: Optional[float]
	x1: int
	y1: int
	x2: int
	y2: int
	caption: Optional[str] = sqlmodel.Field(
		description="The caption of the subfigure.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=True,
		)
	)
	caption_input_tokens: Optional[int] = sqlmodel.Field(
		description="The number of input tokens given to the LLM."
	)
	caption_output_tokens: Optional[int] = sqlmodel.Field(
		description="The number of output tokens returned from the LLM."
	)
	keywords: Optional[list[str]] = sqlmodel.Field(
		default=None,
		description="The keywords related to the subfigure.",
		sa_column=sqlalchemy.Column(
			sqlalchemy.ARRAY(sqlalchemy.TEXT)
		)
	)
	figure_id: str = sqlmodel.Field(
		description="The id of the figure that this subfigure came from.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			# max_length=40,
			nullable=False,
		)
	)
	_figure: Figure = sqlmodel.Relationship(
		back_populates="_subfigures"
	)

	_scales: list["Scale"] = sqlmodel.Relationship(
		back_populates="_subfigure"
	)

	_labels: list["SubfigureLabel"] = sqlmodel.Relationship(
		back_populates="_subfigure"
	)

	@property
	async def figure(self) -> Figure:
		return await self.awaitable_attrs._figure

	@property
	async def scales(self) -> list["Scale"]:
		return await self.awaitable_attrs._scales

	@property
	async def labels(self) -> list["SubfigureLabel"]:
		return await self.awaitable_attrs._labels


class Scale(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "scale"
	__table_args__ = (
		sqlalchemy.ForeignKeyConstraint(["run_id", "subfigure_id"], ["results.subfigure.run_id", "results.subfigure.id"],
							 ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.PrimaryKeyConstraint("run_id", "id"),
		dict(schema="results")
	)

	run_id: UUID = sqlmodel.Field(
		description="The unique run ID that this article is attached to.",
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			nullable=False,
		)
	)

	id: str = sqlmodel.Field(
		description="The id of the figure. Typically, its the id of the article that the figure came from followed by the images number within the article.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			# max_length=48,
			nullable=False,
		)
	)
	x1: int = sqlmodel.Field(
		description="The left coordinate of the scale."
	)
	y1: int = sqlmodel.Field(
		description="The upper coordinate of the scale."
	)
	x2: int = sqlmodel.Field(
		description="The right coordinate of the scale."
	)
	y2: int = sqlmodel.Field(
		description="The lower coordinate of the scale."
	)
	length: Optional[int] = sqlmodel.Field(
		default=None,
		nullable=True,
	)
	label_line_distance: Optional[float] = sqlmodel.Field(
		default=None,
		nullable=True,
	)
	confidence: Optional[float] = sqlmodel.Field(
		default=None,
		nullable=True,
	)
	subfigure_id: str = sqlmodel.Field(
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False,
			# max_length=44
		)
	)
	_subfigure: Subfigure = sqlmodel.Relationship(
		back_populates="_scales"
	)
	_labels: list["ScaleLabel"] = sqlmodel.Relationship(
		back_populates="_scale"
	)

	@property
	async def subfigure(self) -> Subfigure:
		return await self.awaitable_attrs._subfigure

	@property
	async def labels(self) -> list["ScaleLabel"]:
		return await self.awaitable_attrs._labels


class SubfigureLabel(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "subfigurelabel"
	__table_args__ = (
		sqlalchemy.ForeignKeyConstraint(["run_id", "subfigure_id"], ["results.subfigure.run_id", "results.subfigure.id"],
							 ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.PrimaryKeyConstraint("run_id", "subfigure_id"),
		dict(schema="results")
	)

	run_id: UUID = sqlmodel.Field(
		description="The unique run ID that this article is attached to.",
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			nullable=False,
		)
	)

	text: str = sqlmodel.Field(
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False,
		)
	)
	x1: int = sqlmodel.Field(
		description="The left coordinate of the subfigure's label."
	)
	y1: int = sqlmodel.Field(
		description="The upper coordinate of the subfigure's label."
	)
	x2: int = sqlmodel.Field(
		description="The right coordinate of the subfigure's label."
	)
	y2: int = sqlmodel.Field(
		description="The lower coordinate of the subfigure's label."
	)
	label_confidence: Optional[float] = sqlmodel.Field(
		default=None,
		nullable=True,
	)
	box_confidence: Optional[float] = sqlmodel.Field(
		default=None,
		nullable=True,
	)
	subfigure_id: str = sqlmodel.Field(
		# max_length=44,
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False,
		)
	)
	_subfigure: Subfigure = sqlmodel.Relationship(back_populates="_labels")

	@property
	async def subfigure(self) -> Subfigure:
		return await self.awaitable_attrs._subfigure


class ScaleLabel(AsyncAttrs, sqlmodel.SQLModel, table=True):
	__tablename__ = "scalelabel"
	__table_args__ = (
		sqlalchemy.ForeignKeyConstraint(["run_id", "scale_bar_id"], ["results.scale.run_id", "results.scale.id"],
							 ondelete="CASCADE", onupdate="CASCADE"),
		sqlalchemy.PrimaryKeyConstraint("run_id", "scale_bar_id"),
		dict(schema="results")
	)

	run_id: UUID = sqlmodel.Field(
		description="The unique run ID that this article is attached to.",
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			nullable=False,
		)
	)

	text: str = sqlmodel.Field(
		# max_length=15,
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False,
		)
	)
	x1: int = sqlmodel.Field(
		description="The left coordinate of the scale's label."
	)
	y1: int = sqlmodel.Field(
		description="The upper coordinate of the scale's label."
	)
	x2: int = sqlmodel.Field(
		description="The right coordinate of the scale's label."
	)
	y2: int = sqlmodel.Field(
		description="The lower coordinate of the scale's label."
	)
	label_confidence: Optional[float] = sqlmodel.Field(
		default=None,
		nullable=True,
	)
	box_confidence: Optional[float] = sqlmodel.Field(
		default=None,
		nullable=True,
	)
	nm: Optional[float] = sqlmodel.Field(
		default=None,
		nullable=True,
	)
	scale_bar_id: str = sqlmodel.Field(
		description="The id of the scale bar that this label belongs to.",
		# max_length=48,
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False,
		)
	)
	_scale: Scale = sqlmodel.Relationship(back_populates="_labels")

	@property
	async def scale(self) -> Scale:
		return await self.awaitable_attrs._scale
