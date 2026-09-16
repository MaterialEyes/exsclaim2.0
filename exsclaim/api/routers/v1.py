from ..models import Article, Figure, Subfigure, Scale, SubfigureLabel, ScaleLabel, User, Run
from ..dependencies import AcceptHeader, BAD_CONTENT_TYPE_EXCEPTION, CurrentUserId
from ...db import get_db_session

from fastapi import APIRouter, status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, StreamingResponse
from typing import Any, Callable, Optional, Sequence, Type
from uuid import UUID

__all__ = ["router", "get_items_responses", "articles", "figures", "subfigures", "article", "figure", "subfigure"]

router = APIRouter(prefix="/results/v1")
TAG = "Results from Queries"


async def get_run(user: UUID, session: AsyncSession, run_id: UUID, description: str):
	query = await session.execute(select(Run).where(Run.id == run_id))
	run: Optional[Run] = query.scalar_one_or_none()

	if not User.has_permission(user, run):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{description}s not found.")

	return run


async def get_item(cls, run_id: UUID, _id: str, user: UUID, error_msg: Callable[[str], str]):
	async with get_db_session() as session:
		await get_run(user, session, run_id, cls)

		statement = select(cls).where(cls.id == _id).where(cls.run_id == run_id)
		results = await session.execute(statement)
		item = results.scalar_one_or_none()

	if item is not None:
		return item

	return dict(message=error_msg(_id), status_code=status.HTTP_404_NOT_FOUND, media_type="application/json")


async def get_items(cls: Type[Subfigure, Scale, SubfigureLabel, ScaleLabel], run_id: UUID,
					user: UUID, accept: AcceptHeader, page: Optional[int] = None):
	async with get_db_session() as session:
		await get_run(user, session, run_id, cls.__name__)
		query = await session.execute(select(cls).where(cls.run_id == run_id))
		values: Sequence = query.scalars().all()

	media_type, *_ = accept.get_best_option(("application/json", "application/x-ndjson"))
	match media_type:
		case "application/json":
			return values
		case "application/x-ndjson":
			def generator():
				for value in values:
					yield value.model_dump_json() + "\n"

			return StreamingResponse(generator(), media_type=media_type, status_code=200)
		case _:
			raise BAD_CONTENT_TYPE_EXCEPTION


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
						"message": "No article with id: s41467-024-50040-61."
					}
				}
			}
		},
	}


@router.api_route("/{run_id}/articles", methods=["GET", "HEAD"], tags=[TAG], response_model=list[Article],
				  responses=get_items_responses("Article", "articles", [
					  {
						  "url": "https://www.nature.com/articles/s41467-026-72690-4",
						  "open": True,
						  "id": "s41467-026-72690-4",
						  "title": "Amide-engineered copper nitride for shortcut-pathway-locked electroreduction of concentrated hydroxymethylfurfural | Nature Communications",
						  "license": "http://creativecommons.org/licenses/by-nc-nd/4.0/",
						  "abstract": None,
						  "authors": [
							  "Hao Wu",
							  "Jianqiu Zhu",
							  "Shichao Du",
							  "Zhichuan J. Xu",
							  "Zhimin Chen",
							  "Bowen Liu",
							  "Honggang Fu",
							  "Zhiyu Ren",
							  "Chencheng Dai",
							  "Jian-Qiang Wang",
							  "Gang Li",
							  "Ju Huang"
						  ]
					  },
					  {
						  "url": "https://www.nature.com/articles/s41598-025-08421-4",
						  "open": True,
						  "id": "s41598-025-08421-4",
						  "title": "XPS study and electronic structure of non-doped and Cr+ ion implanted CuO thin films | Scientific Reports",
						  "license": "http://creativecommons.org/licenses/by/4.0/",
						  "abstract": None,
						  "authors": [
							  "Denis A. Pikulski",
							  "Konstanty W. Marszalek",
							  "Aurelian C. Galca",
							  "Zbigniew Kąkol",
							  "Waldemar Tokarz",
							  "Katarzyna Ungeheuer",
							  "Amelia E. Bocirnea"
						  ]
					  },
					  {
						  "url": "https://www.nature.com/articles/s41598-026-61978-6",
						  "open": True,
						  "id": "s41598-026-61978-6",
						  "title": "Synthesis of methyldopa-copper nanoparticles with laccase mimics activity for colorimetric detection of norepinephrine | Scientific Reports",
						  "license": "http://creativecommons.org/licenses/by/4.0/",
						  "abstract": None,
						  "authors": [
							  "Amr M. Mahmoud",
							  "Jeffrey G. Bell",
							  "Aya A. Mouhamed",
							  "Ola G. Hussein"
						  ]
					  }
				  ]))
