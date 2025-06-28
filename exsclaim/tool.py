# Copyright 2019 MaterialEyes
# (see accompanying license files for details).

"""Definition of the ExsclaimTool classes.
This module defines the central objects in the EXSCLAIM!
package. All the model classes are independent of each
other, but they expose the same interface, so they are
interchangeable.
"""

from .caption import LLM #, get_context
from .figures import apply_mask
from .journal import JournalFamily
from .utilities import initialize_results_dir, PrinterFormatter

from abc import ABC, abstractmethod
from asyncio import gather, Lock
from json import dump, load, JSONEncoder
from logging import getLogger, StreamHandler
from os import PathLike, getenv
from pathlib import Path
from re import search
from time import time_ns as timer
from typing import Iterable

import numpy as np


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

	async def load(self):
		...

	@property
	def search_query(self) -> dict:
		return self._search_query

	@search_query.setter
	def search_query(self, search_query):
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
				self.logger.debug(f"Search Query must be a pathlib.Path or dictionary, not {search_query.__class__.__name__}.")
				self.logger.exception(e)

		self._search_query = search_query

		# Set up file structure
		self.results_directory = initialize_results_dir(self.search_query.get("results_dir", None)) / self.search_query["name"]

	def _appendJSON(self, exsclaim_json:dict, exsclaim_filename:PathLike[str]=None, data:Iterable[str]=None,
					filename:str|PathLike[str]=None):
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

	def _end_timer(self, t0:int, context:str):
		# The timer measures in nanoseconds, this will convert it to seconds
		time_diff = (timer() - t0) / 1e9
		context = f"\t({context})" if context else ""
		self.display_info(f">>> Time Elapsed: {time_diff:,.2f} sec{context}\n")

	@abstractmethod
	async def run(self, search_query:dict, exsclaim_json:dict):
		pass

	def display_info(self, info):
		"""Display information to the user as the specified in the query

		Args:
			info (str): A string to display (either to stdout, a log file)
		"""
		self.logger.info(info)

	def display_exception(self, e:Exception, figure_path):
		error_msg = f"<!> ERROR: An exception occurred in {self.__class__.__name__} on figure: {figure_path}. Exception: {e}"
		self.logger.exception(error_msg)


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

	def _appendJSON(self, exsclaim_json):
		"""Commit updates to exsclaim json and update list of scraped articles

		Args:
			filename (string): File in which to store the updated EXSCLAIM JSON
			exsclaim_json (dict): Updated EXSCLAIM JSON
		"""
		super()._appendJSON(exsclaim_json, data=map(lambda article: article.split('/')[-1], self.new_articles_visited), filename="articles")

	def _run_loop_function(self, search_query, exsclaim_json: dict, figure: Path, new_separated: set):
		return exsclaim_json

	async def runner(self, exsclaim_json:dict, search_query:dict, article:str, journal_family_name:str, lock:Lock):
		# Extract figures, captions, and metadata from each article
		t0 = self._start_timer()
		self.display_info(f">>> Extracting figures from: {article.split('/')[-1]}")
		try:
			async with JournalFamily(journal_family_name, search_query,
								 scrape_hidden_articles=search_query.get("scrape_hidden_articles", False)) as journal:
			
				article_dict = await journal.get_article_figures(journal.domain + article)

			async with lock:
				self._update_exsclaim(exsclaim_json, article_dict)
			self.new_articles_visited.add(article)
		except Exception as e:
			self.display_exception(e, article)

		self._end_timer(t0, f"JournalScraper: {article}")

	async def run(self, search_query:dict, exsclaim_json:dict):
		"""Run the JournalScraper to find relevant article figures

		Args:
			exsclaim_json (dict): An EXSCLAIM JSON to store results in
		Returns:
			exsclaim_json (dict): Updated with results of search
		"""

		# Initialize the subclass object based on the user input
		search_query = self.search_query
		journal_family_name = search_query["journal_family"]
		exsclaim_json = exsclaim_json or dict()

		self.display_info(f"Running Journal Scraper\n")
		self.results_directory.mkdir(exist_ok=True)

		async with JournalFamily(journal_family_name, search_query,
								 scrape_hidden_articles=search_query.get("scrape_hidden_articles", False)) as journal:
			extensions = await journal.get_article_extensions()
			# extensions = ["/articles/s41467-025-56910-x"] # TODO: Find a test article that will have everything

		lock = Lock()
		await gather(*[
			self.runner(exsclaim_json, search_query, extension, journal_family_name, lock) for extension in extensions
		])

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

	def __init__(self, search_query:dict=None, **kwargs):
		kwargs.setdefault("logger_name", __name__ + ".CaptionDistributor")
		super().__init__(search_query if search_query is not None else {}, **kwargs)
		self.model_path = ""

	def _load_model(self):
		if "" in self.model_path:
			self.model_path = Path(__file__).parent / "captions" / "models"
		# return caption.load_models(self.model_path) # TODO: Find out where load_models comes from

	def _update_exsclaim(self, search_query, exsclaim_dict, figure_name, delimiter, caption_dict, keywords):
		exsclaim_dict[figure_name]["caption_delimiter"] = delimiter

		# Gets the figure number out of the figure name
		match = search(r"^.+_(fig\d+)\.\w{3,4}$", exsclaim_dict[figure_name]["figure_name"])
		if match is None:
			raise ValueError(f"Could not find figure number in name: {figure_name}.")
		figure_number = match.group(1)
		del match

		for label, capt in caption_dict.items():
			query = f"{figure_number}{label} {capt if capt else ''}"

			master_image = {
				"label": label,
				"description": capt,  # ["description"],
				"keywords": keywords,
				# "context": get_context(query, documents, embeddings),
				# "general": get_keywords(get_context(query, documents, embeddings), api, llm).split(', '),
			}
			exsclaim_dict[figure_name]["unassigned"]["captions"].append(master_image)
		return exsclaim_dict

	def _appendJSON(self, exsclaim_json: dict, data: Iterable[str] = None, filename:str=None):
		"""Commit updates to EXSCLAIM JSON and updates list of ed figures

		Args:
			results_directory (string): Path to results directory
			exsclaim_json (dict): Updated EXSCLAIM JSON
			figures_separated (set): Figures which have already been separated
		"""
		super()._appendJSON(exsclaim_json, data=map(lambda figure: figure.split('/')[-1], data), filename=filename)

	async def runner(self, exsclaim_json:dict, search_query:dict, figure:str, new_separated:set, lock:Lock):
		t0 = self._start_timer()
		self.display_info(f">>> Parsing captions from: {figure}")
		try:
			if figure == "s41929-023-01090-4_fig4.jpg":
				self.logger.error(
					f"There's an extra \"'\" in this {figure}'s caption that causes the JSON to not be parsed properly, skipping for now.")
				return exsclaim_json
			caption_text = exsclaim_json[figure]["full_caption"]

			delimiter = 0

			llm = search_query["llm"]
			model_key = search_query.get("model_key", None)
			llm = LLM(llm, model_key)

			caption_dict = await llm.separate_captions(caption_text) # separate_captions(caption_text, api, llm)
			# caption.associate_caption_text( # here add the gpt3 code separate_captions(caption_text) #
			#  model, caption_text, search_query["query"]
			# )
			keywords = await llm.get_keywords(caption_text)

			if caption_dict is not None:
				self.logger.debug(f"Full caption dict: \"{caption_dict}\".")
				async with lock:
					self._update_exsclaim(search_query, exsclaim_json, figure, delimiter, caption_dict, keywords)
					new_separated.add(figure)
			else:
				self.logger.exception(f"Could not find full caption in {figure}.")

		except Exception as e:
			self.display_exception(e, figure)

		self._end_timer(t0, f"CaptionDistributor: {figure}")

	async def run(self, search_query:dict, exsclaim_json:dict):
		"""Run the CaptionDistributor to distribute subfigure captions

		Args:
			search_query (dict): A Search Query JSON to guide search
			exsclaim_json (dict): An EXSCLAIM JSON to store results in
		Returns:
			exsclaim_json (dict): Updated with results of search
		"""
		search_query.setdefault("openai_API", getenv("OPENAI_API_KEY", None))
		exsclaim_json = exsclaim_json or dict()

		self.display_info(f"Running Caption Distributor\n")
		self.results_directory.mkdir(exist_ok=True)

		t0 = self._start_timer()
		# List of objects (figures, captions, etc) that have already been separated
		file = self.results_directory / "_captions"

		if file.is_file():
			with open(file, "r", encoding="utf-8") as f:
				separated = {line.strip() for line in f.readlines()}
		else:
			separated = set()

		with open(file, "w", encoding="utf-8") as f:
			for figure in separated:
				f.write(f"{Path(figure).name}\n")
		# Figure extra goes here
		new_separated = set()

		counter = 1
		figures = [
			value["figure_name"]
			for value in exsclaim_json.values()
			if value["figure_name"] not in separated
		]

		lock = Lock()
		await gather(*[
			self.runner(exsclaim_json, search_query, _path, new_separated, lock)
			for _path in figures
		])

		self._end_timer(t0, f"{counter:,} figures")
		self._appendJSON(exsclaim_json, data=new_separated, filename="_captions")
		return exsclaim_json
