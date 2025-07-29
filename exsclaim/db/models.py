from sqlalchemy import Column, String, ARRAY, ForeignKeyConstraint
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional
from uuid import UUID


__all__ = ["ExsclaimSQLModel", "Article", "Figure", "Subfigure", "Scale", "SubfigureLabel", "ScaleLabel",
		   "ClassificationCodes"]


class ExsclaimSQLModel(SQLModel):
	run_id: UUID = Field(
		primary_key=True,
		nullable=False,
		description="The unique run ID that this article is attached to.",
	)

	@classmethod
	async def get_items(cls, results_id:UUID, session: AsyncSession) -> list["ExsclaimSQLModel"]:
		statement = select(cls).where(cls.run_id == results_id)
		results = await session.exec(statement)
		return results.all()

	@classmethod
	async def get_item(cls, results_id:UUID, _id:str, session: AsyncSession):
		statement = select(cls).where(cls.id == _id).where(cls.run_id == results_id)
		results = await session.exec(statement)
		return results.scalar_one_or_none()


class ClassificationCodes(SQLModel, table=True):
	__tablename__ = "classification_codes"

	code:str = Field(
		primary_key=True,
		min_length=2,
		max_length=2,
		nullable=False,
		description="The name of the classification code.",
	)
	name:str = Field(
		nullable=False,
		max_length=12,
		description="The name of the classification code."
	)


class Article(ExsclaimSQLModel, table=True):
	__tablename__ = "article"
	__table_args__ = dict(schema="results")

	id: str = Field(
		primary_key=True,
		max_length=32,
		nullable=False,
		description="The id of the article. Typically, its the url path without the domain name."
	)
	title:str = Field(
		nullable=False,
		description="The description of the article."
	)
	url:str = Field(
		max_length=200,
		nullable=False,
		description="The url to reach the article."
	)
	license: Optional[str] = Field(
		default=None,
		nullable=True,
		max_length=200,
		description="The article's license url."
	)
	open: bool = Field(
		default=False,
		description="If the article is open access."
	)
	authors: list[str] = Field(
		default=None,
		description="The authors of the article.",
		sa_column=Column(ARRAY(String))
	)
	abstract: Optional[str] = Field(
		default=None,
		description="The abstract for the article."
	)


class Figure(ExsclaimSQLModel, table=True):
	__tablename__ = "figure"
	__table_args__ = (
		ForeignKeyConstraint(["run_id", "article_id"], ["results.article.run_id", "results.article.id"], ondelete="CASCADE"),
		dict(schema="results")
	)

	id: str = Field(
		max_length=40,
		primary_key=True,
		nullable=False,
		description="The id of the figure. Typically, its the id of the article that the figure came from followed by the images number within the article."
	)
	caption: str = Field(
		nullable=False,
		description="The caption of the figure."
	)
	caption_delimiter: Optional[str] = Field(
		max_length=12,
		description="The delimiter used to separate captions."
	)
	url: str = Field(
		max_length=200,
		nullable=False,
		description="The url to reach the raw figure."
	)
	figure_path: str = Field(
		max_length=100,
		nullable=False,
		description="The path to the figure in the results directory."
	)
	article_id: str = Field(
		nullable=False,
		max_length=32
	)


class Subfigure(ExsclaimSQLModel, table=True):
	__tablename__ = "subfigure"
	__table_args__ = (
		ForeignKeyConstraint(["run_id", "figure_id"], ["results.figure.run_id", "results.figure.id"], ondelete="CASCADE"),
		dict(schema="results")
	)

	id: str = Field(
		max_length=44,
		nullable=False,
		primary_key=True,
		description="The id of the figure. Typically, its the id of the article that the figure came from followed by the images number within the article."
	)
	classification_code: str = Field(
		max_length=2,
		foreign_key="classification_codes.code",
		description="The classification code.",
		nullable=False
	)
	height: Optional[float]
	width: Optional[float]
	nm_height: Optional[float]
	nm_width: Optional[float]
	x1: int
	y1: int
	x2: int
	y2: int
	caption: Optional[str]
	keywords: Optional[list[str]] = Field(
		default=None,
		description="The keywords related to the subfigure.",
		sa_column=Column(ARRAY(String))
	)
	figure_id: str = Field(
		nullable=False,
		max_length=40
	)


class Scale(ExsclaimSQLModel, table=True):
	__tablename__ = "scale"
	__table_args__ = (
		ForeignKeyConstraint(["run_id", "subfigure_id"], ["results.subfigure.run_id", "results.subfigure.id"], ondelete="CASCADE"),
		dict(schema="results")
	)

	id: str = Field(
		max_length=48,
		nullable=False,
		primary_key=True,
		description="The id of the figure. Typically, its the id of the article that the figure came from followed by the images number within the article."
	)
	x1: int
	y1: int
	x2: int
	y2: int
	length: Optional[int] = Field(
		default=None,
		nullable=True,
	)
	label_line_distance: Optional[float] = Field(# TODO: Make this DOUBLE PRECISION
		default=None,
		nullable=True,
	)
	confidence: Optional[float] = Field(# TODO: Make this DOUBLE PRECISION
		default=None,
		nullable=True,
	)
	subfigure_id: str = Field(
		nullable=False,
		max_length=44
	)


class SubfigureLabel(ExsclaimSQLModel, table=True):
	__tablename__ = "subfigurelabel"
	__table_args__ = (
		ForeignKeyConstraint(["run_id", "subfigure_id"], ["results.subfigure.run_id", "results.subfigure.id"], ondelete="CASCADE"),
		dict(schema="results")
	)

	text: str = Field(
		max_length=15,
		nullable=False,
	)
	x1: int
	y1: int
	x2: int
	y2: int
	label_confidence: Optional[float] = Field(# TODO: Make this DOUBLE PRECISION
		default=None,
		nullable=True,
	)
	box_confidence: Optional[float] = Field(# TODO: Make this DOUBLE PRECISION
		default=None,
		nullable=True,
	)
	subfigure_id: str = Field(
		nullable=False,
		primary_key=True,
		max_length=44
	)


class ScaleLabel(ExsclaimSQLModel, table=True):
	__tablename__ = "scalelabel"
	__table_args__ = (
		ForeignKeyConstraint(["run_id", "scale_bar_id"], ["results.scale.run_id", "results.scale.id"], ondelete="CASCADE"),
		dict(schema="results")
	)

	text: str = Field(
		max_length=15,
		nullable=False,
	)
	x1: int
	y1: int
	x2: int
	y2: int
	label_confidence: Optional[float] = Field(
		default=None,
		nullable=True,
	)
	box_confidence: Optional[float] = Field(
		default=None,
		nullable=True,
	)
	nm: Optional[float] = Field(
		default=None,
		nullable=True,
	)
	scale_bar_id: str = Field(
		nullable=False,
		primary_key=True,
		max_length=48
	)
