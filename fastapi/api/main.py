import exsclaim
import logging

from datetime import datetime as dt
from exsclaim import get_database_connection_string
from fastapi import FastAPI, Path as FastPath, Request
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from io import BytesIO
from json import dump, dumps
from os import listdir, mkdir
from pathlib import Path
from psycopg import connect, OperationalError
from psycopg.errors import UndefinedTable
from pydantic import BaseModel
from pytz import utc as UTC
from requests import get
from shutil import make_archive, rmtree, _ARCHIVE_FORMATS
from subprocess import Popen
from tarfile import open as tar_open
from tempfile import TemporaryDirectory
from typing import Annotated, Literal
from uuid import UUID


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
	return UTC.localize(date).isoformat()


def get_logger():
	from os import mkdir
	printer_handler = logging.StreamHandler()
	printer_handler.setFormatter(exsclaim.PrinterFormatter())
	file_handler = logging.FileHandler("/exsclaim/logs/exsclaim-api.log", "a")
	file_handler.setFormatter(exsclaim.ExsclaimFormatter())

	logging.basicConfig(level=logging.INFO,
						handlers=(printer_handler, file_handler),
						force=True)
	return logging.getLogger(__name__)


def flush_logger():
	for handler in logger.handlers:
		handler.flush()


app = FastAPI(title="Exsclaim API", docs_url=None, redoc_url=None, on_shutdown=[flush_logger])
app.openapi = my_schema
for _dir in ("results", "logs"):
	path = Path("/exsclaim") / _dir
	path.mkdir(exist_ok=True, parents=True)
logger = get_logger()
_EXAMPLE_UUID = UUID("875be91d-97d9-445b-b281-db9b4997abbb")


class NTFY(BaseModel):
	"""A base model representing the necessary info to send an NTFY notification."""
	link: str
	access_token: str = None
	"""The access token that may be needed to send the NTFY notification as stated in https://docs.ntfy.sh/publish/#access-tokens"""
	priority: Annotated[int, FastPath(title="The priority of the message", ge=1, le=5)] = 3
	"""The priority of the message as stated in https://docs.ntfy.sh/publish/#message-priority"""

	def to_json(self):
		return {
			"url": self.link,
			"access_token": self.access_token,
			"priority": str(self.priority),
		}


class Query(BaseModel):
	name: str
	journal_family: exsclaim.COMPATIBLE_JOURNALS = "Nature"
	"""The Journal Family that EXSCLAIM should look through."""
	maximum_scraped: int = 5
	"""The maximum number of articles that EXSCLAIM should scrape. \
	Maximum does not specify how many articles will be scraped before the process ends, only what the upper limit is."""
	sortby: Literal["relevant", "recent"] = "relevant"
	"""How the search feature should sort the articles, by the relevancy or the recent publish date."""
	term: str
	"""The term or phrase that you want searched."""
	synonyms: list[str] = []
	"""Any synonyms that you're term might be related to."""
	save_format: list[Literal["subfigures", "visualization", "boxes", "postgres", "csv", "mongo"]] = ["boxes"]
	open_access: bool = False
	"""Determines if EXSCLAIM only uses open-access articles (True)."""
	llm: exsclaim.COMPATIBLE_LLMS = "gpt-3.5-turbo"
	"""The Large Language Model (LLM) that is used to separate captions and generate keywords for articles and figures."""
	model_key: str = ""
	"""The API key that might be needed depending on the specified llm."""
	emails: list[str] = []
	"""The email address that will receive a notification when EXSCLAIM has finished running."""
	ntfy: list[NTFY] = []
	"""A list of NTFY links that will receive a notification when EXSCLAIM has finished running."""


@app.get("/", include_in_schema=False)
async def dark_theme(light_mode:bool=False):
	schema = app.openapi()
	return get_swagger_ui_html(
		openapi_url=app.openapi_url,
		title=schema["info"]["title"],
		swagger_css_url="/swagger-dark-ui.css" if not light_mode else "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
		swagger_favicon_url="/favicon.ico"
	)


@app.get("/docs", include_in_schema=False)
def docs_redirect() -> Response:
	return Response(status_code=301, headers={"Location": "/"})


