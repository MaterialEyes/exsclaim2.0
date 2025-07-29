import exsclaim
import logging

from .settings import Settings
from .models import *
from .middleware import *
from .routers import v1_router

from aiohttp import ClientSession
from asyncpg import UndefinedTableError
from contextlib import asynccontextmanager
from datetime import datetime as dt
from exsclaim.__main__ import run_pipeline as exsclaim_pipeline
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import Response, FileResponse, JSONResponse
from io import BytesIO
from json import dump
from logging.handlers import TimedRotatingFileHandler
from os import listdir, getenv
from pathlib import Path
from pytz import utc as UTC
from sqlmodel import select, update, insert
from sqlmodel.ext.asyncio.session import AsyncSession
from shutil import make_archive, rmtree, get_archive_formats
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from tarfile import open as tar_open
from tempfile import TemporaryDirectory
from typing import Literal
from uuid import UUID
from uuid_utils import uuid7


__all__ = ["app"]


def my_schema():
	if app.openapi_schema:
		return app.openapi_schema

	openapi_schema = get_openapi(
		title="EXSCLAIM API",
		version=exsclaim.__version__,
		routes=app.routes,
	)

	openapi_schema["info"] = {
		"title": "EXSCLAIM API",
		"version": exsclaim.__version__,
		"description": "**EX**traction, **S**eparation, and **C**aption-based natural **L**anguage **A**nnotation of **IM**ages from scientific figures API.<br>"
					   "Check out our paper at <a href=\"https://arxiv.org/abs/2103.10631\">https://arxiv.org/abs/2103.10631</a>.<br>"
					   "Check out our GitHub at <a href=\"https://github.com/MaterialEyes/exsclaim2.0\">https://github.com/MaterialEyes/exsclaim2.0</a>.",
		# "termsOfService": "https://materialeyes.org/terms/",
		"contact": {
			"name": "Developers",
			# "url": "https://materialeyes.org/help",
			"email": "developer@materialeyes.org"
		},
		"license": {
			"name": "MIT License",
			"identifier": "MIT",
			"url": "https://opensource.org/license/mit"
		},
	}

	app.openapi_schema = openapi_schema
	return app.openapi_schema


def date_to_json(date:dt | None) -> str | None:
	if date is None:
		return None
	# FIXME: The Start time shows the time in America/Chicago but says the timezone is UTC (+00:00)
	if date.tzinfo is None:
		date = UTC.localize(date)

	return date.isoformat()


def create_logger():
	printer_handler = logging.StreamHandler()
	printer_handler.setFormatter(exsclaim.PrinterFormatter())
	file_handler = TimedRotatingFileHandler("/exsclaim/logs/exsclaim-api.log", backupCount=2,
											interval=1, when="D")
	file_handler.setFormatter(exsclaim.ExsclaimFormatter())

	logging.basicConfig(level=logging.INFO,
						handlers=(printer_handler, file_handler),
						force=True)
	return logging.getLogger(__name__)


def flush_logger():
	for handler in logger.handlers:
		handler.flush()


@asynccontextmanager
async def lifespan(app:FastAPI):
	# Runs before the application starts
	for _dir in ("results", "logs"):
		path = Path("/exsclaim") / _dir
		path.mkdir(exist_ok=True, parents=True)

	yield # Runs the application

	# Runs after the application has finished
	flush_logger()


def get_middleware() -> list[Middleware]:
	middleware = [
		Middleware(RequestLoggerMiddleware, logger=logger),
		Middleware(PreflightCacheMiddleware),
	]

	# region CORS Middleware
	origins = ["https://exsclaim.materialeyes.org", "https://exsclaim-dev.materialeyes.org"]
	if settings.DEBUG:
		origins.append(getenv("DASHBOARD_URL", "http://localhost:3000").rstrip('/'))

	middleware.append(Middleware(
		CORSMiddleware,
		allow_origins=origins,
		allow_credentials=True,
		allow_methods=["GET", "POST"],
		allow_headers=["*"],
	))
	# endregion

	# region Trusted Host Middleware
	trusted_hosts = [
		"exsclaim.materialeyes.org",
		"*.exsclaim.materialeyes.org",
		"exsclaim-dev.materialeyes.org",
		"*.exsclaim-dev.materialeyes.org",
		"localhost",
		"127.0.0.1",
	]

	middleware.append(Middleware(
		TrustedHostMiddleware,
		allowed_hosts=trusted_hosts
	))
	# endregion

	middleware.append(Middleware(GZipMiddleware, minimum_size=1_000))
	middleware.append(Middleware(SQLAlchemyMiddleware, logger=logger))
	middleware.append(Middleware(HashMiddleware))

	return middleware


