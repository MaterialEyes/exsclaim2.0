from ..models import *
from .users import CurrentUser
from ...db import get_db_session

from fastapi import APIRouter, status, HTTPException
from re import findall
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Callable, Optional
from uuid import UUID

__all__ = ["router", "get_items_responses", "articles", "figures", "subfigures", "article", "figure", "subfigure"]

router = APIRouter(prefix="/results/v1")
TAG = "Results from Queries"


async def check_run_owner(user: User, session: AsyncSession, results_id: UUID, cls: Type[ExsclaimSQLModel]):
	query = await session.execute(select(Results).where(Results.id == results_id))
	results: Optional[Results] = query.scalar_one_or_none()

	if not User.has_permission(user, results):
		match = findall(r"([A-Z][a-z]+)", cls.__name__)
		if match:
			description = " ".join(match).capitalize()
		else:
			description = cls.__name__

		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{description}s not found.")


async def get_item(cls, results_id: UUID, _id: str, user: User, error_msg: Callable[[str], str]):
	async with get_db_session() as session:
		await check_run_owner(user, session, results_id, cls)

		statement = select(cls).where(cls.id == _id).where(cls.run_id == results_id)
		results = await session.execute(statement)
		item = results.scalar_one_or_none()

	if item is not None:
		return item

	return dict(message=error_msg(_id), status_code=status.HTTP_404_NOT_FOUND, media_type="application/json")


async def get_items(cls, results_id: UUID, user: User, page: Optional[int] = None):
	async with get_db_session() as session:
		await check_run_owner(user, session, results_id, cls)

		statement = select(cls).where(cls.run_id == results_id)
		if isinstance(page, int) and page != -1:
			statement = statement.limit(50).offset(page * 50)
		query = await session.execute(statement)
		return query.scalars().all()


def get_items_responses(_type: str, description_word: str, example: list[dict[str, Any]]):
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
@router.api_route("/{results_id}/articles", methods=["GET", "HEAD"], tags=[TAG], response_model=list[Article],
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
async def articles(results_id: UUID, user: CurrentUser):
	return await get_items(Article, results_id, user)


@router.api_route("/{results_id}/figures", methods=["GET", "HEAD"], tags=[TAG], response_model=list[Figure],
			responses=get_items_responses("Figure", "figures", []))
async def figures(results_id: UUID, user: CurrentUser, page=None):
	return await get_items(Figure, results_id, user, page)


@router.api_route("/{results_id}/subfigures", methods=["GET", "HEAD"], tags=[TAG], response_model=list[Subfigure],
			responses=get_items_responses("Subfigure", "subfigures", []))
async def subfigures(results_id: UUID, user: CurrentUser, page=None):
	return await get_items(Subfigure, results_id, user)


@router.api_route("/{results_id}/scales", methods=["GET", "HEAD"], tags=[TAG], response_model=list[Scale],
			responses=get_items_responses("Scale", "scales", []))
async def scales(results_id: UUID, user: CurrentUser):
	return await get_items(Scale, results_id, user)


@router.api_route("/{results_id}/subfigure_labels", methods=["GET", "HEAD"], tags=[TAG], response_model=list[SubfigureLabel],
			responses=get_items_responses("SubfigureLabel", "subfigure labels", []))
async def subfigure_labels(results_id: UUID, user: CurrentUser):
	return await get_items(SubfigureLabel, results_id, user)


@router.api_route("/{results_id}/scale_labels", methods=["GET", "HEAD"], tags=[TAG], response_model=list[ScaleLabel],
			responses=get_items_responses("ScaleLabel", "scale labels", []))
async def scale_labels(results_id: UUID, user: CurrentUser):
	return await get_items(ScaleLabel, results_id, user)
# endregion


# region Individual Objects
@router.api_route("/{results_id}/articles/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=Article,
			responses=get_item_responses("Article", "article"))
async def article(results_id: UUID, id: str, user: CurrentUser):
	return await get_item(Article, results_id, id, user, "No Article with id: {}".format)


@router.api_route("/{results_id}/figures/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=Figure,
			responses=get_item_responses("Figure", "figure", []))
async def figure(results_id: UUID, id: str, user: CurrentUser):
	return await get_item(Figure, results_id, id, user, "No Figure with id: {}".format)


@router.api_route("/{results_id}/subfigures/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=Subfigure,
			responses=get_item_responses("Subfigure", "subfigure", []))
async def subfigure(results_id: UUID, id: str, user: CurrentUser):
	return await get_item(Subfigure, results_id, id, user, "No Subfigure with id: {}".format)


@router.api_route("/{results_id}/scales/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=Scale,
			responses=get_item_responses("Scale", "scale", []))
async def scale(results_id: UUID, id: str, user: CurrentUser):
	return await get_item(Scale, results_id, id, user, "No Scale with id: {}".format)


@router.api_route("/{results_id}/subfigure_labels/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=SubfigureLabel,
			responses=get_item_responses("SubfigureLabel", "subfigure label", []))
async def subfigure_label(results_id: UUID, id: str, user: CurrentUser):
	return await get_item(SubfigureLabel, results_id, id, user, "No SubfigureLabel with id: {}".format)


@router.api_route("/{results_id}/scale_labels/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=ScaleLabel,
			responses=get_item_responses("ScaleLabel", "scale label", []))
async def scale_label(results_id: UUID, id: str, user: CurrentUser):
	return await get_item(ScaleLabel, results_id, id, user, "No ScaleLabel with id: {}".format)
# endregion
