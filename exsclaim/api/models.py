from __future__ import annotations

from ..journal import JournalFamily
from ..caption import LLM
from ..config import ExsclaimSettings
from ..db.models import ExsclaimSQLModel, Article, Figure, Subfigure, Scale, SubfigureLabel, ScaleLabel, ClassificationCodes
from .json_models import *

from datetime import datetime as dt, timezone as tz
from enum import StrEnum
from fastapi import Path
from fastapi.responses import JSONResponse
from httpx import Client, InvalidURL, Response
from orjson import dumps
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import Enum as SAEnum, Column, ForeignKeyConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import text, SQLModel, Field, DateTime
from typing import Annotated, Literal, Optional, Any
from uuid import UUID


__all__ = ["BaseModel", "NTFY", "Query", "ExsclaimSQLModel", "Article", "Figure", "Subfigure", "Scale", "SubfigureLabel",
		   "ScaleLabel", "ClassificationCodes", "SaveExtensions", "Status", "Results", "User", "get_guest_uuid", "Sessions",
		   "gen_uuid7", "PasswordReset", "generate_salt", "cryptographic_hash", "ExsclaimJSONResponse", "Output", "Banner"]


def gen_uuid7() -> UUID:
	from sys import version_info
	if version_info >= (3, 14):
		from uuid import uuid7, uuid5
		return uuid7()

	from uuid_utils import uuid7
	return UUID(str(uuid7()))


def create_link(link: str) -> str:
	# return f"<a href={link}>{link}</a>"
	# return f"[{link}]({link})"
	return link


def get_guest_uuid() -> UUID:
	# The time value came from when EXSCLAIM's first paper was released on arxiv, which will put the user before every other chronologically
	return UUID("01784c75-cd60-71d1-8988-8f2ebf927b3f")


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


def generate_salt(length: int = 16) -> bytes:
	from os import urandom # TODO: Generate better salts
	return urandom(length)


class User(SQLModel, table=True):
	__tablename__ = "users"
	__table_args__ = (
		# Checks that the user is the guest login (which shouldn't have any login methods) OR has an attached ORCID OR has an email, password and salt saved
		CheckConstraint(f"""id = '{get_guest_uuid()}' OR
									orcid IS NOT NULL OR
                                    (email IS NOT NULL AND password_hash IS NOT NULL AND salt IS NOT NULL)""", name="check_login_methods"),
		dict(schema="users")
	)

	id: UUID = Field(
		default_factory=gen_uuid7,
		title="The user's unique ID.",
		sa_column=Column(
			PGUUID(as_uuid=True),
			primary_key=True,
			index=True,
			server_default=text("uuidv7()"),
			unique=True,
			nullable=False,
		)
	)

	name: str = Field(
		primary_key=False,
		unique=False,
		title="The user's name.",
		nullable=False
	)

	email: Optional[EmailStr] = Field(
		unique=True,
		title="The user's email.",
		nullable=True
	)

	orcid: Optional[str] = Field(
		unique=True,
		title="The ORCID id associated with the user's login.",
		nullable=True,
		regex=r"\d{4}-\d{4}-\d{4}-\d{4}"
	)

	created: dt = Field(
		default_factory=lambda: dt.now(tz.utc),
		sa_column=Column(
			DateTime(timezone=True),
			server_default=text("NOW()"),
			nullable=False,
		)
	)

	salt: Optional[bytes] = Field(
		# default_factory=generate_salt,
		title="The salt for the user's password.",
		nullable=True,
		min_length=6,
		max_length=10
	)

	# DO NOT ENTER RAW (CLEARTEXT) PASSWORDS INTO THE DATABASE, ONLY ENCRYPTED HASHES!
	password_hash: Optional[bytes] = Field(
		title="The user's password as a cryptographic hash.",
		nullable=True
	)

	@field_validator("email", mode="before")
	@classmethod
	def normalize_emails(cls, raw_email):
		"""Ensures that all emails in the database are lowercase."""
		return raw_email.strip().lower()

	@staticmethod
	def generate_salt(*args, **kwargs) -> bytes:
		return generate_salt(*args, **kwargs)

	def verify_password(self, attempted_password: str) -> bool:
		from hmac import compare_digest

		return compare_digest(cryptographic_hash(attempted_password, salt=self.salt), self.password_hash)

	@staticmethod
	def has_permission(viewer: UUID, results: Optional[Results]) -> bool:
		if results is None:
			return False
		owner = results.user_id
		return owner == get_guest_uuid() or owner == viewer or results.publicize_results