logger = create_logger()
_EXAMPLE_UUID = UUID("fd70dd4b-1043-4650-aa11-9f55dc2e2c2b")
# TODO: Cache content like favicon and the css files so they're scraped once
cache = dict()

settings = Settings()
app = FastAPI(
	title=settings.PROJECT_NAME,
	debug=settings.DEBUG,
	docs_url=None,
	redoc_url=None,
	lifespan=lifespan,
	middleware=get_middleware()
)
app.openapi = my_schema
app.configuration_ini = None

app.include_router(v1_router, prefix="/results/v1")


@app.get("/", include_in_schema=False)
async def dark_theme(request:Request, light_mode:bool = True):
	schema = app.openapi()

	# https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-CH-Prefers-Color-Scheme
	color_scheme:str = request.headers.get("Sec-Ch-Prefers-Color-Scheme", "").replace("'\"", "")

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
		openapi_url=app.openapi_url,
		title=schema["info"]["title"],
		swagger_css_url=css,
		swagger_favicon_url="/favicon.ico"
	)

	return response


@app.get("/docs", include_in_schema=False)
async def docs_redirect() -> Response:
	return Response(status_code=301, headers={"Location": "/"})


@app.get("/redoc", include_in_schema=False)
async def redoc():
	schema = app.openapi()
	return get_redoc_html(
		openapi_url=app.openapi_url,
		title=schema["info"]["title"],
		redoc_favicon_url="https://raw.githubusercontent.com/MaterialEyes/exsclaim2.0/b22ed4009c63ddd58d8415c5882ab58febde691c/dashboard/public/favicon.ico",
	)


async def get(url:str) -> Response | bytes:
	global cache
	if url in cache:
		return cache[url]

	async with ClientSession() as session:
		response = await session.get(url)
		if not response.ok:
			return Response(status_code=301, headers={"Location": url})
		content = await response.content.read()

	cache[url] = content

	return content


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
	if hasattr(app, "favicon"):
		return Response(app.favicon, media_type="image/x-icon", status_code=200)

	content = await get("https://raw.githubusercontent.com/MaterialEyes/exsclaim2.0/b22ed4009c63ddd58d8415c5882ab58febde691c/dashboard/public/favicon.ico")
	if isinstance(content, Response):
		return content

	app.favicon = content
	return Response(app.favicon, media_type="image/x-icon", status_code=200)


@app.get("/swagger-dark-ui.css", include_in_schema=False)
async def get_dark_css() -> Response:
	return await get_dark_ui(False)


@app.get("/swagger-dark-ui.css.map", include_in_schema=False)
async def get_dark_css() -> Response:
	return await get_dark_ui(True)


async def get_dark_ui(map_file:bool = False) -> Response:
	"""An endpoint to get around an error retrieving the Dark UI CSS file from jcphlux on GitHub."""
	dark_ui = "https://raw.githubusercontent.com/jcphlux/swagger-ui-themes/main/docs/css/swagger-dark-ui.css"
	if map_file:
		dark_ui += ".map"
	
	content = await get(dark_ui)
	if isinstance(content, bytes):
		return Response(content, media_type="text/css", status_code=200, headers={"Location": dark_ui})
	return content


