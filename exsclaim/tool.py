# Copyright 2019 MaterialEyes
# (see accompanying license files for details).

"""Definition of the ExsclaimTool classes.
This module defines the central objects in the EXSCLAIM!
package. All the model classes are independent of each
other, but they expose the same interface, so they are
interchangeable.
"""
from .caption import LLM, LLMUsage, OptionalSemaphore
from .config import settings
from .exceptions import PipelineInterruptionException, JournalScrapeError
from .journals import JournalFamily
from .utilities import initialize_results_dir, PrinterFormatter

from abc import ABC, abstractmethod
from json import dump, load, JSONEncoder
from logging import getLogger, StreamHandler
from os import PathLike
from pathlib import Path
from time import time_ns as timer
from typing import Any, Callable, Collection, Iterable, Optional

import asyncio
import numpy as np
import re

if settings.DISPLAY_TQDM:
	from tqdm.asyncio import tqdm_asyncio
	# from tqdm.contrib.logging import logging_redirect_tqdm
	from .utilities.tqdm import tqdm_logging_redirect


__all__ = ["ExsclaimTool", "JournalScraper", "CaptionDistributor"]


class ExsclaimEncoder(JSONEncoder):
	def default(self, obj):
		if isinstance(obj, np.integer):
			print(obj)
			return int(obj)
		elif isinstance(obj, np.floating):
			print(obj)
			return float(obj)
		return super().default(obj)


class ExsclaimTool(ABC):
	def __init__(self, search_query, **kwargs):
		logger = kwargs.get("logger", None)
		if logger is None:
			logger = getLogger(kwargs.get("logger_name", __name__))
			# set up logging / printing
			if "print" in search_query.get("logging", []):
				handler = StreamHandler()
				handler.setFormatter(PrinterFormatter())
				logger.addHandler(handler)

		self.logger = logger
		self.search_query = search_query

	async def __aenter__(self):
		await self.load()

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		await self.unload()

	async def load(self):
		...

	async def unload(self):
		...

	@property
	def search_query(self) -> dict:
		return self._search_query

	@search_query.setter
	def search_query(self, search_query: dict[str, Any] | Path):
		"""initializes search query as instance attribute

		Args:
			search_query (a dict or path to dict): The Query JSON
		"""
		if not isinstance(search_query, dict):
			try:
				with open(search_query) as f:
					# Load query file to dict
					search_query = load(f)
			except Exception as e:
				self.logger.exception(f"Search Query must be a dictionary or pathlib.Path, not {search_query.__class__.__name__}.", exc_info=e)
				raise PipelineInterruptionException("Could not validate the search query passed.") from e

		self._search_query = search_query

		# Set up file structure
		self.results_directory = initialize_results_dir(self.search_query)

	def _appendJSON(self, exsclaim_json:dict, exsclaim_filename: PathLike[str] = None, data: Iterable[str] = None,
					filename: str | PathLike[str] = None):
		"""Commit updates to exsclaim json and update list of scraped articles

		Args:
			filename (string): File in which to store the updated EXSCLAIM JSON
			exsclaim_json (dict): Updated EXSCLAIM JSON
		"""
		if exsclaim_filename is None:
			exsclaim_filename = self.results_directory / "exsclaim.json"
		with open(exsclaim_filename, 'w', encoding="utf-8") as f:
			dump(exsclaim_json, f, indent='\t', cls=ExsclaimEncoder)

		if data is None and filename is None:
			return

		if (data is None) ^ (filename is None):
			raise ValueError("If additional data is provided, the filename to append the data to must also be provided.")

		with open(self.results_directory / filename, "a+", encoding="utf-8") as f:
			for item in data:
				f.write(f"{item}\n")

	def _update_exsclaim(self, exsclaim_dict:dict, article_dict:dict, *args, **kwargs):
		"""Update the exsclaim_dict with article_dict contents

		Args:
			exsclaim_dict (dict): An EXSCLAIM JSON
			article_dict (dict):
		Returns:
			exsclaim_dict (dict): EXSCLAIM JSON with article_dict
				contents added.
		"""
		exsclaim_dict.update(article_dict)
		return exsclaim_dict

	@staticmethod
	def _start_timer() -> int:
		return timer()

	def _end_timer(self, start: int, context: str, idx: Optional[int] = None, total: Optional[int] = None):
		# The timer measures in nanoseconds, this will convert it to seconds
		time_diff = (timer() - start) / 1e9
		context = f"\t({context})" if context else ""
		message = f">>> Time Elapsed: {time_diff:,.2f} sec{context}"
		if idx is not None:
			message += f"\t[{idx:,} of {total:,}]"
		self.display_info(message + "\n")

	@abstractmethod
	async def check_search_query(self, query_dict: dict[str, Any]):
		"""Checks if any values from the search query would cause the pipeline to crash later on, such as an invalid API key for the LLM or a missing model for the Figure Separator."""
		...

	@abstractmethod
	async def run(self, search_query: dict, exsclaim_json: dict):
		pass

	async def _await_task_completions(self, tasks: Collection[asyncio.Task], t0: int, units: str, tqdm_desc: Callable[[str], str]):
		num_items = len(tasks)
		if not settings.DISPLAY_TQDM:
			for i, future in enumerate(asyncio.as_completed(tasks), start=1):
				_id = await future
				self._end_timer(t0, f"{self.__class__.__name__}: {_id}", i, num_items)
		else:
			pbar = tqdm_asyncio(asyncio.as_completed(tasks), total=num_items,
			                    desc=tqdm_desc)
			with tqdm_logging_redirect(self.logger):
				for f in pbar:
					await f

		self._end_timer(t0, f"{num_items:,} {units}")

	def display_info(self, info):
		"""Display information to the user as the specified in the query

		Args:
			info (str): A string to display (either to stdout, a log file)
		"""
		self.logger.info(info)

	def display_exception(self, e: Exception, figure_path: str):
		error_msg = f"<!> ERROR: An exception occurred in {self.__class__.__name__} on figure: {figure_path}."
		self.logger.exception(error_msg, exc_info=e)


