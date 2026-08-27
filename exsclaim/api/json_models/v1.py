from typing import Annotated, Literal
from pydantic import BaseModel, Field

from .v0 import ArticleV0, GeometryV0, MasterImageV0, SubfigureLabelV0, OutputV0

__all__ = ["OutputV1", "migrate_v0_to_v1"]


class GeometryV1(BaseModel):
	x0: int = Field(description="The left boundary of the image.")
	y0: int = Field(description="The upper boundary of the image.")
	x1: int = Field(description="The right boundary of the image.")
	y1: int = Field(description="The bottom boundary of the image.")


ArticleV1 = ArticleV0[GeometryV1]


class OutputV1(BaseModel):
	version: Literal["1.0"] = "1.0"
	results: dict[str, ArticleV1] = Field(...)


def get_coords_from_list(new_list: list[GeometryV0]) -> GeometryV1:
	xs = set(i.x for i in new_list)
	ys = set(i.y for i in new_list)

	return GeometryV1(
		x0=min(xs),
		y0=min(ys),
		x1=max(xs),
		y1=max(ys),
	)


def migrate_v0_to_v1(v0: OutputV0) -> OutputV1:
	results: dict[str, ArticleV0[list[GeometryV0]]] = v0.root
	articles = dict()

	for article_id, article in results.items():
		master_images: list[MasterImageV0[GeometryV1]] = [None] * len(article.master_images)

		for i, master_image in enumerate(article.master_images):
			subfigure_label = SubfigureLabelV0[GeometryV1](
				text=master_image.subfigure_label.text,
				geometry=get_coords_from_list(master_image.subfigure_label.geometry),
			)

			master_images[i] = MasterImageV0[GeometryV1](
				caption=master_image.caption,
				classification=master_image.classification,
				classification_confidence=master_image.classification_confidence,
				confidence=master_image.confidence,
				geometry=get_coords_from_list(master_image.geometry),
				height=master_image.height,
				keywords=master_image.keywords,
				scale_bars=master_image.scale_bars,
				subfigure_label=subfigure_label,
				width=master_image.width,
			)

		articles[article_id] = ArticleV1(
			article_name=article.article_name,
			article_url=article.article_url,
			authors=article.authors,
			caption_delimiter=article.caption_delimiter,
			figure_name=article.figure_name,
			figure_path=article.figure_path,
			full_caption=article.full_caption,
			image_url=article.image_url,
			master_images=master_images,
			open=article.open,
			title=article.title,
			unassigned=article.unassigned,
		)

	return OutputV1(results=articles)