@app.get("/healthcheck", tags=["System Check"],
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
			 503: {
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
async def healthcheck(request:Request) -> Response:
	logger: logging.Logger = request.state.logger
	try:
		session = request.state.session
		await session.exec(select(Results))
		response = Response(f"EXSCLAIM! version {exsclaim.__version__} is running fine.",
							status_code=200, media_type="text/plain")
	except OSError as e:
		logger.exception(f"An error occurred trying to connect to the database during a healthcheck: {e}")
		response = Response("The API is running but cannot connect to the database.",
							status_code=503, media_type="text/plain")
	except UndefinedTableError as e:
		logger.exception(e)
		response = Response("The API and database are both running, however, the database seems to empty. Please try again later.",
							status_code=503, media_type="text/plain")
	except Exception as e:
		logger.exception(f"An error occurred during the healthcheck: {e}.")
		response = Response("A fundamental error has prevented the API from functioning.",
							status_code=503, media_type="text/plain")

	if request.headers.get("Accept") == "application/json":
		response = JSONResponse({"message": response.body.decode(response.charset)}, status_code=response.status_code, media_type="application/json")

	return response


async def run_exsclaim(_id:UUID, search_query_location:Path, session: AsyncSession):
	db_result: Status = Status.ERROR
	result_code = -1
	try:
		result_code = await exsclaim_pipeline(query=search_query_location, journal_scraper=True, caption_distributor=True, figure_separator=True,
											  compress="gztar", compress_location=f"/exsclaim/results/{_id}", verbose=settings.DEBUG)
		if result_code == 0:
			db_result = Status.FINISHED

		results_dir = search_query_location.parent
		if results_dir.is_dir():
			rmtree(results_dir.absolute(), ignore_errors=True)
	except KeyboardInterrupt:
		db_result = Status.KILLED
	except Exception as e:
		logging.getLogger(f"run_exsclaim_{_id}").exception(e)

	# "UPDATE results SET status = %s, end_time = NOW() WHERE id = %s", (db_result, _id)
	logger.debug("\n\n\nAbout to update result to finished\n\n\n")
	await session.exec(update(Results).where(Results.id == _id).values(status=db_result, end_time=dt.now()))
	await session.commit()
	logger.debug("\n\n\nCode should have gone through.\n\n\n")

	return result_code


@app.post("/query", responses={
	202: {
		"description": "Query successfully submitted.",
		"content": {
			"application/json": {
				"schema": {
					"type": "object",
					"properties": {
						"message": {
							"type": "string",
						},
						"result_id": {
							"type": "string",
							"format": "uuid"
						},
					}
				},
				"example": {
					"message": "Thank you, your request is currently being processed.",
					"result_id": str(_EXAMPLE_UUID)
				}
			},
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": f"Thank you, your request is currently being processed, and the results can be found using id: {_EXAMPLE_UUID}."
			}
		}
	},
	500: {
		"description": "An internal database error stopped the query from being submitted.",
		"content": {
			"application/json": {
				"schema": {
					"type": "object",
					"properties": {
						"message": {
							"type": "string",
						},
					}
				},
				"example": {
					"message": "An error occurred connecting to the database. Please try again later.",
				}
			},
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": "An error occurred connecting to the database. Please try again later."
			}
		}
	},
	503: {
		"description": "An internal error stopped the query from being submitted.",
		"content": {
			"application/json": {
				"schema": {
					"type": "object",
					"properties": {
						"message": {
							"type": "string",
						},
					}
				},
				"example": {
					"message": "An unknown error occurred within the EXSCLAIM! API. Please try again later.",
				}
			},
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": "An unknown error occurred within the EXSCLAIM! API. Please try again later."
			}
		}
	}
}, tags=["Using EXSCLAIM"])
async def query(request:Request, search_query: Query, background_tasks:BackgroundTasks) -> Response:
	session = request.state.session
	logger: logging.Logger = request.state.logger

	send_json = request.headers.get("accept", "") == "application/json"
	try:
		uuid = uuid7()
		str_uuid = str(uuid)
		uuid = UUID(str_uuid)

		results_dir = Path("/exsclaim") / "results" / str_uuid
		results_dir.mkdir(exist_ok=True, parents=True)

		exsclaim_input = {
			"name": search_query.name if search_query else "exsclaim_results",
			"run_id": str_uuid,
			"journal_family": search_query.journal_family.lower(),
			"maximum_scraped": search_query.maximum_scraped,
			"sortby": search_query.sortby,
			"query": {
				"search_field_1": {
					"term": search_query.term,
					"synonyms": search_query.synonyms
				}
			},
			"llm": search_query.llm,
			"model_key": search_query.model_key,
			"open": search_query.open_access,
			"save_format": search_query.save_format,
			"logging": ["exsclaim.log"],
			"results_dir": str(results_dir),
			"notifications": {
				"ntfy": list(map(lambda ntfy: ntfy.to_json(), search_query.ntfy)),
				"emails": search_query.emails,
			}
		}

		with open(results_dir / "search_query.json", "w") as f:
			dump(exsclaim_input, f, indent='\t')
		background_tasks.add_task(run_exsclaim, uuid, results_dir / "search_query.json", session)

		db_json = exsclaim_input.copy()
		db_json["model_key"] = "model_key" in db_json.keys()
		for unnecessary_key in ["notifications", "results_dir", "logging"]:
			if unnecessary_key in db_json:
				db_json.pop(unnecessary_key)

		for sanitized_keys in ("name", "term", "synonyms"):
			... # TODO: Sanitize these user inputs

		# "INSERT INTO results(id, search_query, extension) VALUES(%s, %s, %s);", (uuid, dumps(db_json), "tar.gz")
		await session.exec(insert(Results).values(id=uuid, search_query=db_json, extension=SaveExtensions.TAR))
		await session.commit()

		if send_json:
			response = JSONResponse({"message": "Thank you, your request is currently being processed.", "result_id": str_uuid},
									status_code=202, media_type="application/json")
		else:
			response = Response(f"Thank you, your request is currently being processed, and the results can be found using id: {str_uuid}.",
						status_code=202, media_type="text/plain")
	except OSError as e:
		logger.exception(e)
		message = "An error occurred connecting to the database. Please try again later."
		if send_json:
			response = JSONResponse({"message": message}, status_code=500, media_type="application/json")
		else:
			response = Response(message, status_code=500, media_type="text/plain")
	except Exception as e:
		print(f"{logger=}, {e}")
		logger.exception(e)
		message = "An unknown error occurred within the EXSCLAIM! API. Please try again later."
		if send_json:
			response = JSONResponse({"message": message}, status_code=503, media_type="application/json")
		else:
			response = Response(message, status_code=503, media_type="text/plain")

	return response


