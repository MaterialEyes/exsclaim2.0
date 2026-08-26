from ..models import *
from ...config import ui_settings

import exsclaim
import httpx2
import logging

from asyncpg import UndefinedTableError
from datetime import datetime as dt, timezone as tz
from fastapi import APIRouter, status
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import JSONResponse
from hashlib import sha256
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse
from starlette.routing import BaseRoute
from textwrap import dedent
from typing import Optional
from uuid import UUID

__all__ = ["router"]

router = APIRouter()
cache = dict()


async def get(url: str) -> tuple[Response | bytes, str]:
	global cache
	if url in cache:
		return cache[url]

	async with httpx2.AsyncClient() as client:
		response = await client.get(url)
		if not response.is_success:
			return Response(status_code=status.HTTP_301_MOVED_PERMANENTLY, headers={"Location": url})
		content = response.content

	etag = sha256(content).hexdigest()
	cache[url] = (content, etag)

	return content, etag


def get_host_from_request(request: Request) -> str:
	scheme = request.headers.get("X-Forwarded-Proto", request.url.scheme)
	return f"{scheme}://{request.url.netloc}"


async def get_dark_ui(map_file: bool = False) -> Response:
	"""An endpoint to get around an error retrieving the Dark UI CSS file from jcphlux on GitHub."""
	dark_ui = "https://raw.githubusercontent.com/jcphlux/swagger-ui-themes/main/docs/css/swagger-dark-ui.css"
	if map_file:
		dark_ui += ".map"

	content, _ = await get(dark_ui)
	if isinstance(content, bytes):
		return Response(content, media_type="text/css", status_code=status.HTTP_200_OK, headers={"Location": dark_ui})
	return content


@router.get("/", include_in_schema=False)
async def dark_theme(request: Request):
	schema = request.app.openapi()
	logger = request.app.logger

	# https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-CH-Prefers-Color-Scheme
	color_scheme: str = request.headers.get("Sec-Ch-Prefers-Color-Scheme", "").replace("'\"", "")

	light_css = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
	dark_css = "/swagger-dark-ui.css"

	match color_scheme:
		case "light":
			css = light_css
		case "dark" | "":
			css = dark_css
		case _:
			logger.error(f"Unsupported light mode preference: \"{color_scheme}\".")
			css = light_css

	response = get_swagger_ui_html(
		openapi_url=request.app.openapi_url,
		title=schema["info"]["title"],
		swagger_css_url=css,
		swagger_favicon_url="/favicon.ico"
	)

	return response


@router.api_route("/docs", methods=["GET", "HEAD"], include_in_schema=False)
async def docs_redirect() -> Response:
	return Response(status_code=status.HTTP_301_MOVED_PERMANENTLY, headers={"Location": "/"})


@router.api_route("/redoc", methods=["GET", "HEAD"], include_in_schema=False)
async def redoc(request: Request) -> Response:
	app = request.app
	schema = app.openapi()
	return get_redoc_html(
		openapi_url=app.openapi_url,
		title=schema["info"]["title"],
		redoc_favicon_url="/favicon.ico",
	)


@router.api_route("/openapi.yaml", methods=["GET"], include_in_schema=False)
async def openapi_yaml(request: Request) -> Response:
	app = request.app
	if not hasattr(app, "openapi_yaml_schema"):
		app.openapi()

	schema = request.app.openapi_yaml_schema
	return Response(schema, status_code=200, media_type="text/plain")


@router.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def favicon() -> Response:
	return Response(status_code=status.HTTP_308_PERMANENT_REDIRECT, headers={"Location": f"{ui_settings.DASHBOARD_URL}/favicon.ico"})


@router.api_route("/favicon.png", methods=["GET", "HEAD"], include_in_schema=False)
async def favicon() -> Response:
	return Response(status_code=status.HTTP_308_PERMANENT_REDIRECT, headers={"Location": f"{ui_settings.DASHBOARD_URL}/favicon.png"})


@router.api_route("/swagger-dark-ui.css", methods=["GET", "HEAD"], include_in_schema=False)
async def get_dark_css() -> Response:
	return await get_dark_ui(False)


@router.api_route("/swagger-dark-ui.css.map", methods=["GET", "HEAD"], include_in_schema=False)
async def get_dark_css() -> Response:
	return await get_dark_ui(True)