async def articles(run_id: UUID, user: CurrentUserId):
	async with get_db_session() as session:
		run = await get_run(user, session, run_id, "Article")
		return await run.articles


@router.api_route("/{run_id}/figures", methods=["GET", "HEAD"], tags=[TAG],
				responses={
					200: {
						"description": "All saved figures for the given run.",
						"content": {
							"application/json": {
								"schema": {
									"type": "array",
									"items": {
										"type": "object",
										"$ref": "#/components/schemas/Figure",
									},
								},
								"examples": [
									[
										{
											"id": "s41467-026-72690-4-fig1",
											"figure_path": "webhook_test/figures/s41467-026-72690-4_fig1.png",
											"caption": "<p><b>a</b> Schematic illustration of synthetic route for Ami-Cu<sub>3</sub>N/CF via nanowire-templated growth, ligand-driven MOF conversion, and concurrent nitridation and amidation. <b>b</b> XRD patterns of Ami-Cu<sub>3</sub>N/CF, BTC-Cu/CF, Cu<sub>3</sub>N/CF, Cu(OH)<sub>2</sub>/CF and Cu/CF. Red triangles, black symbols and yellow stars denote Cu<sub>3</sub>N, Cu(OH)<sub>2</sub> and Cu phases, respectively. <b>c</b>, <b>d</b> SEM image of Ami-Cu<sub>3</sub>N/CF. <b>e</b> TEM image of Ami-Cu<sub>3</sub>N/CF. <b>f</b>, <b>g</b> high-resolution TEM images of Ami-Cu<sub>3</sub>N/CF exfoliated from CF. <b>h</b> HAADF-STEM image and corresponding elemental mapping images of Cu (yellow), N (green) and C (red) for Ami-Cu<sub>3</sub>N/CF exfoliated from CF. Source data for <b>b</b> are provided as a Source Data file.</p>",
											"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-026-72690-4/MediaObjects/41467_2026_72690_Fig1_HTML.png",
											"article_id": "s41467-026-72690-4"
										},
										{
											"id": "s41467-026-72690-4-fig2",
											"figure_path": "webhook_test/figures/s41467-026-72690-4_fig2.png",
											"caption": "<p><b>a</b> Cu <i>2p</i> XPS spectra and <b>b</b> Cu <i>LMM</i> auger spectra of Ami-Cu<sub>3</sub>N/CF, Cu<sub>3</sub>N/CF and Cu/CF. <b>c</b> Cu K-edge XANES spectra and <b>d</b> corresponding Fourier-transformed EXAFS spectra of Ami-Cu<sub>3</sub>N, Cu<sub>3</sub>N and BTC-Cu, with Cu foil, Cu<sub>2</sub>O and CuO as reference compounds. The dashed lines indicate the main scattering features corresponding to Cu–N and Cu–Cu coordination. <b>e</b> Wavelet transform EXAFS spectra of Ami-Cu<sub>3</sub>N, BTC-Cu, Cu<sub>3</sub>N and Cu. <b>f</b> N <i>1</i><i>s</i> XPS spectra of Ami-Cu<sub>3</sub>N/CF and Cu<sub>3</sub>N/CF. <b>g</b> N K-edge XANES spectra of Ami-Cu<sub>3</sub>N and Cu<sub>3</sub>N. <b>h</b> XPS valence band spectra of Ami-Cu<sub>3</sub>N/CF, Cu<sub>3</sub>N/CF and Cu/CF. Source data for <b>a</b>–<b>h</b> are provided as a Source Data file.</p>",
											"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-026-72690-4/MediaObjects/41467_2026_72690_Fig2_HTML.png",
											"article_id": "s41467-026-72690-4"
										},
										{
											"id": "s41467-026-72690-4-fig3",
											"figure_path": "webhook_test/figures/s41467-026-72690-4_fig3.png",
											"caption": "<p><b>a</b> Schematic illustration of the HMF electrocatalytic hydrogenation (ECH) system in a custom-built flow cell, where CE, WE, RE and PEM denote the counter electrode, working electrode, reference electrode and proton exchange membrane, respectively. <b>b</b> HPLC traces of HMF ECH over Ami-Cu<sub>3</sub>N/CF at −100 mA cm<sup>−2</sup> in 0.5 M PBS with 100 mM HMF. <b>c</b> FE<sub>DHMF</sub> and corresponding potential over Ami-Cu<sub>3</sub>N/CF, Cu<sub>3</sub>N/CF and Cu/CF at current densities from −200 to −600 mA cm<sup>−2</sup> (0.5 M PBS with 200 mM HMF, total charge of 3859 C). <b>d</b> FE<sub>DHMF</sub> and DHMF productivity over Ami-Cu<sub>3</sub>N/CF, Cu<sub>3</sub>N/CF, and Cu/CF at different HMF concentrations (0.5 M PBS with 500 mM HMF at −500 mA cm<sup>−2</sup>, 0.5 M PBS with 1000 mM HMF at −600 mA cm<sup>−2</sup>). <b>e</b> Time-dependent evolution of HMF and DHMF concentrations during HMF ECH over Ami-Cu<sub>3</sub>N/CF in a custom-built flow cell. <b>f</b> FE<sub>DHMF</sub> and DHMF productivity over Ami-Cu<sub>3</sub>N/CF under different times in 0.5 M PBS with 200 mM HMF in a custom-built flow cell. Unless otherwise specified, all electrochemical measurements were conducted at room temperature (~25 °C) in 0.5 M PBS (pH ~7.0) using a 1 cm<sup>2</sup> geometric electrode area without electrode rotation or gas flow, all potentials are referenced to RHE, with LSV measurements performed using 95% iR compensation and CA/CP data collected without real-time iR correction, and the uncompensated solution resistance (Rs) ranged from 2.5 to 4.8 Ω cm<sup>2</sup>. Source data for <b>b</b>–<b>f</b> are provided as a Source Data file.</p>",
											"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-026-72690-4/MediaObjects/41467_2026_72690_Fig3_HTML.png",
											"article_id": "s41467-026-72690-4"
										}
									]
								]
							},
							"application/x-ndjson": {
								"itemSchema": {
									"type": "array",
									"items": {
										"type": "object",
										"$ref": "#/components/schemas/Figure",
									},
								},
								"examples": [
									[
										{
											"id": "s41467-026-72690-4-fig1",
											"figure_path": "webhook_test/figures/s41467-026-72690-4_fig1.png",
											"caption": "<p><b>a</b> Schematic illustration of synthetic route for Ami-Cu<sub>3</sub>N/CF via nanowire-templated growth, ligand-driven MOF conversion, and concurrent nitridation and amidation. <b>b</b> XRD patterns of Ami-Cu<sub>3</sub>N/CF, BTC-Cu/CF, Cu<sub>3</sub>N/CF, Cu(OH)<sub>2</sub>/CF and Cu/CF. Red triangles, black symbols and yellow stars denote Cu<sub>3</sub>N, Cu(OH)<sub>2</sub> and Cu phases, respectively. <b>c</b>, <b>d</b> SEM image of Ami-Cu<sub>3</sub>N/CF. <b>e</b> TEM image of Ami-Cu<sub>3</sub>N/CF. <b>f</b>, <b>g</b> high-resolution TEM images of Ami-Cu<sub>3</sub>N/CF exfoliated from CF. <b>h</b> HAADF-STEM image and corresponding elemental mapping images of Cu (yellow), N (green) and C (red) for Ami-Cu<sub>3</sub>N/CF exfoliated from CF. Source data for <b>b</b> are provided as a Source Data file.</p>",
											"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-026-72690-4/MediaObjects/41467_2026_72690_Fig1_HTML.png",
											"article_id": "s41467-026-72690-4"
										},
										{
											"id": "s41467-026-72690-4-fig2",
											"figure_path": "webhook_test/figures/s41467-026-72690-4_fig2.png",
											"caption": "<p><b>a</b> Cu <i>2p</i> XPS spectra and <b>b</b> Cu <i>LMM</i> auger spectra of Ami-Cu<sub>3</sub>N/CF, Cu<sub>3</sub>N/CF and Cu/CF. <b>c</b> Cu K-edge XANES spectra and <b>d</b> corresponding Fourier-transformed EXAFS spectra of Ami-Cu<sub>3</sub>N, Cu<sub>3</sub>N and BTC-Cu, with Cu foil, Cu<sub>2</sub>O and CuO as reference compounds. The dashed lines indicate the main scattering features corresponding to Cu–N and Cu–Cu coordination. <b>e</b> Wavelet transform EXAFS spectra of Ami-Cu<sub>3</sub>N, BTC-Cu, Cu<sub>3</sub>N and Cu. <b>f</b> N <i>1</i><i>s</i> XPS spectra of Ami-Cu<sub>3</sub>N/CF and Cu<sub>3</sub>N/CF. <b>g</b> N K-edge XANES spectra of Ami-Cu<sub>3</sub>N and Cu<sub>3</sub>N. <b>h</b> XPS valence band spectra of Ami-Cu<sub>3</sub>N/CF, Cu<sub>3</sub>N/CF and Cu/CF. Source data for <b>a</b>–<b>h</b> are provided as a Source Data file.</p>",
											"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-026-72690-4/MediaObjects/41467_2026_72690_Fig2_HTML.png",
											"article_id": "s41467-026-72690-4"
										},
										{
											"id": "s41467-026-72690-4-fig3",
											"figure_path": "webhook_test/figures/s41467-026-72690-4_fig3.png",
											"caption": "<p><b>a</b> Schematic illustration of the HMF electrocatalytic hydrogenation (ECH) system in a custom-built flow cell, where CE, WE, RE and PEM denote the counter electrode, working electrode, reference electrode and proton exchange membrane, respectively. <b>b</b> HPLC traces of HMF ECH over Ami-Cu<sub>3</sub>N/CF at −100 mA cm<sup>−2</sup> in 0.5 M PBS with 100 mM HMF. <b>c</b> FE<sub>DHMF</sub> and corresponding potential over Ami-Cu<sub>3</sub>N/CF, Cu<sub>3</sub>N/CF and Cu/CF at current densities from −200 to −600 mA cm<sup>−2</sup> (0.5 M PBS with 200 mM HMF, total charge of 3859 C). <b>d</b> FE<sub>DHMF</sub> and DHMF productivity over Ami-Cu<sub>3</sub>N/CF, Cu<sub>3</sub>N/CF, and Cu/CF at different HMF concentrations (0.5 M PBS with 500 mM HMF at −500 mA cm<sup>−2</sup>, 0.5 M PBS with 1000 mM HMF at −600 mA cm<sup>−2</sup>). <b>e</b> Time-dependent evolution of HMF and DHMF concentrations during HMF ECH over Ami-Cu<sub>3</sub>N/CF in a custom-built flow cell. <b>f</b> FE<sub>DHMF</sub> and DHMF productivity over Ami-Cu<sub>3</sub>N/CF under different times in 0.5 M PBS with 200 mM HMF in a custom-built flow cell. Unless otherwise specified, all electrochemical measurements were conducted at room temperature (~25 °C) in 0.5 M PBS (pH ~7.0) using a 1 cm<sup>2</sup> geometric electrode area without electrode rotation or gas flow, all potentials are referenced to RHE, with LSV measurements performed using 95% iR compensation and CA/CP data collected without real-time iR correction, and the uncompensated solution resistance (Rs) ranged from 2.5 to 4.8 Ω cm<sup>2</sup>. Source data for <b>b</b>–<b>f</b> are provided as a Source Data file.</p>",
											"url": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-026-72690-4/MediaObjects/41467_2026_72690_Fig3_HTML.png",
											"article_id": "s41467-026-72690-4"
										}
									]
								]
							},
						}
					}
				})
