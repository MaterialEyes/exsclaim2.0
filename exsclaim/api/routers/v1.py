from ..models import *

from fastapi import APIRouter
from starlette.responses import JSONResponse
from starlette.requests import Request
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Any, Callable
from uuid import UUID

__all__ = ["router", "get_items_responses", "articles", "figures", "subfigures", "article", "figure", "subfigure"]

router = APIRouter()
DJANGO_COMPATIBILITY = "Django API Backwards Compatibility"


async def get_item(cls, results_id:UUID, _id:str, session: AsyncSession, error_msg:Callable[[str], str]):
	item = await cls.get_item(results_id, _id, session)

	if item is not None:
		return item

	return JSONResponse(dict(message=error_msg(_id), status_code=404, media_type="application/json"))


def get_items_responses(_type:str, description_word:str, example:list[dict[str, Any]]):
	return {
		200: {
			"description": f"All saved {description_word}.",
			"content": {
				"application/json": {
					"schema": {
						"type": "array",
						"items": {
							"type": "object",
							"$ref": f"#/components/schemas/{_type}",
						},
					},
					"example": example
				},
			}
		}
	}


def get_item_responses(*args, **kwargs):
	return {
		200: {
			"description": "The article was found and sent to the user.",
			"content": {
				"application/json": {
					"schema": {
						"type": "object",
						"$ref": "#/components/schemas/Article",
					},
					"example":
						{
							"id": "s41467-024-50040-6",
							"title": "Offshore wind and wave energy can reduce total installed capacity required in zero-emissions grids | Nature Communications",
							"url": "https://www.nature.com/articles/s41467-024-50040-6",
							"license": "http://creativecommons.org/licenses/by/4.0/",
							"open": True,
							"authors": "Natalia Gonzalez, Paul Serna-Torre, Pedro A. Sánchez-Pérez, Ryan Davidson, Bryan Murray, Martin Staadecker, Julia Szinai, Rachel Wei, Daniel M. Kammen, Deborah A. Sunter, Patricia Hidalgo-Gonzalez ",
							"abstract": "As the world races to decarbonize power systems to mitigate climate change, the body of research analyzing paths to zero emissions electricity grids has substantially grown. Although studies typically include commercially available technologies, few of them consider offshore wind and wave energy as contenders in future zero-emissions grids. Here, we model with high geographic resolution both offshore wind and wave energy as independent technologies with the possibility of collocation in a power system capacity expansion model of the Western Interconnection with zero emissions by 2050. In this work, we identify cost targets for offshore wind and wave energy to become cost effective, calculate a 17% reduction in total installed capacity by 2050 when offshore wind and wave energy are fully deployed, and show how curtailment, generation, and transmission change as offshore wind and wave energy deployment increase."
						}
				},
			}
		},
		404: {
			"description": "ID Not Found.",
			"content": {
				"application/json": {
					"schema": {
						"type": "object",
						"properties": {
							"message": {
								"type": "string"
							}
						}

					},
					"example": {
						"message": f"No article with id: s41467-024-50040-61."
					}
				}
			}
		},
	}


# region Lists of Objects
@router.get("/{results_id}/articles", tags=[DJANGO_COMPATIBILITY], response_model=list[Article],
		 responses=get_items_responses("Article", "articles", [
			 {
				 "id": "s41467-024-50040-6",
				 "title": "Offshore wind and wave energy can reduce total installed capacity required in zero-emissions grids | Nature Communications",
				 "url": "https://www.nature.com/articles/s41467-024-50040-6",
				 "license": "http://creativecommons.org/licenses/by/4.0/",
				 "open": "true",
				 "authors": "null",
				 "abstract": "null"
			 },
			 {
				 "id": "s41560-024-01492-z",
				 "title": "Impact of global heterogeneity of renewable energy supply on heavy industrial production and green value chains | Nature Energy",
				 "url": "https://www.nature.com/articles/s41560-024-01492-z",
				 "license": "http://creativecommons.org/licenses/by/4.0/",
				 "open": "true",
				 "authors": "null",
				 "abstract": "null"
			 },
			 {
				 "id": "s41560-024-01518-6",
				 "title": "Estimation of useful-stage energy returns on investment for fossil fuels and implications for renewable energy systems | Nature Energy",
				 "url": "https://www.nature.com/articles/s41560-024-01518-6",
				 "license": "http://creativecommons.org/licenses/by/4.0/",
				 "open": "true",
				 "authors": "null",
				 "abstract": "null"
			 }
		 ]))
