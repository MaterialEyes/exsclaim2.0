from ..journal import JournalFamily
from ..caption import LLM
from ..db.models import ExsclaimSQLModel, Article, Figure, Subfigure, Scale, SubfigureLabel, ScaleLabel, ClassificationCodes

from datetime import datetime as dt, timezone as tz
from enum import StrEnum
from fastapi import Path
from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import Enum as SAEnum, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import text, SQLModel, Field, DateTime
from typing import Annotated, Literal, Optional
from uuid import UUID, uuid4


__all__ = ["BaseModel", "NTFY", "Query", "ExsclaimSQLModel", "Article", "Figure", "Subfigure", "Scale", "SubfigureLabel", "ScaleLabel",
		   "ClassificationCodes", "SaveExtensions", "Status", "Results"]


def create_link(link:str) -> str:
	# return f"<a href={link}>{link}</a>"
	# return f"[{link}]({link})"
	return link


class SaveExtensions(StrEnum):
	ZIP = "zip"
	TAR = "tar.gz"
	_7ZIP = "7z"


class Status(StrEnum):
	RUNNING = "Running"
	FINISHED = "Finished"
	ERROR = "Closed due to an error"


class Results(SQLModel, table=True):
	__tablename__ = "results"

	id: UUID = Field(
		default_factory=uuid4,
		primary_key=True,
		index=True,
		title="The unique run ID",
		sa_column_kwargs=dict(
			server_default=text("uuid_generate_v4()"),
			unique=True,
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


class NTFY(BaseModel):
	"""A base model representing the necessary info to send an NTFY notification."""
	link: Annotated[str, Path(title=f"The link to the NTFY server, with the topic included (e.g. {create_link('https://ntfy.sh/exsclaim')})")]
	access_token: Annotated[str, Path(title=f"The access token that may be needed to send the NTFY notification as stated in {create_link('https://docs.ntfy.sh/publish/#access-tokens')}")] = None
	priority: Annotated[int, Path(title=f"The priority of the message as stated in {create_link('https://docs.ntfy.sh/publish/#message-priority')}.", ge=1, le=5)] = 3

	def to_json(self):
		return {
			"url": self.link,
			"access_token": self.access_token,
			"priority": str(self.priority),
		}


class Query(BaseModel):
	name: Annotated[str, Path(title="The name of the folder for this run.")]
	journal_family: Annotated[str, Path(title="The Journal Family that EXSCLAIM should look through.")] = "Nature"
	maximum_scraped: Annotated[int, Path(title="The maximum number of articles that EXSCLAIM should scrape. Maximum does not specify how many articles will be scraped before the process ends, only what the upper limit is.", ge=1)] = 5
	sortby: Annotated[Literal["relevant", "recent"], Path(title="How the search feature should sort the articles, by the relevancy or the recent publish date.")] = "relevant"
	term: Annotated[str, Path(title="The term or phrase that you want searched.")]
	synonyms: Annotated[list[str], Path(title="Any synonyms that you're term might be related to.")] = []
	save_format: Annotated[list[Literal["subfigures", "visualization", "boxes", "postgres", "csv", "mongo"]],
	Path(title="How the results should be saved.")] = ["boxes", "postgres"]
	open_access: Annotated[bool, Path(title="Determines if EXSCLAIM only uses open-access articles (True).")] = False
	llm: Annotated[str,	Path(title="The Large Language Model (LLM) that is used to separate captions and generate keywords for articles and figures.")] = "llama3.2"
	model_key: Annotated[str, Path(title="The API key that might be needed depending on the specified llm.")] = ""
	emails: Annotated[list[str], Path(title="The email address that will receive a notification when EXSCLAIM has finished running.")] = []
	ntfy: Annotated[list[NTFY], Path(title="A list of NTFY links that will receive a notification when EXSCLAIM has finished running.")] = []

	@field_validator("llm", mode="before")
	@classmethod
	def validate_llm(cls, llm: str) -> str:
		"""Checks if the given LLM is valid."""
		llm_lower = llm.lower()
		for name, (_, needs_api_key, label) in LLM:
			if llm_lower == name.lower() or (label is not None and label.lower() == llm_lower):
				return name
		raise ValidationError(f"LLM \"{llm}\" is not a valid LLM model.")

	@field_validator("journal_family", mode="before")
	@classmethod
	def validate_journal_family(cls, journal: str) -> str:
		"""Checks if the given journal is valid."""
		journal_lower = journal.lower()
		for name, subclass in JournalFamily:
			if journal_lower == name.lower() or journal_lower == subclass.name().lower():
				return name
		raise ValidationError(f"Journal \"{journal}\" is not a valid journal family.")