async def figures(run_id: UUID, user: CurrentUserId, accept: AcceptHeader, page=None):
	async def figure_generator(stream: bool = False):
		async with get_db_session() as session:
			run = await get_run(user, session, run_id, "Figure")
			for article in await run.articles:
				for figure in await article.figures:
					if stream:
						yield figure.model_dump_json() + "\n"
					else:
						yield figure.model_dump()

	media_type, *_ = accept.get_best_option(("application/json", "application/x-ndjson"))
	match media_type:
		case "application/json":
			figures = [figure async for figure in figure_generator(stream=False)]
			return JSONResponse(figures, media_type=media_type, status_code=200)
		case "application/x-ndjson":
			return StreamingResponse(figure_generator(stream=True), media_type=media_type, status_code=200)
		case _:
			raise BAD_CONTENT_TYPE_EXCEPTION


@router.api_route("/{run_id}/subfigures", methods=["GET", "HEAD"], tags=[TAG],
				responses={
					200: {
						"description": "All saved subfigures for the given run.",
						"content": {
							"application/json": {
								"schema": {
									"type": "array",
									"items": {
										"type": "object",
										"$ref": "#/components/schemas/Subfigure",
									},
								},
								"example": [
									{
										"id": "s41598-026-61978-6-fig6-a",
										"nm_width": None,
										"keywords": [
											"Nanoparticles",
											"Oxidation",
											"Catalysis",
											"Kinetics",
											"Michaelis-Menten"
										],
										"run_id": "019fecd9-fe81-728f-be85-e856db6548b9",
										"x1": 0,
										"figure_id": "s41598-026-61978-6-fig6",
										"classification_code": "GR",
										"y1": 0,
										"classification_confidence": 0.9940880537033081,
										"x2": 1064,
										"confidence": 0.9655985236167908,
										"y2": 860,
										"height": 860,
										"caption": "<p>(<b>a</b>) Time-dependent oxidation of norepinephrine catalyzed by PMD-Cu NPs under the optimized experimental conditions (phosphate buffer, pH 6.0, 40 °C).</p>",
										"width": 1064,
										"caption_input_tokens": 405,
										"nm_height": None,
										"caption_output_tokens": 221
									},
									{
										"id": "s41467-025-65314-w-fig1-b",
										"nm_width": None,
										"keywords": [
											"La2CuO4",
											"X-ray spectroscopy",
											"Auger decay",
											"Oxygen K-shell ionization"
										],
										"run_id": "019fecd9-fe81-728f-be85-e856db6548b9",
										"x1": 312,
										"figure_id": "s41467-025-65314-w-fig1",
										"classification_code": "IL",
										"y1": 14,
										"classification_confidence": 0.9603189826011658,
										"x2": 611,
										"confidence": 0.933527410030365,
										"y2": 665,
										"height": 651,
										"caption": "Structure and surface termination of tetragonal La<sub>2</sub>CuO<sub>4</sub>: Octahedral coordination (blue polygons) of Copper atoms (grey) to six lattice oxygen atoms O<sub>latt.</sub> (red). The surface layer (right hand side) contains under-coordinated surface oxygen species O<sub>ad.</sub> (light orange).",
										"width": 299,
										"caption_input_tokens": 573,
										"nm_height": None,
										"caption_output_tokens": 403
									},
									{
										"id": "s41467-025-65314-w-fig1-a",
										"nm_width": None,
										"keywords": [
											"La2CuO4",
											"X-ray spectroscopy",
											"Auger decay",
											"Oxygen K-shell ionization"
										],
										"run_id": "019fecd9-fe81-728f-be85-e856db6548b9",
										"x1": 4,
										"figure_id": "s41467-025-65314-w-fig1",
										"classification_code": "GR",
										"y1": 12,
										"classification_confidence": 0.4316732585430145,
										"x2": 268,
										"confidence": 0.8992604613304138,
										"y2": 660,
										"height": 648,
										"caption": "The on-site oxygen 2<i>p</i> two-hole state is prepared and detected via coincidences of oxygen 1<i>s</i> (K-shell) ionization and the oxygen <i>KVV</i> Auger decay. LHB and UHB denote lower and upper Hubbard band, respectively.",
										"width": 264,
										"caption_input_tokens": 573,
										"nm_height": None,
										"caption_output_tokens": 403
									},
								]
							},
							"application/x-ndjson": {
								"itemSchema": {
									"type": "array",
									"items": {
										"type": "object",
										"$ref": "#/components/schemas/Subfigure",
									},
								},
								"examples": [
									[
										[
											{
												"id": "s41598-026-61978-6-fig6-a",
												"nm_width": None,
												"keywords": [
													"Nanoparticles",
													"Oxidation",
													"Catalysis",
													"Kinetics",
													"Michaelis-Menten"
												],
												"run_id": "019fecd9-fe81-728f-be85-e856db6548b9",
												"x1": 0,
												"figure_id": "s41598-026-61978-6-fig6",
												"classification_code": "GR",
												"y1": 0,
												"classification_confidence": 0.9940880537033081,
												"x2": 1064,
												"confidence": 0.9655985236167908,
												"y2": 860,
												"height": 860,
												"caption": "<p>(<b>a</b>) Time-dependent oxidation of norepinephrine catalyzed by PMD-Cu NPs under the optimized experimental conditions (phosphate buffer, pH 6.0, 40 °C).</p>",
												"width": 1064,
												"caption_input_tokens": 405,
												"nm_height": None,
												"caption_output_tokens": 221
											},
											{
												"id": "s41467-025-65314-w-fig1-b",
												"nm_width": None,
												"keywords": [
													"La2CuO4",
													"X-ray spectroscopy",
													"Auger decay",
													"Oxygen K-shell ionization"
												],
												"run_id": "019fecd9-fe81-728f-be85-e856db6548b9",
												"x1": 312,
												"figure_id": "s41467-025-65314-w-fig1",
												"classification_code": "IL",
												"y1": 14,
												"classification_confidence": 0.9603189826011658,
												"x2": 611,
												"confidence": 0.933527410030365,
												"y2": 665,
												"height": 651,
												"caption": "Structure and surface termination of tetragonal La<sub>2</sub>CuO<sub>4</sub>: Octahedral coordination (blue polygons) of Copper atoms (grey) to six lattice oxygen atoms O<sub>latt.</sub> (red). The surface layer (right hand side) contains under-coordinated surface oxygen species O<sub>ad.</sub> (light orange).",
												"width": 299,
												"caption_input_tokens": 573,
												"nm_height": None,
												"caption_output_tokens": 403
											},
											{
												"id": "s41467-025-65314-w-fig1-a",
												"nm_width": None,
												"keywords": [
													"La2CuO4",
													"X-ray spectroscopy",
													"Auger decay",
													"Oxygen K-shell ionization"
												],
												"run_id": "019fecd9-fe81-728f-be85-e856db6548b9",
												"x1": 4,
												"figure_id": "s41467-025-65314-w-fig1",
												"classification_code": "GR",
												"y1": 12,
												"classification_confidence": 0.4316732585430145,
												"x2": 268,
												"confidence": 0.8992604613304138,
												"y2": 660,
												"height": 648,
												"caption": "The on-site oxygen 2<i>p</i> two-hole state is prepared and detected via coincidences of oxygen 1<i>s</i> (K-shell) ionization and the oxygen <i>KVV</i> Auger decay. LHB and UHB denote lower and upper Hubbard band, respectively.",
												"width": 264,
												"caption_input_tokens": 573,
												"nm_height": None,
												"caption_output_tokens": 403
											},
										]
									]
								]
							},
						}
					}
				})