@app.get("/redoc", include_in_schema=False)
async def redoc():
	schema = app.openapi()
	return get_redoc_html(
		openapi_url=app.openapi_url,
		title=schema["info"]["title"],
		redoc_favicon_url="https://raw.githubusercontent.com/MaterialEyes/exsclaim2.0/b22ed4009c63ddd58d8415c5882ab58febde691c/dashboard/public/favicon.ico"
	)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
	if hasattr(app, "favicon"):
		return Response(app.favicon, media_type="image/x-icon", status_code=200)

	favicon_link = "https://raw.githubusercontent.com/MaterialEyes/exsclaim2.0/b22ed4009c63ddd58d8415c5882ab58febde691c/dashboard/public/favicon.ico"
	response = get(favicon_link)
	if not response.ok:
		return Response(status_code=301, headers={"Location": favicon_link})

	app.favicon = response.content
	return Response(app.favicon, media_type="image/x-icon", status_code=200)


@app.get("/swagger-dark-ui.css", include_in_schema=False)
def get_dark_css() -> Response:
	return get_dark_ui(False)


@app.get("/swagger-dark-ui.css.map", include_in_schema=False)
def get_dark_css() -> Response:
	return get_dark_ui(True)


def get_dark_ui(map_file:bool=False) -> Response:
	"""An endpoint to get around an error retrieving the Dark UI CSS file from jcphlux on GitHub."""
	dark_ui = "https://raw.githubusercontent.com/jcphlux/swagger-ui-themes/main/docs/css/swagger-dark-ui.css"
	if map_file:
		dark_ui += ".map"
	response = get(dark_ui)
	if not response.ok:
		return Response(status_code=301, headers={"Location": dark_ui})

	return Response(response.content, media_type="text/css", status_code=200, headers={"Location": dark_ui})


