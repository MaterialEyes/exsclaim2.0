import exsclaim
import logging
import pathlib

from datetime import datetime as dt, timedelta as td
from fastapi import FastAPI, Response, Path
from json import dump, dumps
from os import getenv
from psycopg import connect, OperationalError
from psycopg.errors import UndefinedTable
from pydantic import BaseModel
from subprocess import Popen
from typing import Any, Annotated, Union, Literal
from threading import Thread
from uuid import UUID


def get_database_connection_string() -> str:
	username = getenv("POSTGRES_USER", "exsclaim")
	password = getenv("POSTGRES_PASSWORD", "exsclaimtest!9700")
	port = getenv("POSTGRES_PORT", "5432")
	database_name = getenv("POSTGRES_DB", "exsclaim")
	host = getenv("POSTGRES_HOST", "db")

	# db is one of the aliases given through Docker Compose
	url = f'postgres://{username}:{password}@{host}:{port}/{database_name}'
	return url


printer_handler = logging.StreamHandler()
printer_handler.setFormatter(exsclaim.PrinterFormatter())
file_handler = logging.FileHandler("/exsclaim/logs/exsclaim-api.log", "a")
file_handler.setFormatter(exsclaim.ExsclaimFormatter())

logging.basicConfig(level=logging.INFO,
					handlers=(printer_handler, file_handler),
					force=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Exsclaim API")


class Item(BaseModel):
	"""Test for the name of the class"""
	name: str
	price: float
	is_offer: Union[bool, None] = None


class NTFY(BaseModel):
	"""A base model representing the necessary info to send an NTFY notification."""
	link: str
	access_token: str = None
	"""The access token that may be needed to send the NTFY notification as stated in https://docs.ntfy.sh/publish/#access-tokens"""
	priority: Annotated[int, Path(title="The priority of the message", ge=1, le=5)] = 3
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
	save_format: list[Literal["subfigures", "visualization", "boxes", "postgres", "csv", "mongo"]] = ["mongo"]
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


@app.get("/")
def read_root():
	return "Welcome to the EXSCLAIM! API."


@app.get("/healthcheck")
def healthcheck() -> Response:
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

	return response


@app.post("/query")
def query(search_query: Query) -> Response:
	try:
		with connect(get_database_connection_string()) as db:
			cursor = db.cursor()
			cursor.execute("SELECT uuid_generate_v4() AS uuid;")
			uuid = str(cursor.fetchone()[0])

			results_dir = pathlib.Path("/exsclaim") / "results" / uuid
			results_dir.mkdir(exist_ok=True, parents=True)

			exsclaim_input = {
				"name": search_query.name,
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
			Popen(["python3", str(pathlib.Path(__file__).parent / "run_exsclaim.py"), uuid, str(results_dir / "search_query.json")],
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

		return Response(f"Thank you, your request is currently being processed, and the results can be found using id: {uuid}.",
					status_code=200, media_type="text/plain")
	except OperationalError as e:
		logger.exception(e)
		return Response("An error occurred connecting to the database. Please try again later.", status_code=500,
						media_type="text/plain")
	except Exception as e:
		logger.exception(e)
		return Response("An unknown error occurred within the EXSCLAIM! API. Please try again later.", status_code=503, media_type="text/plain")


@app.get("/status/{result_id}")
def status(result_id: str | UUID) -> Response:
	if isinstance(result_id, str):
		try:
			result_id = UUID(result_id)
		except ValueError:
			return Response("The result ID inserted is not a valid UUID, try again with a correct value.", status_code=422, media_type="text/plain")

	try:
		with connect(get_database_connection_string()) as db:
			cursor = db.cursor()
			cursor.execute("SELECT status, start_time, end_time FROM results WHERE id = %s", (result_id,))
			results = cursor.fetchone()
			if results is None:
				return Response(f"There is no query recorded in our database with id: \"{result_id}\".", status_code=404, media_type="text/plain")

			status, start_time, end_time = results

			match status:
				case "Running":
					# TODO: Make this human readable
					time_diff = dt.now() - start_time
					response = Response(f"The query was started {time_diff} ago and is still currently running.", status_code=200, media_type="text/plain")
				case "Finished":
					response = Response(f"The query finished execution at {end_time}.", status_code=200, media_type="text/plain")
				case "Closed due to an error":
					response = Response(f"The query stopped running at {end_time} due to an error.", status_code=500, media_type="text/plain")
				case _:
					response = Response(status, status_code=200, media_type="text/plain")
	except OperationalError as e:
		logger.exception(e)
		response = Response("An unknown Internal Server Error has occurred. Please try again later.", status_code=500, media_type="text/plain")

	return response

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
	return {"item_id": item_id, "q": q}


@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
	return {"item_name": item.name, "item_id": item_id}