class Sessions(SQLModel, table=True):
	__tablename__ = "sessions"
	__table_args__ = (
		ForeignKeyConstraint(["user"], ["users.users.id"],
							 ondelete="CASCADE", onupdate="CASCADE"),
		dict(schema="users")
	)

	user: UUID = Field(title="The user's ID")
	key: UUID = Field(primary_key=True)
	salt: bytes = Field()
	created: dt = Field(
		default_factory=lambda: dt.now(tz.utc),
		sa_column=Column(
			DateTime(timezone=True),
			server_default=text("NOW()"),
			nullable=False,
		)
	)
	expiration: Optional[dt] = Field(
		sa_column=Column(
			DateTime(timezone=True),
			server_default=text("NOW() + '1 DAYS'::INTERVAL"),
			nullable=True,
		)
	)


class PasswordReset(SQLModel, table=True):
	__tablename__ = "password_reset"
	__table_args__ = (
		ForeignKeyConstraint(["email"], ["users.users.email"],
							 ondelete="CASCADE", onupdate="CASCADE"),
		dict(schema="users")
	)

	email: EmailStr = Field(
		title="The email of the user who's password needs to be reset.",
		primary_key=True
	)

	created: dt = Field(
		title="When the password reset attempt was created.",
		default_factory=lambda: dt.now(tz.utc),
		sa_column=Column(
			DateTime(timezone=True),
			server_default=text("NOW()"),
			nullable=False,
		)
	)

	token: str = Field(primary_key=True) # TODO: Cryptographically create a token to prove that the link sent to the email belongs to this email.


class Results(SQLModel, table=True):
	__tablename__ = "results"
	__table_args__ = (
		ForeignKeyConstraint(["user_id"], ["users.users.id"],
							 ondelete="CASCADE", onupdate="CASCADE"),
		dict(schema="results")
	)

	id: UUID = Field(
		default_factory=gen_uuid7,
		title="The unique run ID",
		sa_column=Column(
			PGUUID(as_uuid=True),
			primary_key=True,
			server_default=text("uuidv7()"),
			unique=True,
			nullable=False,
		)
	)
	user_id: UUID = Field(
		default_factory=get_guest_uuid,
		title="The ID of the user that requested this run.",
		sa_column=Column(
			PGUUID(as_uuid=True),
			server_default=text(f"'{get_guest_uuid()}'::UUID"),
			nullable=False,
		)
	)
	start_time: dt = Field(
		default_factory=lambda: dt.now(tz.utc),
		sa_column=Column(
			DateTime(timezone=True),
			server_default=text("NOW()"),
			nullable=False,
		)
	)
	end_time: Optional[dt] = Field(
		sa_column=Column(
			DateTime(timezone=True),
			server_default=text("NULL"),
			nullable=True,
		)
	)
	search_query: dict = Field(
		nullable=False,
		sa_type=JSONB
	)
	extension: SaveExtensions = Field(
		default=SaveExtensions.TAR,
		sa_column=Column(
			SAEnum(
				SaveExtensions,
				name="save_extensions",
				create_constraint=True,
				values_callable=lambda x: [i.value for i in x]
			),
			server_default=text("'tar.gz'::save_extensions"),
			nullable=False,
		),
	)
	status: Status = Field(
		default=Status.RUNNING,
		sa_column=Column(
			SAEnum(
				Status,
				name="status",
				create_constraint=True,
				values_callable=lambda x: [i.value for i in x]
			),
			server_default=text("'Running'::status"),
			nullable=False,
		),
	)
	publicize_results: bool = Field(
		default=False,
		sa_column_kwargs=dict(
			server_default=text("FALSE"),
			nullable=False,
		)
	)


class Banner(SQLModel, table=True):
	id: UUID = Field(
		default_factory=gen_uuid7,
		title="The unique ID for the banners",
		sa_column=Column(
			PGUUID(as_uuid=True),
			primary_key=True,
			server_default=text("uuidv7()"),
			unique=True,
			nullable=False,
		)
	)
	content: str = Field(
		title="The ID of the user that requested this run.",
		nullable=False
	)
	created: dt = Field(
		default_factory=lambda: dt.now(tz.utc),
		sa_column=Column(
			DateTime(timezone=True),
			server_default=text("NOW()"),
			nullable=False,
		)
	)



class NTFY(BaseModel):
	"""A base model representing the necessary info to send an NTFY notification."""
	url: Annotated[str, Path(title=f"The url to the NTFY server, with the topic included (e.g. {create_link('https://ntfy.sh/exsclaim')})")]
	access_token: Annotated[str, Path(title=f"The access token that may be needed to send the NTFY notification as stated in {create_link('https://docs.ntfy.sh/publish/#access-tokens')}")] = None
	priority: Annotated[int, Path(title=f"The priority of the message as stated in {create_link('https://docs.ntfy.sh/publish/#message-priority')}.", ge=1, le=5)] = 3

	@field_validator("url", mode="before")
	@classmethod
	def validate_llm(cls, url: str) -> str:
		"""Checks if the given LLM is valid."""
		try:
			with Client() as client:
				response: Response = client.get(url)
				if response.is_success or response.is_redirect:
					return url
				raise ValueError(response.text)
		except InvalidURL as e:
			raise ValueError(str(e)) from e

	def to_json(self):
		return {
			"url": self.url,
			"access_token": self.access_token,
			"priority": str(self.priority),
		}