@app.get("/healthcheck",
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
def healthcheck(request:Request) -> Response:
	db_url = get_database_connection_string()
	try:
		db = connect(db_url)
		cursor = db.cursor()
		cursor.execute("SELECT * FROM results;")
		cursor.close()
		db.close()
		response = Response(f"EXSCLAIM! version {exsclaim.__version__} is running fine.",
							status_code=200, media_type="text/plain")
	except OperationalError as e:
		logger.exception(f"Database URL: {db_url}. {e}")
		response = Response("The API is running but cannot connect to the database.",
							status_code=503, media_type="text/plain")
	except UndefinedTable as e:
		logger.exception(e)
		response = Response("The API and database are both running, however, the database seems to empty. Please try again later.",
							status_code=503, media_type="text/plain")
	except Exception as e:
		logger.exception(f"Database URL: {db_url}. {e}")
		response = Response("A fundamental error has prevented the API from functioning.",
							status_code=503, media_type="text/plain")

	if request.headers.get("Accept") == "application/json":
		response = JSONResponse({"message": response.body.decode(response.charset)}, status_code=response.status_code, media_type="application/json")

	flush_logger()
	return response


@app.post("/query", responses={
	200: {
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
})
def query(request:Request, search_query: Query) -> Response:
	send_json = request.headers.get("accept", "") == "application/json"
	try:
		with connect(get_database_connection_string()) as db:
			cursor = db.cursor()
			cursor.execute("SELECT uuid_generate_v4() AS uuid;")
			uuid = str(cursor.fetchone()[0])

			results_dir = Path("/exsclaim") / "results" / uuid
			results_dir.mkdir(exist_ok=True, parents=True)

			exsclaim_input = {
				"name": search_query.name if search_query else "exsclaim_results",
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
				"openai_API": search_query.model_key,
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
				dump(exsclaim_input, f)
			Popen(["python3", str(Path(__file__).parent / "run_exsclaim.py"), uuid, str(results_dir / "search_query.json")],
				  start_new_session=True,
			)

			db_json = exsclaim_input.copy()
			db_json["openai_API"] = "openai_API" in db_json.keys()
			for unnecessary_key in ["notifications", "results_dir", "logging"]:
				if unnecessary_key in db_json:
					db_json.pop(unnecessary_key)

			cursor.execute("INSERT INTO results(id, search_query, extension) VALUES(%s, %s, %s);", (uuid, dumps(db_json), "tar.gz"))
			db.commit()
			cursor.close()

		if send_json:
			response = JSONResponse({"message": "Thank you, your request is currently being processed.", "result_id": str(uuid)},
									status_code=200, media_type="application/json")
		else:
			response = Response(f"Thank you, your request is currently being processed, and the results can be found using id: {uuid}.",
						status_code=200, media_type="text/plain")
	except OperationalError as e:
		logger.exception(e)
		message = "An error occurred connecting to the database. Please try again later."
		if send_json:
			response = JSONResponse({"message": message}, status_code=500, media_type="application/json")
		else:
			response = Response(message, status_code=500,
								media_type="text/plain")
	except Exception as e:
		logger.exception(e)
		message = "An unknown error occurred within the EXSCLAIM! API. Please try again later."
		if send_json:
			response = JSONResponse({"message": message}, status_code=503, media_type="application/json")
		else:
			response = Response(message, status_code=503, media_type="text/plain")

	flush_logger()
	return response


def ensure_uuid(uuid: str | UUID) -> UUID:
	if isinstance(uuid, UUID):
		return uuid

	try:
		return UUID(uuid)
	except ValueError:
		raise ValueError(f"\"{uuid}\" is not a valid UUID.")


@app.get("/status/{result_id}",
		 responses={
			 200: {
				 "description": "Known Status Found.",
				 "content": {
					 "application/json": {
						 "schema": {
							 "type": "object",
							 "properties": {
								 "status": {
									 "type": "string",
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
def status(result_id: str | UUID) -> JSONResponse:
	try:
		result_id = ensure_uuid(result_id)
	except ValueError as e:
		return JSONResponse({"status": None, "message": str(e)}, status_code=422, media_type="application/json")

	try:
		with connect(get_database_connection_string()) as db:
			cursor = db.cursor()
			cursor.execute("SELECT status, start_time, end_time FROM results WHERE id = %s", (result_id,))
			results = cursor.fetchone()
			if results is None:
				return JSONResponse({"status": "Not Found", "message": f"There is no query recorded in our database with id: \"{result_id}\"."}, status_code=404, media_type="application/json")

			status, start_time, end_time = results

			try:
				time_diff = end_time - start_time
			except TypeError:
				time_diff = dt.now() - start_time

			match status:
				case "Running":
					status_code = 200
				case "Finished":
					status_code = 200
				case "Closed due to an error":
					status_code = 500
				case _:
					status_code = 200

		response = JSONResponse({"status": f"{status}.", "start_time": date_to_json(start_time), "end_time": date_to_json(end_time),
								 "run_time": time_diff.total_seconds()}, status_code=status_code, media_type="application/json")
	except OperationalError as e:
		logger.exception(e)
		response = JSONResponse({"status": "Unknown", "message": "An unknown error has occurred within the database. Please try again later."},
								status_code=503, media_type="application/json")

	flush_logger()
	return response


@app.get("/results/{result_id}",
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
			 500: {
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
		 })
def download(request:Request, result_id:UUID, compression:str="default", filename:Literal["name", "id"]="id") -> Response:
	# Set the filename to be id by default
	try:
		result_id = ensure_uuid(result_id)
	except ValueError as e:
		return Response(str(e), status_code=422, media_type="text/plain")

	if compression != "default":
		if compression not in _ARCHIVE_FORMATS.keys():
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

	with connect(get_database_connection_string()) as db:
		cursor = db.cursor()
		cursor.execute("SELECT status FROM results WHERE id = %s", (result_id,))
		results = cursor.fetchone()
		if results is None:
			return Response(f"There is no query recorded in our database with id: \"{result_id}\".", status_code=404, media_type="text/plain")

	match results[0]:
		case "Running":
			return Response("The results are still being compiled.", status_code=202, media_type="text/plain")
		case "Closed due to an error":
			return Response("The results could not be compiled due to an error. Please submit your query again.",
							status_code=500, media_type="text/plain")
		case "Finished":
			# Passing so the indentation level doesn't need to be kept up
			pass
		case _:
			return Response(f"The database has an unknown status for id \"{result_id}\" and cannot send the results at this time.",
							status_code=501, media_type="text/plain")

	results_file = (Path("/exsclaim") / "results" / str(result_id)).with_suffix(".tar.gz")
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

		return Response(content=buffer.getvalue(), media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename*=utf8''{filename}"})
	except ValueError as e:
		return Response(str(e), status_code=422, media_type="text/plain")


@app.get("/compression_types",
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
def get_possible_compressions(request:Request, compression_type:str = None) -> Response:
	send_json = request.headers.get("accept", "") == "application/json"
	if compression_type is None:
		compression_types = list(_ARCHIVE_FORMATS.keys())
		if send_json:
			return JSONResponse({"compression_types": compression_types}, status_code=200, media_type="application/json")
		return Response(str(compression_types), status_code=200, media_type="text/plain")

	allowed = compression_type in _ARCHIVE_FORMATS.keys()
	status_code = 202 if allowed else 404
	if send_json:
		return JSONResponse({"allowed": allowed}, status_code=status_code, media_type="application/json")

	return Response(f"{compression_type} is {'NOT ' if not allowed else ''}an available compression type.", status_code=status_code, media_type="text/plain")