@app.get("/status/{result_id}", tags=["Using EXSCLAIM"],
		 responses={
			 200: {
				 "description": "Status Found for ID.",
				 "content": {
					 "application/json": {
						 "schema": {
							 "type": "object",
							 "properties": {
								 "status": {
									 "type": "string",
								 },
								 "start_time": {
									 "type": "string",
									 "format": "date-time"
								 },
								 "end_time": {
									 "type": "string",
									 "format": "date-time"
								 },
								 "run_time": {
									 "type": "number",
									 "format": "float"
								 },
							 }
						 },
						 "example": {
							 "status": "Finished.",
							 "start_time": "2024-07-15T13:00:12.712358+00:00",
							 "end_time": "2024-07-15T13:06:58.928669+00:00",
							 "run_time": 3641.92811
						 }
					 }
				 }
			 },
			 404: {
				 "description": "ID Not Found.",
				 "content": {
					 "application/json": {
						 "schema": {
							 "type": "object",
							 "properties": {
								 "status": {
									 "type": "string"
								 },
								 "message": {
									 "type": "string"
								 }
							 }
						 },
						 "example": {
							 "status": "Finished",
							 "message": f"There is no query recorded in our database with id: \"{_EXAMPLE_UUID}\".",
						 }
					 }
				 }
			 },
			 422: {
				 "description": "Improper UUID Format for ID.",
				 "content": {
					 "application/json": {
						 "schema": {
							 "type": "object",
							 "properties": {
								 "status": {
									 "type": "null"
								 },
								 "message": {
									 "type": "string"
								 }
							 }
						 },
						 "example": {
							 "status": None,
							 "message": f"\"{_EXAMPLE_UUID}\"is not a valid UUID.",
						 }
					 }
				 }
			 },
			 500: {
				 "description": "Unknown Internal Server Error.",
				 "content": {
					 "application/json": {
						 "schema": {
							 "type": "object",
							 "properties": {
								 "status": {
									 "type": "string"
								 },
								 "start_time": {
									 "type": "string"
								 },
								 "end_time": {
									 "type": "string"
								 },
								 "run_time": {
									 "type": "number",
									 "format": "float"
								 },
							 }
						 },
						 "example": {
							 "status": "Closed due to an error.",
							 "start_time": "2024-07-15T13:00:12.712358+00:00",
							 "end_time": "2024-07-15T13:06:58.928669+00:00",
							 "run_time": 3641.92811
						 }
					 }
				 }
			 },
			 503: {
				 "description": "Internal Database Error.",
				 "content": {
					 "application/json": {
						 "schema": {
							 "type": "object",
							 "properties": {
								 "status": {
									 "type": "string"
								 },
								 "message": {
									 "type": "string"
								 }
							 }
						 },
						 "example": {
							 "status": "Unknown",
							 "message": "An unknown error has occurred within the database. Please try again later.",
						 }
					 }
				 }
			 },
		 })