class JournalScraper(ExsclaimTool):
	"""
	JournalScraper object.
	Extract scientific figures from journal articles by passing
	a json-style search query to the run method
	Parameters:
	None
	"""
	def __init__(self, search_query:dict, **kwargs):
		kwargs.setdefault("logger_name", __name__ + ".JournalScraper")
		super().__init__(search_query, **kwargs)
		self.new_articles_visited = set()

	def _appendJSON(self, exsclaim_json: dict, data: Iterable[str] = None, filename: Optional[str] = None):
		"""Commit updates to exsclaim json and update list of scraped articles

		Args:
			filename (string): File in which to store the updated EXSCLAIM JSON
			exsclaim_json (dict): Updated EXSCLAIM JSON
		"""
		super()._appendJSON(exsclaim_json, data=map(lambda article: article.split('/')[-1], data), filename=filename)

	async def _handle_scrape_error(self, e: JournalScrapeError):
		self.logger.exception("An error occurred during the journal scraping.", exc_info=e)
		if (error_dir := settings.UNSCRAPED_HTML_PATH) is not None:
			if e.url is not None and e.html is not None:
				error_dir.mkdir(parents=True, exist_ok=True)

				with open(error_dir / f"{e.url.split('/')[-1]}.html", 'w') as f:
					f.write(await e.html.prettify())

	async def check_search_query(self, query_dict: dict[str, Any]):
		...

	async def task(self, exsclaim_json: dict, journal: JournalFamily, article: str, html_directory: Path,
					 lock: asyncio.Lock):
		# Extract figures, captions, and metadata from each article
		self.display_info(f">>> Extracting figures from: {journal.get_article_name_from_url(article)}")
		url = journal.domain + article

		try:
			article_dict = await journal.get_article_figures(url, html_directory)

			if article_dict:
				async with lock:
					self._update_exsclaim(exsclaim_json, article_dict)
			self.new_articles_visited.add(article)
		except JournalScrapeError as e:
			self.logger.exception(f"Could not scrape the details for {url}.")
			await self._handle_scrape_error(e)
			raise e
		except Exception as e:
			self.display_exception(e, article)
		return article

	async def run(self, search_query: dict, exsclaim_json: dict):
		"""Run the JournalScraper to find relevant article figures

		Args:
			exsclaim_json (dict): An EXSCLAIM JSON to store results in
		Returns:
			exsclaim_json (dict): Updated with results of search
		"""

		# Initialize the subclass object based on the user input
		search_query = self.search_query
		exsclaim_json = exsclaim_json or dict()

		# List of objects (articles) that have already been separated
		already_done = self.results_directory / "_articles"

		if already_done.is_file():
			with open(already_done, "r", encoding="utf-8") as f:
				separated = {line.strip() for line in f.readlines()}
		else:
			separated = set()

		with open(already_done, "w", encoding="utf-8") as f:
			for figure in separated:
				f.write(f"{Path(figure).name}\n")

		html_directory = self.results_directory / "html"
		html_directory.mkdir(exist_ok=True)

		self.display_info(f"Running Journal Scraper\n")

		lock = asyncio.Lock()
		journal = JournalFamily.from_search_query(search_query)

		async with journal:
			try:
				extensions = await journal.get_article_extensions()
			except JournalScrapeError as e:
				await self._handle_scrape_error(e)
				raise

			async with asyncio.TaskGroup() as tg:
				t0 = self._start_timer()
				tasks = [tg.create_task(self.task(exsclaim_json, journal, extension, html_directory, lock))
						 for extension in extensions]

				await self._await_task_completions(tasks, t0, "articles", "Scraping articles from {}".format)

		self._appendJSON(exsclaim_json, data=separated, filename="_articles")
		return exsclaim_json