@router.api_route("/healthcheck", methods=["GET", "HEAD"], tags=["System Check"], include_in_schema=False,
		 responses={
			 200: {
				 "description": "API is Healthy.",
				 "content": {
					 "application/json": {
						 "schema": {
							 "type": "object",
							 "properties": {
								 "message": {
									 "type": "string"
								 },
							 }
						 },
						 "example": {
							 "message": f"EXSCLAIM! version {exsclaim.__version__} is running fine."
						 }
					 },
					 "text/plain": {
						 "schema": {
							 "type": "string",
						 },
						 "example": f"EXSCLAIM! version {exsclaim.__version__} is running fine."
					 }
				 }
			 },
			 status.HTTP_503_SERVICE_UNAVAILABLE: {
				 "description": "API Unhealthy.",
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
							 "message": "The API is running but cannot connect to the database.",
						 }
					 },
					 "text/plain": {
						 "schema": {
							 "type": "string",
						 },
						 "example": "The API is running but cannot connect to the database.",
					 }
				 }
			 },
		 })
async def healthcheck(request: Request) -> Response:
	logger: logging.Logger = request.state.logger
	try:
		session: AsyncSession = request.state.session
		await session.execute(select(Results))
		response = Response(f"EXSCLAIM! version {exsclaim.__version__} is running fine.",
							status_code=status.HTTP_200_OK, media_type="text/plain")
	except OSError as e:
		logger.exception(f"An error occurred trying to connect to the database during a healthcheck: {e}")
		response = Response("The API is running but cannot connect to the database.",
							status_code=status.HTTP_503_SERVICE_UNAVAILABLE, media_type="text/plain")
	except UndefinedTableError as e:
		logger.exception(e)
		response = Response(
			"The API and database are both running, however, the database seems to empty. Please try again later.",
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE, media_type="text/plain")
	except Exception as e:
		logger.exception(f"An error occurred during the healthcheck: {e}.")
		response = Response("A fundamental error has prevented the API from functioning.",
							status_code=status.HTTP_503_SERVICE_UNAVAILABLE, media_type="text/plain")

	if request.headers.get("Accept") == "application/json":
		response = JSONResponse({"message": response.body.decode(response.charset)}, status_code=response.status_code)

	return response


@router.api_route("/sitemap.xml", methods=["GET"], include_in_schema=False)
def sitemap(request: Request) -> Response:
	if (sitemap := request.app.sitemap) is None:
		last_mod = dt.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%z")
		host = get_host_from_request(request)

		def format_xml(route: BaseRoute) -> Optional[str]:
			path = route.path
			if "{" in path:
				return None

			return dedent(f"""\
				<url>
					<loc>{host}{path}</loc>
					<lastmod>{last_mod}</lastmod>
				</url>
			""")

		routes = filter(lambda route: route is not None, map(format_xml, request.app.routes))
		sitemap = f'<urlset xmlns="https://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="https://www.w3.org/1999/xhtml">\n{''.join(routes)}</urlset>'
		request.app.sitemap = sitemap

	return Response(sitemap, media_type="text/xml", status_code=status.HTTP_200_OK)


@router.api_route("/robots.txt", methods=["GET"], include_in_schema=False)
def robots(request: Request) -> Response:
	robots_message = dedent(f"""\
			User-Agent: *
			Content-signal: search=yes, ai-train=no, use=reference
			Allow: /
			
			User-Agent: Amazonbot
			Disallow: /
			
			User-agent: Applebot-Extended
			Disallow: /
			
			User-agent: Bytespider
			Disallow: /
			
			User-agent: CCBot
			Disallow: /
			
			User-Agent: ClaudeBot
			Disallow: /
			
			User-Agent: Google-Extended
			Disallow: /
			
			User-Agent: GPTBot
			Disallow: /
			
			Allow: /robots.txt
			
			Allow: /sitemap.xml
			
			Allow: /classification_codes
			
			Allow: /compression_types
			
			Allow: /query
			
			Allow: /openapi.json
			
			Allow: /openapi.yaml
			
			Allow: /docs
			
			Allow: /redoc
			
			Disallow: /user/previous_runs
			
			Disallow: /healthcheck
			
			Disallow: /banner
			
			Disallow: /checkpoints
			
			Disallow: /results/*
			
			Disallow: /status/*
			
			Disallow: /user/*
			
			Disallow: /swagger-dark-ui.css
			
			Disallow: /swagger-dark-ui.css.map
			
			Sitemap: {get_host_from_request(request)}/sitemap.xml
		""")
	return Response(robots_message, media_type="text/plain", status_code=status.HTTP_200_OK)


@router.api_route("/banner", methods=["GET", "HEAD"], include_in_schema=False)
async def get_banner_text(request: Request, last_seen_banner: Optional[UUID] = None) -> Response:
	session: AsyncSession = request.state.session
	results = await session.execute(select(Banner).order_by(Banner.created.desc()).limit(1))

	banner: Banner = results.scalar_one_or_none()

	if banner is None or banner.id == last_seen_banner:
		return HTMLResponse(status_code=status.HTTP_204_NO_CONTENT)

	return JSONResponse(dict(id=str(banner.id), content=banner.content), status_code=status.HTTP_200_OK)
