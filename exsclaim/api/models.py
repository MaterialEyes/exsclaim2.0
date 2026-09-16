from __future__ import annotations

from ..journals import JournalFamily
from ..caption import LLM
from ..config import ExsclaimSettings
from ..notifications import NTFY, Email, Webhook, QueryNotifications
from ..db.models import Article, Figure, Subfigure, Scale, SubfigureLabel, ScaleLabel, ClassificationCodes, \
	User, Run, SaveExtensions, Status, gen_uuid7, get_guest_uuid, RunArticles
from .json_models import Output

from datetime import datetime as dt, timezone as tz
from fastapi.responses import JSONResponse
from orjson import dumps
from pydantic import field_validator, model_validator
from sqlalchemy import text
from typing import Any, Literal, Optional, Self
from uuid import UUID

import pydantic
import sqlalchemy
import sqlalchemy.dialects.postgresql as sa_psql
import sqlmodel

__all__ = ["NTFY", "Email", "Webhook", "Query", "Article", "Figure", "Subfigure", "Scale", "SubfigureLabel",
		   "ScaleLabel", "ClassificationCodes", "SaveExtensions", "Status", "Run", "User", "get_guest_uuid",
		   "gen_uuid7", "PasswordReset", "ExsclaimJSONResponse", "Output", "Banner",
		   "QueryTools", "PreviousRunFilters", "RunArticles"]


class PasswordReset(sqlmodel.SQLModel, table=True):
	__tablename__ = "password_reset"
	__table_args__ = (
		sqlalchemy.ForeignKeyConstraint(["email"], ["users.users.email"], ondelete="CASCADE", onupdate="CASCADE"),
		dict(schema="users")
	)

	email: pydantic.EmailStr = sqlmodel.Field(
		title="The email of the user who's password needs to be reset.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			unique=True,
			primary_key=True,
			nullable=False
		)
	)

	created: dt = sqlmodel.Field(
		title="When the password reset attempt was created.",
		default_factory=lambda: dt.now(tz.utc),
		sa_column=sqlalchemy.Column(
			sqlmodel.DateTime(timezone=True),
			server_default=text("NOW()"),
			nullable=False,
		)
	)

	token: str = sqlmodel.Field(primary_key=True)
	# TODO: Cryptographically create a token to prove that the link sent to the email belongs to this email.


class Banner(sqlmodel.SQLModel, table=True):
	id: UUID = sqlmodel.Field(
		default_factory=gen_uuid7,
		title="The unique ID for the banners",
		sa_column=sqlalchemy.Column(
			sa_psql.UUID(as_uuid=True),
			primary_key=True,
			server_default=text("uuidv7()"),
			unique=True,
			nullable=False,
		)
	)
	content: str = sqlmodel.Field(
		title="The content that should be shown to the user.",
		sa_column=sqlalchemy.Column(
			sa_psql.TEXT,
			nullable=False
		)
	)
	created: dt = sqlmodel.Field(
		default_factory=lambda: dt.now(tz.utc),
		sa_column=sqlalchemy.Column(
			sqlmodel.DateTime(timezone=True),
			server_default=text("NOW()"),
			nullable=False,
		)
	)


class QueryTools(pydantic.BaseModel):
	journal_scraper: bool = pydantic.Field(default=True, description="If the JournalScraper should be run.")
	caption_distributor: bool = pydantic.Field(default=True, description="If the CaptionDistributor should be run.")
	figure_separator: bool = pydantic.Field(default=True, description="If the FigureSeparator should be run.")
	pdf_scraper: bool = pydantic.Field(default=False, description="If the PDFScraper should be run.")

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


class Query(pydantic.BaseModel):
	name: str = pydantic.Field(
		description="The name of the folder for this run.",
		pattern=r"^[\w_ -]+$"
	)

	journal_family: str = pydantic.Field(
		default="Nature",
		description="The Journal Family that EXSCLAIM should look through."
	)

	maximum_scraped: int = pydantic.Field(
		default=5,
		description="The maximum number of articles that EXSCLAIM should scrape. Maximum does not specify how many articles will be scraped before the process ends, only what the upper limit is.",
		ge=1
	)

	sortby: Literal["relevant", "recent"] = pydantic.Field(
		default="relevant",
		description="How the search feature should sort the articles, by the relevancy or the recent publish date."
	)

	term: str = pydantic.Field(
		description="The term or phrase that you want searched."
	)

	synonyms: list[str] = pydantic.Field(
		default_factory=list,
		description="Any synonyms that you're term might be related to."
	)

	save_format: list[Literal["subfigures", "visualization", "boxes", "postgres", "csv"]] = pydantic.Field(
		default=["boxes", "postgres"],
		description="How the results should be saved."
	)

	open: bool = pydantic.Field(
		default=False,
		description="Determines if EXSCLAIM only uses open-access articles (True) or any article that it can see (False)."
	)

	llm: str = pydantic.Field(
		default="llama3.2",
		description="The Large Language Model (LLM) that is used to separate captions and generate keywords for articles and figures."
	)

	pdf_path: Optional[str] = pydantic.Field(
		default=None,
		description="The local path towards the directory holding pdf files."
	)

	model_key: Optional[str] = pydantic.Field(
		default=None,
		description="The API key that might be needed depending on the specified llm."
	)

	notifications: QueryNotifications = pydantic.Field(
		description="A list of notification objects that are used when the pipeline finishes."
	)

	tools: QueryTools = pydantic.Field(
		default_factory=QueryTools,
		description="A list of EXSCLAIM tools to run in the pipeline.",
	)

	base_run_id: Optional[UUID] = pydantic.Field(
		default=None,
		description="The id of the EXSCLAIM run that this run will inherit the results from."
	)

	@field_validator("llm", mode="before")
	@classmethod
	def validate_llm(cls, llm: str) -> str:
		"""Checks if the given LLM is valid."""
		llm_lower = llm.lower()
		for name, (_, show_api_key, needs_api_key, label) in LLM:
			if llm_lower == name.lower() or (label is not None and label.lower() == llm_lower):
				return name
		raise ValueError(f"LLM \"{llm}\" is not a valid LLM model.")

	@field_validator("model_key", mode="before")
	@classmethod
	def validate_model_key(cls, model_key: Optional[str]) -> Optional[str]:
		if model_key is None:
			return None

		model_key = model_key.strip()
		if len(model_key) == 0:
			return None

		return model_key

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


