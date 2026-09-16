from ..models import User, Run
from ..dependencies import CurrentUserId
from ...db import get_db_session

from fastapi import APIRouter, status, HTTPException
from starlette.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel
from typing import Literal, Optional
from uuid import UUID

import enum
import orjson

__all__ = ["router"]

router = APIRouter(prefix="/results/v2")
TAG = "Results from Queries"

SearchLevels = Literal["article", "figure", "subfigure", "subfigure_label", "scale", "scale_label"]


class SearchEnum(enum.IntEnum):
	Article = 0
	Figure = 1
	Subfigure = 2
	SubfigureLabel = 3
	Scale = 4
	ScaleLabel = 5

	@classmethod
	def get_level(cls, level: SearchLevels) -> "SearchEnum":
		try:
			return cls[level.title()]
		except ValueError as e:
			match level.lower():
				case "subfigure_label":
					return cls.SubfigureLabel
				case "scale_label":
					return cls.ScaleLabel
				case _:
					raise e


async def check_run_owner(user: UUID, session: AsyncSession, results_id: UUID, description: str) -> Run:
	query = await session.execute(select(Run).where(Run.id == results_id))
	run: Optional[Run] = query.scalar_one_or_none()

	if run is None or not User.has_permission(user, run):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{description}s not found.")

	return run


# region Lists of Objects
def parse_object(model: SQLModel, model_type: SearchLevels) -> bytes:
	model_json = model.model_dump()
	model_json["type"] = model_type
	try:
		return orjson.dumps(model_json) + b"\n"
	except BaseException as e:
		raise ValueError(f"An error occurred with {model_type=}: {e}") from e


async def dashboard_item_generator(results_id: UUID, user: CurrentUserId, lowest_level: SearchEnum = SearchEnum.Subfigure):
	async with get_db_session() as session:
		run = await check_run_owner(user, session, results_id, "Article")
		for article in await run.articles:
			yield parse_object(article, "article")
			if lowest_level == SearchEnum.Article:
				continue

			for figure in await article.figures:
				yield parse_object(figure, "figure")
				if lowest_level == SearchEnum.Figure:
					continue

				for subfigure in await figure.subfigures:
					if subfigure.run_id != results_id:
						continue

					yield parse_object(subfigure, "subfigure")
					if lowest_level == SearchEnum.Subfigure:
						continue

					for subfig_label in await subfigure.labels:
						yield parse_object(subfig_label, "subfigure_label")

					if lowest_level == SearchEnum.SubfigureLabel:
						continue

					for scale in await subfigure.scales:
						yield parse_object(scale, "scale")
						if lowest_level == SearchEnum.Scale:
							continue

						for scale_label in await scale.labels:
							yield parse_object(scale_label, "scale_label")