async def status(request:Request, result_id: UUID):
	session = request.state.session
	logger: logging.Logger = request.state.logger
	results = await session.exec(select(Results).where(Results.id == result_id))
	result:Results = results.one_or_none()

	if result is None:
		return JSONResponse(
			{"status": "Not Found", "message": f"There is no query recorded in our database with id: {result_id}."},
			status_code=404, media_type="application/json")

	status, start_time, end_time = result.status, result.start_time, result.end_time

	time_diff = (end_time or dt.now(tz=start_time.tzinfo)) - start_time

	match status:
		case Status.RUNNING | Status.FINISHED | Status.KILLED:
			status_code = 200
		case Status.ERROR:
			status_code = 503
		case _:
			logger.exception(f"Unknown status {status} when checking status of {result_id}.")
			return JSONResponse(dict(message="An unknown status was saved in our database. Try again later."), status_code=500, media_type="application/json")

	json = dict(
		status=f"{status}.",
		start_time=date_to_json(start_time),
		end_time=date_to_json(end_time),
		run_time=time_diff.total_seconds()
	)

	headers = {}
	if status == "Finished":
		headers = {"Location": f"/results/{result_id}"}
	response = JSONResponse(json, status_code=status_code, media_type="application/json", headers=headers)

	return response


@app.get("/results/{result_id}", tags=["Using EXSCLAIM"],
		 responses={
			 200: {
				 "description": "Results Compressed and Included.",
				 "content": {
					 "application/octet-stream": {
						 "schema": {
							 "type": "string"
						 },
						 "example": ""
					 }
				 }
			 },
			 202: {
				 "description": "Query Currently Running.",
				 "content": {
					 "text/plain": {
						 "schema": {
							 "type": "string",
						 },
						 "example": "The results are still being compiled.",
					 }
				 }
			 },
			 404: {
				 "description": "ID Not Found.",
				 "content": {
					 "text/plain": {
						 "schema": {
							 "type": "string"
						 },
						 "example": f"There is no query recorded in our database with id: \"{_EXAMPLE_UUID}\"."
					 }
				 }
			 },
			 422: {
				 "description": "Improper UUID Format for ID or Improper Compression Value.",
				 "content": {
					 "text/plain": {
						 "schema": {
							 "type": "string",
						 },
						 "example": "unknown archive format 'gztar21'",
					 }
				 }
			 },
			 501: {
				 "description": "Internal Database Error.",
				 "content": {
					 "text/plain": {
						 "schema": {
							 "type": "string",
						 },
						 "example": f"The database has an unknown status for id \"{_EXAMPLE_UUID}\" and cannot send the results at this time."
					 }
				 }
			 },
			 503: {
				 "description": "Error caused the query to not finish which results in no results.",
				 "content": {
					 "text/plain": {
						 "schema": {
							 "type": "string",
						 },
						 "example": "The results could not be compiled due to an error. Please submit your query again."
					 }
				 }
			 },
		 })
async def download(request:Request, result_id:UUID, compression:str = "default", filename:Literal["name", "id"] = "id") -> Response:
	session = request.state.session
	# Set the filename to be id by default
	if compression != "default":
		if compression not in get_archive_formats().keys():
			return Response(f"Unknown archive format '{compression}'. Check /compression_types to see what values are allowed.", status_code=422, media_type="text/plain")

	else: # compression == "default"
		if request.headers.get("sec-ch-ua-platform", ""):
			match request.headers.get("sec-ch-ua-platform", "").replace('"', ""):
				case "Linux":
					compression = "gztar"
				case "Android" | "Chrome OS" | "Chromium OS" | "iOS" | "macOS" | "Windows" | "Unknown" | _:
					compression = "zip"
		else:
			os = request.headers.get("user-agent", "")
			if "Linux" in os:
				compression = "gztar"
			else:
				compression = "zip"

	results = await session.exec(select(Results).where(Results.id == result_id))
	result:Results = results.one_or_none()

	if result is None:
		return Response(f"There is no query recorded in our database with id: {result_id}.", status_code=404, media_type="text/plain")

	match result.status:
		case Status.RUNNING:
			return Response("The results are still being compiled.", status_code=202, media_type="text/plain")
		case Status.KILLED:
			return Response("The results were closed by user or admin intervention.",
							status_code=200, media_type="text/plain")
		case Status.ERROR:
			return Response("The results could not be compiled due to an error. Please submit your query again.",
							status_code=503, media_type="text/plain")
		case Status.FINISHED:
			...
		case _:
			return Response(f"The database has an unknown status for id \"{result_id}\" and cannot send the results at this time.",
							status_code=501, media_type="text/plain")

	results_file = (Path("/exsclaim") / "results" / str(result_id)).with_suffix(".tar.gz")
	if not results_file.exists():
		return Response("The result id was found in our database, but the corresponding results file could not be found. Please try again later.",
						status_code=500, media_type="text/plain")

	if compression == "gztar":
		return FileResponse(path=str(results_file), media_type="application/octet-stream", filename=results_file.name,
							status_code=200)

	tmp_dir = Path(TemporaryDirectory().name)

	with tar_open(results_file) as f:
		f.extractall(tmp_dir)

	name = [file for file in listdir(tmp_dir) if "." not in file][0]

	try:
		results_file = Path(make_archive(str(tmp_dir / str(result_id)), compression, root_dir=str(tmp_dir), base_dir=name))

		buffer = BytesIO()

		with open(results_file, "rb") as f:
			buffer.write(f.read())

		rmtree(tmp_dir)

		if filename == "name":
			filename = results_file.with_stem(name).name
		elif filename == "id":
			filename = results_file.name

		return Response(content=buffer.getvalue(), media_type="application/octet-stream", headers={"Content-Disposition": f"inline ; filename = \"{filename}\""})
	except ValueError as e:
		return Response(str(e), status_code=422, media_type="text/plain")