class CaptionDistributor(ExsclaimTool):
	"""
	CaptionDistributor object.
	Distribute subfigure caption chunks from full figure captions
	in an exsclaim_dict using custom caption nlp tools
	Parameters:
	model_path: str
		Absolute path to caption nlp model
	"""

	def __init__(self, search_query: dict, **kwargs):
		kwargs.setdefault("logger_name", __name__ + ".CaptionDistributor")
		super().__init__(search_query, **kwargs)
		self.llm: LLM = LLM.from_search_query(search_query, run_id=kwargs.get("run_id"))

	def _update_exsclaim(self, search_query, exsclaim_dict, figure_name, caption_dict: dict[str, str],
						 keywords: Collection[str], usage: LLMUsage):
		empty_list_regex = re.compile(r"\s*\[\s*]\s*")

		for label, capt in caption_dict.items():
			if empty_list_regex.match(capt):
				capt = ""

			master_image = {
				"label": label,
				"description": capt,
				"keywords": keywords,
				"input_tokens": usage.input_tokens,
				"output_tokens": usage.output_tokens
			}
			exsclaim_dict[figure_name]["unassigned"]["captions"].append(master_image)
		return exsclaim_dict

	def _appendJSON(self, exsclaim_json: dict, data: Iterable[str] = None, filename: Optional[str] = None):
		"""Commit updates to EXSCLAIM JSON and updates list of ed figures

		Args:
			results_directory (string): Path to results directory
			exsclaim_json (dict): Updated EXSCLAIM JSON
			figures_separated (set): Figures which have already been separated
		"""
		super()._appendJSON(exsclaim_json, data=map(lambda figure: figure.split('/')[-1], data), filename=filename)

	async def load(self):
		self.logger.info(f"Loading LLM: {self.llm.model}.")
		load_status = await self.llm.load(logger=self.logger)
		if load_status:
			self.logger.info(f"Finished loading LLM: {self.llm.model}.")

	async def unload(self):
		self.logger.info(f"Unloading LLM: {self.llm.model}.")
		await self.llm.unload(logger=self.logger)
		self.logger.info(f"Finished unloading LLM: {self.llm.model}.")

	async def check_search_query(self, query_dict: dict[str, Any]):
		self.llm.validate_search_query(query_dict)

	async def _task(self, exsclaim_json: dict, search_query: dict, figure: str, new_separated: set, lock: asyncio.Lock,
					 semaphore: OptionalSemaphore):
		async with semaphore:
			try:
				caption_text = exsclaim_json[figure]["full_caption"]

				caption_dict, keywords, usage = await self.llm.parse_captions(caption_text)

				if caption_dict is not None:
					self.logger.debug(f"Full caption dict: \"{caption_dict}\".")
					async with lock:
						self._update_exsclaim(search_query, exsclaim_json, figure, caption_dict, keywords, usage)
						new_separated.add(figure)
				else:
					self.logger.exception(f"Could not find full caption in {figure}.")

			except Exception as e:
				self.display_exception(e, figure)

		return figure

	async def run(self, search_query: dict, exsclaim_json: dict, limit_llms_to: Optional[int] = None):
		"""Run the CaptionDistributor to distribute subfigure captions

		Args:
			search_query (dict): A Search Query JSON to guide search
			exsclaim_json (dict): An EXSCLAIM JSON to store results in
			limit_llms_to (int | None): Limit the number of llms to run at once. None will remove the limit.
		Returns:
			exsclaim_json (dict): Updated with results of search
		"""
		exsclaim_json = exsclaim_json or dict()
		self.display_info(f"Running Caption Distributor\n")

		t0 = self._start_timer()
		# List of objects (figures, captions, etc) that have already been separated
		already_done = self.results_directory / "_captions"

		if already_done.is_file():
			with open(already_done, "r", encoding="utf-8") as f:
				separated = {line.strip() for line in f.readlines()}
		else:
			separated = set()

		with open(already_done, "w", encoding="utf-8") as f:
			for figure in separated:
				f.write(f"{Path(figure).name}\n")
		# Figure extra goes here
		new_separated = set()

		figures = [
			value["figure_name"]
			for value in exsclaim_json.values()
			if value["figure_name"] not in separated
		]

		lock = asyncio.Lock()
		concurrency = self.llm.request_concurrency()
		semaphore = OptionalSemaphore(concurrency)

		async with asyncio.TaskGroup() as tg:
			tasks = [tg.create_task(self._task(exsclaim_json, search_query, _path, new_separated, lock, semaphore))
			         for _path in figures]

			await self._await_task_completions(tasks, t0, "captions", "Distributing captions from {}".format)

		self._appendJSON(exsclaim_json, data=new_separated, filename="_captions")
		return exsclaim_json