@router.api_route("/{results_id}/dashboard", methods=["GET", "HEAD"], tags=[TAG], response_class=StreamingResponse,
				  responses={
					  200: {
						  "description": "The results for the dashboard for a given run.",
						  "content": {
							  "application/x-ndjson": {
								  "itemSchema": {
									  "oneOf": [
										  {
											  "type": "object",
											  "properties": {
												  "type": {"type": "string", "enum": ["article"]},
												  "title": {"type": "string"},
												  "url": {"type": "url"},
												  "open": {"type": "boolean"},
												  "id": {"type": "string"},
												  "abstract": {"type": "string"}
											  },
											  "examples": [
												  {
													  "title": "XPS analysis of polymer brush coatings \nOpen Access",
													  "url": "https://pubs.rsc.org/py/article/doi/10.1039/d6py00562d/1289602/XPS-analysis-of-polymer-brush-coatings",
													  "open": True,
													  "id": "d6py00562d",
													  "license": "https://creativecommons.org/licenses/by/4.0",
													  "abstract": "",
													  "type": "article"
												  }
											  ]
										  },
										  {
											  "type": "object",
											  "properties": {
												  "caption": {"type": "string"},
												  "url": {"type": "string"},
												  "article_id": {"type": "string"},
												  "id": {"type": "string"},
												  "figure_path": {"type": "string"},
												  "type": {"type": "string"},
											  },
											  "examples": [
												  {
													  "caption": "XPS examines the near-surface region of organic films. This tutorial covers XPS analysis of polymer-brush coatings: sample preparation, charge referencing, survey quantification, C 1s fitting, depth profiling, and DFT-assisted peak assignment.",
													  "url": "https://rscj.silverchair-cdn.com/rscj/content_public/journal/py/pap/10.1039_d6py00562d/1/d6py00562d-ga.png?Expires=1790613731&Signature=TuFk4jmVJlX~zLw3E5dGdvunnKLz1QI0bm6usCA9JD6jej3dqRzKfou97NmaOiN2JZ~wkWzHSBaSCRNeIpsbvHks51~3cC5tJXHmEWid6womoKloUPrj7VzGeXDErrEWVyV8vjf7hMELb0QSK7rgHkkv8IeWqHFg7fPI0LziJlBXiEyGI4mXi~GZEgu5CKpmEua2Mv1aZj2kw1kgyJKCtD1w5Dem~2SUDcdQ5pxMNV8jL8B4MmXp48dSgJcYHWvy1jXJ~sOS6i9a5tsGGiEWGllj2cVR-JvkwvZMS41zpD6oL~Zj2Ji5FC6tsmK9AntDAPynH3mHQmgIAx7IpxFtSw__&Key-Pair-Id=APKAIE5G5CRDK6RD3PGA",
													  "article_id": "d6py00562d",
													  "id": "d6py00562d-fig1",
													  "figure_path": "rsc_test/figures/d6py00562d_fig1.png",
													  "type": "figure"
												  }
											  ]
										  },
										  {
											  "type": "object",
											  "properties": {
												  "height": {"type": "number"},
												  "caption": {"type": "string"},
												  "width": {"type": "number"},
												  "caption_input_tokens": {
													  "type": ["number", "null"],
													  "format": "integer"
												  },
												  "nm_height": {"type": ["number", "null"]},
												  "caption_output_tokens": {
													  "type": ["number", "null"],
													  "format": "integer"
												  },
												  "id": {"type": "string"},
												  "nm_width": {"type": ["number", "null"]},
												  "keywords": {"type": "array"},
												  "run_id": {"type": "string"},
												  "x1": {"type": "number"},
												  "figure_id": {"type": "string"},
												  "classification_code": {"type": "number"},
												  "y1": {"type": "integer"},
												  "classification_confidence": {
													  "type": "number",
													  "format": "float",
													  "maximum": 1.0,
													  "exclusiveMaximum": False,
													  "minimum": 0.0,
													  "exclusiveMinimum": False,
												  },
												  "x2": {"type": "integer"},
												  "confidence": {
													  "type": "number",
													  "format": "float",
													  "maximum": 1.0,
													  "exclusiveMaximum": False,
													  "minimum": 0.0,
													  "exclusiveMinimum": False,
												  },
												  "y2": {"type": "integer"},
												  "type": {"type": "string", "enum": ["subfigure"]},
											  },
											  "examples": [
												  {
													  "height": 282.0,
													  "caption": "showing three main peaks: C 1s, N 1s, and O 1s.",
													  "width": 147.0,
													  "caption_input_tokens": 374,
													  "nm_height": None,
													  "caption_output_tokens": 210,
													  "id": "d6py00562d-fig3-b",
													  "nm_width": None,
													  "keywords": [
														  "XPS",
														  "poly(HPMA)",
														  "X-ray photoelectron spectroscopy",
														  "spectrum",
														  "polymer"
													  ],
													  "run_id": "01a034c4-4523-735e-83d3-68d2c41aab78",
													  "x1": 0,
													  "figure_id": "d6py00562d-fig3",
													  "classification_code": "MC",
													  "y1": 1,
													  "classification_confidence": 0.5288102030754089,
													  "x2": 147,
													  "confidence": 0.6461105942726135,
													  "y2": 283,
													  "type": "subfigure"
												  }
											  ]
										  },
									  ]
								  },
							  }
						  }
					  }
				  })
async def dashboard(results_id: UUID, user: CurrentUserId, lowest_level: SearchLevels = "subfigure"):
	level = SearchEnum.get_level(lowest_level)
	return StreamingResponse(dashboard_item_generator(results_id, user, level), media_type="application/x-ndjson",
							 status_code=200)
