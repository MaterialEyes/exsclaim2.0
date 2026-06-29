from pathlib import Path
from pydantic import BaseModel, RootModel, Field
from typing import Any, Annotated, TypeVar, Generic


__all__ = ["Output", "OutputV0", "OutputV1"]


class GeometryV0(BaseModel):
	x: Annotated[int, Field(...)]
	y: Annotated[int, Field(...)]


Geometry = list[GeometryV0]
T = TypeVar("T")


class SubfigureLabelV0(BaseModel, Generic[T]):
	text: Annotated[str, Field(...)]
	geometry: Annotated[T, Field(...)]


class MasterImageV0(BaseModel, Generic[T]):
	classification: Annotated[
		str,
		Field(...)
	]
	classification_confidence: Annotated[
		float,
		Field(...)
	]
	confidence: Annotated[
		float,
		Field(...)
	]
	height: Annotated[
		int,
		Field(...)
	]
	width: Annotated[
		int,
		Field(...)
	]
	geometry: Annotated[
		T,
		Field(...)
	]
	subfigure_label: Annotated[
		SubfigureLabelV0[T],
		Field(...)
	]
	scale_bars: list[dict[str, Any]]
	caption: list[dict[str, str]]
	keywords: list[str]


class UnassignedV0(BaseModel, Generic[T]): # TODO: Add the types for Unassigned
	master_images: Annotated[
		list,
		Field(default_factory=list)
	]
	dependent_images: Annotated[
		list,
		Field(default_factory=list)
	]
	inset_images: Annotated[
		list,
		Field(default_factory=list)
	]
	subfigure_labels: Annotated[
		list,
		Field(default_factory=list)
	]
	scale_bar_labels: Annotated[
		list,
		Field(default_factory=list)
	]
	scale_bar_lines: Annotated[
		list,
		Field(default_factory=list)
	]
	captions: Annotated[
		list[str],
		Field(default_factory=list)
	]


class ArticleV0(BaseModel, Generic[T]):
	title: Annotated[
		str,
		Field(default_factory=str),
	]
	authors: Annotated[
		list[str],
		Field(default_factory=list)
	]
	article_url: Annotated[
		str,
		Field(default_factory=str)
	]
	open: Annotated[
		bool,
		Field(...)
	]
	full_caption: Annotated[
		str,
		Field(default_factory=str)
	]
	article_name: Annotated[
		str,
		Field(default_factory=str)
	]
	image_url: Annotated[
		str,
		Field(default_factory=str)
	]
	caption_delimiter: Annotated[
		str,
		Field(default="0")
	] = "0"
	master_images: Annotated[
		list[MasterImageV0[T]],
		Field(...)
	]
	unassigned: Annotated[
		UnassignedV0,
		Field(...)
	]

	figure_name: Annotated[
		str,
		Field(...)
	]
	figure_path: Annotated[
		Path,
		Field(...)
	]


class OutputV0(RootModel[dict[str, ArticleV0[Geometry]]]):
	...