@app.get("/compression_types", tags=["Using EXSCLAIM"],
		 responses={
			 200: {
				 "description": "Possible Compression Algorithms/Extensions",
				 "content": {
					 "application/json": {
						 "schema": {
							 "type": "object",
							 "properties": {
								 "compression_types": {
									 "type": "object"
								 }
							 }
						 },
						 "example": {
							 "compression_types": ["tar","gztar","zip","bztar","xztar"],
						 }
					 },
					 "text/plain": {
						 "schema": {
							 "type": "string",
						 },
						 "example": '["tar","gztar","zip","bztar","xztar"]'
					 }
				 }
			 },
			 202: {
				 "description": "The given compression type is allowed.",
				 "content": {
					 "application/json": {
						 "schema": {
							 "type": "object",
							 "properties": {
								 "allowed": {
									 "type": "boolean"
								 }
							 }
						 },
						 "example": {
							 "allowed": True,
						 }
					 },
					 "text/plain": {
						 "schema": {
							 "type": "string",
						 },
						 "example": "zip is an allowed value."
					 }
				 }
			 },
			 404: {
				 "description": "The given compression type is not allowed.",
				 "content": {
					 "application/json": {
						 "schema": {
							 "type": "object",
							 "properties": {
								 "allowed": {
									 "type": "boolean"
								 }
							 }
						 },
						 "example": {
							 "allowed": False,
						 }
					 },
					 "text/plain": {
						 "schema": {
							 "type": "string",
						 },
						 "example": "zip is NOT an allowed value."
					 }
				 }
			 }
		 })
async def get_possible_compressions(request:Request, compression_type:str = None) -> Response:
	send_json = request.headers.get("accept", "") == "application/json"
	compression_types = frozenset(map(lambda i: i[0], get_archive_formats()))

	if compression_type is None:
		compression_types = list(compression_types)
		if send_json:
			return JSONResponse({"compression_types": compression_types}, status_code=200, media_type="application/json")
		return Response(str(compression_types), status_code=200, media_type="text/plain")

	allowed = compression_type in compression_types
	status_code = 202 if allowed else 404
	if send_json:
		return JSONResponse({"allowed": allowed}, status_code=status_code, media_type="application/json")

	return Response(f"{compression_type} is {'NOT ' if not allowed else ''}an available compression type.", status_code=status_code, media_type="text/plain")


@app.get("/classification_codes", tags=["Using EXSCLAIM"], response_model=list[ClassificationCodes])
async def classification_codes(request:Request) -> Response:
	session = request.state.session
	results = await session.exec(select(ClassificationCodes))
	return results.all()


@app.get("/checkpoints/{checkpoint}", tags=["EXSCLAIM Model Checkpoints"])
async def download_checkpoint(checkpoint:str) -> Response:
	checkpoint_folder = Path(getenv("EXSCLAIM_CHECKPOINTS", "/exsclaim/checkpoints")).resolve()

	if not checkpoint_folder.exists() or not checkpoint_folder.is_dir():
		return Response("Could not find any checkpoints. Please try again later.", status_code=503, media_type="text/plain")

	checkpoint_path = checkpoint_folder / checkpoint
	if not checkpoint_path.exists():
		return Response(f"Could not find checkpoint \"{checkpoint}\". ", status_code=404, media_type="text/plain")

	return FileResponse(path=str(checkpoint_path), media_type="application/octet-stream", filename=checkpoint,
						status_code=200)