async def articles(request: Request, results_id:UUID):
	session = request.state.session
	return await Article.get_items(results_id, session)


@router.get("/{results_id}/figures/", tags=[DJANGO_COMPATIBILITY], response_model=list[Figure],
		 responses=get_items_responses("Figure", "figures", []))
async def figures(request: Request, results_id:UUID, page=None):
	session = request.state.session
	return await Figure.get_items(results_id, session)


@router.get("/{results_id}/subfigures/", tags=[DJANGO_COMPATIBILITY], response_model=list[Subfigure],
		 responses=get_items_responses("Subfigure", "subfigures", []))
async def subfigures(request: Request, results_id:UUID, page=None):
	session = request.state.session
	return await Subfigure.get_items(results_id, session)


@router.get("/{results_id}/scales/", tags=[DJANGO_COMPATIBILITY], response_model=list[Scale],
		 responses=get_items_responses("Scale", "scales", []))
async def scales(request: Request, results_id:UUID):
	session = request.state.session
	return await Scale.get_items(results_id, session)


@router.get("/{results_id}/subfigure_labels/", tags=[DJANGO_COMPATIBILITY], response_model=list[SubfigureLabel],
		 responses=get_items_responses("SubfigureLabel", "subfigure labels", []))
async def subfigure_labels(request: Request, results_id:UUID):
	session = request.state.session
	return await SubfigureLabel.get_items(results_id, session)


@router.get("/{results_id}/scale_labels/", tags=[DJANGO_COMPATIBILITY], response_model=list[ScaleLabel],
		 responses=get_items_responses("ScaleLabel", "scale labels", []))
async def scale_labels(request: Request, results_id:UUID):
	session = request.state.session
	return await ScaleLabel.get_items(results_id, session)


@router.get("/{results_id}/articles/{id}", tags=[DJANGO_COMPATIBILITY], response_model=Article,
		 responses=get_item_responses())
async def article(request: Request, results_id:UUID, id:str) -> JSONResponse | SQLModel:
	session = request.state.session
	return await get_item(Article, results_id, id, session, "No article with id: {}.".format)
# endregion


# region Individual Objects
@router.get("/{results_id}/articles/{id}", tags=[DJANGO_COMPATIBILITY], response_model=Article,
			responses=get_item_responses("Article", "articles"))
async def articles(request: Request, results_id:UUID, id:str):
	session = request.state.session
	return await get_item(Article, results_id, id, session, "No Article with id: {}".format)


@router.get("/{results_id}/figures/{id}", tags=[DJANGO_COMPATIBILITY], response_model=Figure,
			responses=get_item_responses("Figure", "figures", []))
async def figures(request: Request, results_id:UUID, id:str):
	session = request.state.session
	return await get_item(Figure, results_id, id, session, "No Figure with id: {}".format)


@router.get("/{results_id}/subfigures/{id}", tags=[DJANGO_COMPATIBILITY], response_model=Subfigure,
			responses=get_item_responses("Subfigure", "subfigures", []))
async def subfigures(request: Request, results_id:UUID, id:str):
	session = request.state.session
	return await get_item(Subfigure, results_id, id, session, "No Subfigure with id: {}".format)


@router.get("/{results_id}/scales/{id}", tags=[DJANGO_COMPATIBILITY], response_model=Scale,
			responses=get_item_responses("Scale", "scales", []))
async def scales(request: Request, results_id:UUID, id:str):
	session = request.state.session
	return await get_item(Scale, results_id, id, session, "No Scale with id: {}".format)


@router.get("/{results_id}/subfigure_labels/{id}", tags=[DJANGO_COMPATIBILITY], response_model=SubfigureLabel,
			responses=get_item_responses("SubfigureLabel", "subfigure labels", []))
async def subfigure_labels(request: Request, results_id:UUID, id:str):
	session = request.state.session
	return await get_item(SubfigureLabel, results_id, id, session, "No SubfigureLabel with id: {}".format)


@router.get("/{results_id}/scale_labels/{id}", tags=[DJANGO_COMPATIBILITY], response_model=ScaleLabel,
			responses=get_item_responses("ScaleLabel", "scale labels", []))
async def scale_labels(request: Request, results_id:UUID, id:str):
	session = request.state.session
	return await get_item(ScaleLabel, results_id, id, session, "No ScaleLabel with id: {}".format)
# endregion