class QueryTools(BaseModel):
	journal_scraper: Annotated[bool, Path(title="If the JournalScraper should be run.")] = True
	caption_distributor: Annotated[bool, Path(title="If the CaptionDistributor should be run.")] = True
	figure_separator: Annotated[bool, Path(title="If the FigureSeparator should be run.")] = True
	pdf_scraper: Annotated[bool, Path(title="If the PDFScraper should be run.")] = False

	@field_validator("pdf_scraper", mode="before")
	@classmethod
	def validate_pdf_path(cls, pdf_scraper: bool) -> bool:
		"""Checks the system is allowing PDFScraper to be run."""
		if ExsclaimSettings().ALLOW_PDF_PATHS: # PDF Path won't even run in this isn't the case
			return pdf_scraper
		return False

	@property
	def tools(self):
		return dict(
			journal_scraper=self.journal_scraper,
			caption_distributor=self.caption_distributor,
			figure_separator=self.figure_separator,
			pdf_scraper=self.pdf_scraper,
		)


class Query(BaseModel):
	name: str = Field(
		description="The name of the folder for this run.",
		regex=r"^[\w_-]+$"
	)
	journal_family: Annotated[str, Path(title="The Journal Family that EXSCLAIM should look through.")] = "Nature"

	maximum_scraped: Annotated[int, Path(title="The maximum number of articles that EXSCLAIM should scrape. Maximum does not specify how many articles will be scraped before the process ends, only what the upper limit is.", ge=1)] = 5

	sortby: Annotated[Literal["relevant", "recent"], Path(title="How the search feature should sort the articles, by the relevancy or the recent publish date.")] = "relevant"

	term: Annotated[str, Path(title="The term or phrase that you want searched.")]

	synonyms: Annotated[list[str], Path(title="Any synonyms that you're term might be related to.", default_factory=list)]

	save_format: Annotated[list[Literal["subfigures", "visualization", "boxes", "postgres", "csv", "mongo"]],
		Path(title="How the results should be saved.")] = ["boxes", "postgres"]

	open_access: Annotated[bool, Path(title="Determines if EXSCLAIM only uses open-access articles (True).")] = False

	llm: Annotated[str,	Path(title="The Large Language Model (LLM) that is used to separate captions and generate keywords for articles and figures.")] = "llama3.2"

	pdf_path: Annotated[Optional[str], Path(title="The local path towards the directory holding the pdfs")] = None

	model_key: Annotated[str, Path(title="The API key that might be needed depending on the specified llm.")] = ""

	emails: Annotated[list[str], Path(title="The email address that will receive a notification when EXSCLAIM has finished running.",
	default_factory=list)]

	ntfy: Annotated[list[NTFY], Path(title="A list of NTFY links that will receive a notification when EXSCLAIM has finished running.",
	default_factory=list)]

	tools: Annotated[QueryTools, Path(description="A list of EXSCLAIM tools to run in the pipeline.")] = QueryTools()

	@field_validator("llm", mode="before")
	@classmethod
	def validate_llm(cls, llm: str) -> str:
		"""Checks if the given LLM is valid."""
		llm_lower = llm.lower()
		for name, (_, needs_api_key, label) in LLM:
			if llm_lower == name.lower() or (label is not None and label.lower() == llm_lower):
				return name
		raise ValueError(f"LLM \"{llm}\" is not a valid LLM model.")

	@field_validator("journal_family", mode="before")
	@classmethod
	def validate_journal_family(cls, journal: str) -> str:
		"""Checks if the given journal is valid."""
		journal_lower = journal.lower()
		for name, subclass in JournalFamily:
			if journal_lower == name.lower() or journal_lower == subclass.name().lower():
				return name
		raise ValueError(f"Journal \"{journal}\" is not a valid journal family.")

	@field_validator("pdf_path", mode="before")
	@classmethod
	def validate_pdf_path(cls, pdf_path: Optional[str]) -> Optional[str]:
		"""Checks if the PDF path is a valid path."""
		if ExsclaimSettings().ALLOW_PDF_PATHS: # PDF Path won't even run in this case
			return pdf_path
		return None


class ExsclaimJSONResponse(JSONResponse):
	@staticmethod
	def encoder(obj):
		if isinstance(obj, dt):
			return obj.isoformat()
		raise NotImplementedError

	def render(self, content: Any) -> bytes:
		# orjson
		return dumps(content)
