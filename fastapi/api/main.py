import exsclaim
import logging
import pathlib

from fastapi import FastAPI, Response, Path
from json import dumps
from os import getenv
from psycopg import connect, OperationalError
from pydantic import BaseModel
from typing import Any, Annotated, Union, Literal
from threading import Thread


def get_database_connection_string() -> str:
	username = getenv("POSTGRES_USER", "exsclaim")
	password = getenv("POSTGRES_PASSWORD", "exsclaimtest!9700")
	port = getenv("POSTGRES_PORT", "5432")
	database_name = getenv("POSTGRES_DB", "exsclaim")

	# db is one of the aliases given through Docker Compose
	url = f'postgres://{username}:{password}@db:{port}/{database_name}'
	return url


printer_handler = logging.StreamHandler()
printer_handler.setFormatter(exsclaim.PrinterFormatter())
file_handler = logging.FileHandler("/logs/exsclaim-api.log", "a")
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
	"""The access token that may be needed to send the NTFY notification as stated in https://docs.ntfy.sh/publish/#access-tokens"""
	access_token: str = None
	"""The priority of the message as stated in https://docs.ntfy.sh/publish/#message-priority"""
	priority: Annotated[int, Path(title="The priority of the message", ge=1, le=5)] = 3


class Query(BaseModel):
	name: str
	"""The Journal Family that EXSCLAIM should look through."""
	journal_family: exsclaim.COMPATIBLE_JOURNALS = "Nature"
	"""The maximum number of articles that EXSCLAIM should scrape. \
	Maximum does not specify how many articles will be scraped before the process ends, only what the upper limit is."""
	maximum_scraped: int = 5
	"""How the search feature should sort the articles, by the relevancy or the recent publish date."""
	sortby: Literal["relevant", "recent"] = "relevant"
	"""The term of phrase that you want searched."""
	term: str
	"""Any synonyms that you're term might be related to."""
	synonyms: list[str] = []
	save_format: Literal["subfigures", "visualization", "boxes", "postgres", "csv", "mongo"] = "mongo"
	"""Determines if EXSCLAIM only uses open-access articles (True)."""
	open_access: bool = False
	"""The Large Language Model (LLM) that is used to separate captions and generate keywords for articles and figures."""
	llm: exsclaim.COMPATIBLE_LLMS = "gpt-3.5-turbo"
	"""The API key that might be needed depending on the specified llm."""
	llm_token: str = ""
	"""The email address that will receive a notification when EXSCLAIM has finished running."""
	emails: list[str] = []
	"""A list of NTFY links that will receive a notification when EXSCLAIM has finished running."""
	ntfy: list[NTFY] = []


@app.get("/")
def read_root():
	return "Welcome to the EXSCLAIM! API."


@app.get("/healthcheck")
def healthcheck():
	return f"EXSCLAIM! version {exsclaim.__version__} is running fine."


def run_query(query:dict) -> dict:
	try:
		test_pipeline = exsclaim.Pipeline(query)
		results = test_pipeline.run(
			html_scraper=False
		)

		with tar_open(f"/results/{uuid}.tar.gz", "w:gz") as tar:
			tar.add(results_dir / exsclaim_input["name"], arcname=exsclaim_input["name"])

		system(f"rm -rf {results_dir}")
		return results
	except NameError as e:
		logger.exception(e)
		return {}


@app.post("/query")
def query(search_query: Query) -> Response:
	try:
		with connect(get_database_connection_string()) as db:
			cursor = db.cursor()
			cursor.execute("SELECT uuid_generate_v4() AS uuid;")
			uuid = str(cursor.fetchone()[0])

			results_dir = pathlib.Path("/results") / uuid
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
				"openai_API": search_query.llm_token,
				"open": search_query.open_access,
				"save_format": search_query.save_format,
				"logging": ["exsclaim.log"],
				"results_dir": str(results_dir)
			}

			thread = Thread(target=run_query, args=(exsclaim_input,))
			thread.start()

			db_json = exsclaim_input.copy()
			db_json["openai_API"] = "openai_API" in db_json.keys()
			for unnecessary_key in ["notifications", "results_dir", "logging"]:
				if unnecessary_key in db_json:
					db_json.pop(unnecessary_key)

			cursor.execute("INSERT INTO results(id, search_query, extension) VALUES(%s, %s, %s);", (uuid, dumps(db_json), "tar.gz"))
			db.commit()
			cursor.close()

		try:
			return Response(f"Thank you, your request is currently being processed, and the results can be found using id: {uuid}.",
						status_code=200, media_type="text/plain")
		finally:
			thread.join()
	except OperationalError as e:
		logger.exception(e)
		return Response("An error occurred connecting to the database. Please try again later.", status_code=500,
						media_type="text/plain")
	except Exception as e:
		logger.exception(e)
		return Response("An unknown error occurred. Please try again later.", status_code=500, media_type="text/plain")


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
	return {"item_id": item_id, "q": q}


@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
	return {"item_name": item.name, "item_id": item_id}