async def subfigures(run_id: UUID, user: CurrentUserId, accept: AcceptHeader, page=None):
	return await get_items(Subfigure, run_id, user, accept, page)


@router.api_route("/{run_id}/scales", methods=["GET", "HEAD"], tags=[TAG],
				  responses=get_items_responses("Scale", "scales", []))
async def scales(run_id: UUID, user: CurrentUserId, accept: AcceptHeader):
	return await get_items(Scale, run_id, user, accept)


@router.api_route("/{run_id}/subfigure_labels", methods=["GET", "HEAD"], tags=[TAG],
				  responses=get_items_responses("SubfigureLabel", "subfigure labels", []))
async def subfigure_labels(run_id: UUID, user: CurrentUserId, accept: AcceptHeader):
	return await get_items(SubfigureLabel, run_id, user, accept)


@router.api_route("/{run_id}/scale_labels", methods=["GET", "HEAD"], tags=[TAG],
				  responses=get_items_responses("ScaleLabel", "scale labels", []))
async def scale_labels(run_id: UUID, user: CurrentUserId, accept: AcceptHeader):
	return await get_items(ScaleLabel, run_id, user, accept)
# endregion


# region Individual Objects
@router.api_route("/{run_id}/articles/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=Article,
				  responses=get_item_responses("Article", "article"))