class PreviousRunFilters(pydantic.BaseModel):
	status: list[Status] = pydantic.Field(
		default_factory=list,
		description="Look for runs with this status type."
	)

	name: Optional[str] = pydantic.Field(
		default=None,
		description="Look for runs with this name."
	)

	term: Optional[str] = pydantic.Field(
		default=None,
		description="Look for runs searching for this term."
	)

	min_articles: Optional[int] = pydantic.Field(
		default=None,
		description="Look for runs with at least this many articles found.",
		ge=0
	)

	max_articles: Optional[int] = pydantic.Field(
		default=None,
		description="Look for runs with at most this many articles found.",
		ge=0
	)

	min_figures: Optional[int] = pydantic.Field(
		default=None,
		description="Look for runs with at least this many figures.",
		ge=0
	)

	max_figures: Optional[int] = pydantic.Field(
		default=None,
		description="Look for runs with at most this many figures.",
		ge=0
	)

	min_scraped: Optional[int] = pydantic.Field(
		default=None,
		description="Look for runs that scraped at least this many articles.",
		ge=0
	)

	max_scraped: Optional[int] = pydantic.Field(
		default=None,
		description="Look for runs that scraped at most this many articles.",
		ge=0
	)

	return_values: list[Literal["id", "status", "name", "term", "start_time", "end_time", "run_time", "max_articles", "num_articles", "num_figures", "*"]] \
		= pydantic.Field(
		default=["*"],
		description="Only these columns will be returned."
	)

	@field_validator("return_values", mode="after")
	@classmethod
	def check_return_values(cls, return_values: list[str]) -> list[str]:
		if len(return_values) == 0:
			raise ValueError("At least one column must be returned.")

		if "*" in return_values and len(return_values) != 1:
			raise ValueError("Individual columns can not be specified when '*' is given. Only send ['*'] or remove it.")
		return return_values

	@model_validator(mode="after")
	def check_filters(self) -> Self:
		pairs = (
			(self.min_articles, self.min_articles, "number of articles"),
			(self.min_figures, self.min_figures, "number of figures"),
			(self.min_scraped, self.min_scraped, "number of scraped articles"),
		)

		for lower, upper, units in pairs:
			if lower is None or upper is None:
				continue

			if lower > upper:
				raise ValueError(f"The minimum {units} {lower:,} must be less than or equal to the maximum {units} {upper:,}.")

		return self

	def add_conditions_to_sql(self, params: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
		filters = [None] * (8 + len(Status))
		i = 0

		def set_filter(_filter: str, name: str, value):
			nonlocal i
			filters[i] = _filter
			params[name] = value
			i += 1

		for num, status in enumerate(set(self.status)):
			set_filter(f"r.status = :status{num}", f"status{num}", status)

		if self.name is not None:
			set_filter("r.name = :name", "name", self.name)

		if self.term is not None:
			set_filter("r.term = :term", "term", self.term)

		if self.min_articles is not None:
			set_filter("r.num_articles >= :min_articles", "min_articles", self.min_articles)

		if self.max_articles is not None:
			set_filter("r.num_articles <= :max_articles", "max_articles", self.max_articles)

		if self.min_figures is not None:
			set_filter("r.num_figures >= :min_figures", "min_figures", self.min_figures)

		if self.max_figures is not None:
			set_filter("r.num_figures <= :max_figures", "max_figures", self.max_figures)

		if self.min_scraped is not None:
			set_filter("r.max_articles >= :min_scraped", "min_scraped", self.min_scraped)

		if self.max_scraped is not None:
			set_filter("r.max_articles <= :max_scraped", "max_scraped", self.max_scraped)

		filters: list[str] = [f for f in filters if f is not None]
		return filters, params

	@property
	def selection(self) -> str:
		return ", ".join(map(lambda value: f"r.{value}", self.return_values))
