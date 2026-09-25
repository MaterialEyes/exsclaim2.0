from pathlib import Path
from pydantic import BaseModel, RootModel, Field
from typing import Any, TypeVar, Generic


__all__ = ["OutputV0"]


class GeometryV0(BaseModel):
	x: int = Field(...)
	y: int = Field(...)


Geometry = list[GeometryV0]
T = TypeVar("T")


class SubfigureLabelV0(BaseModel, Generic[T]):
	text: str = Field(...)
	geometry: T = Field(...)


class MasterImageV0(BaseModel, Generic[T]):
	classification: str = Field(...)
	classification_confidence: float = Field(...)
	confidence: float = Field(...)
	height: int = Field(...)
	width: int = Field(...)
	geometry: T = Field(...)
	subfigure_label: SubfigureLabelV0[T] = Field(...)
	scale_bars: list[dict[str, Any]]
	caption: list[dict[str, str]]
	keywords: list[str]


class UnassignedV0(BaseModel, Generic[T]): # TODO: Add the types for Unassigned
	master_images: list = Field(default_factory=list)
	dependent_images: list = Field(default_factory=list)
	inset_images: list = Field(default_factory=list)
	subfigure_labels: list = Field(default_factory=list)
	scale_bar_labels: list = Field(default_factory=list)
	scale_bar_lines: list = Field(default_factory=list)
	captions: list[str] = Field(default_factory=list)


class ArticleV0(BaseModel, Generic[T]):
	title: str = Field(default_factory=str)
	authors: list[str] = Field(default_factory=list)
	article_url: str = Field(default_factory=str)
	open: bool = Field(...)
	full_caption: str = Field(default_factory=str)
	article_name: str = Field(default_factory=str)
	image_url: str = Field(default_factory=str)
	caption_delimiter: str = Field(default="0")
	master_images: list[MasterImageV0[T]] = Field(...)
	unassigned: UnassignedV0 = Field(...)
	figure_name: str = Field(...)
	figure_path: Path = Field(...)


class OutputV0(RootModel[dict[str, ArticleV0[Geometry]]]):
	...