async def article(run_id: UUID, id: str, user: CurrentUserId):
	return await get_item(Article, run_id, id, user, "No Article with id: {}".format)


@router.api_route("/{run_id}/figures/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=Figure,
				  responses=get_item_responses("Figure", "figure", []))
async def figure(run_id: UUID, id: str, user: CurrentUserId):
	return await get_item(Figure, run_id, id, user, "No Figure with id: {}".format)


@router.api_route("/{run_id}/subfigures/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=Subfigure,
				  responses=get_item_responses("Subfigure", "subfigure", []))
async def subfigure(run_id: UUID, id: str, user: CurrentUserId):
	return await get_item(Subfigure, run_id, id, user, "No Subfigure with id: {}".format)


@router.api_route("/{run_id}/scales/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=Scale,
				  responses=get_item_responses("Scale", "scale", []))
async def scale(run_id: UUID, id: str, user: CurrentUserId):
	return await get_item(Scale, run_id, id, user, "No Scale with id: {}".format)


@router.api_route("/{run_id}/subfigure_labels/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=SubfigureLabel,
				  responses=get_item_responses("SubfigureLabel", "subfigure label", []))
async def subfigure_label(run_id: UUID, id: str, user: CurrentUserId):
	return await get_item(SubfigureLabel, run_id, id, user, "No SubfigureLabel with id: {}".format)


@router.api_route("/{run_id}/scale_labels/{id}", methods=["GET", "HEAD"], tags=[TAG], response_model=ScaleLabel,
				  responses=get_item_responses("ScaleLabel", "scale label", []))
async def scale_label(run_id: UUID, id: str, user: CurrentUserId):
	return await get_item(ScaleLabel, run_id, id, user, "No ScaleLabel with id: {}".format)
# endregion
