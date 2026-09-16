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
from .exceptions import PipelineInterruptionException, JournalScrapeError, ExsclaimToolException, PipelineConfigError
from .figures import CRNN, ctc, non_max_suppression_malisiewicz, create_scale_bar_objects, ScalebarInfo, resize_transform, \
	geometry_boxes as boxes
from .journals import JournalFamily
from .utilities import initialize_results_dir, PrinterFormatter, load_model_from_checkpoint, download_model_checkpoint

from abc import ABC, abstractmethod
from logging import getLogger, StreamHandler
from os import PathLike
from pathlib import Path
from PIL import Image
from time import time_ns as timer
from typing import Any, Callable, Collection, Iterable, Optional

import asyncio
import cv2
import json
import numpy as np
import pydantic
import re
import torch

if settings.DISPLAY_TQDM:
	from tqdm.asyncio import tqdm_asyncio
	# from tqdm.contrib.logging import logging_redirect_tqdm
	from .utilities.tqdm import tqdm_logging_redirect


__all__ = ["ExsclaimTool", "JournalScraper", "CaptionDistributor", "FigureSeparator", "ExsclaimEncoder"]


class ExsclaimEncoder(json.JSONEncoder):
	def default(self, o):
		if isinstance(o, np.integer):
			return int(o)
		elif isinstance(o, np.floating):
			return float(o)
		elif isinstance(o, pydantic.BaseModel):
			return o.model_dump()
		return super().default(o)


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
		return self

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
					search_query = json.load(f)
			except Exception as e:
				self.logger.exception(f"Search Query must be a dictionary or pathlib.Path, not {search_query.__class__.__name__}.", exc_info=e)
				raise PipelineInterruptionException("Could not validate the search query passed.") from e

		self._search_query = search_query

		# Set up file structure
		self.results_directory = initialize_results_dir(self.search_query)

	def _appendJSON(self, exsclaim_json: dict, exsclaim_filename: PathLike[str] = None, data: Iterable[str] = None,
					filename: Optional[str | PathLike[str]] = None):
		"""Commit updates to exsclaim json and update list of scraped articles

		Args:
			filename (string): File in which to store the updated EXSCLAIM JSON
			exsclaim_json (dict): Updated EXSCLAIM JSON
		"""
		if exsclaim_filename is None:
			exsclaim_filename = self.results_directory / "exsclaim.json"
		with open(exsclaim_filename, 'w', encoding="utf-8") as f:
			json.dump(exsclaim_json, f, indent='\t', cls=ExsclaimEncoder)

		if data is None and filename is None:
			return

		if (data is None) ^ (filename is None):
			raise ValueError("If additional data is provided, the filename to append the data to must also be provided.")

		with open(self.results_directory / filename, "a+", encoding="utf-8") as f:
			for item in data:
				f.write(f"{item}\n")

	def _update_exsclaim(self, exsclaim_dict: dict, article_name: str, article_dict: dict, *args, **kwargs):
		"""Update the exsclaim_dict with article_dict contents

		Args:
			exsclaim_dict (dict): An EXSCLAIM JSON
			article_dict (dict):
		Returns:
			exsclaim_dict (dict): EXSCLAIM JSON with article_dict
				contents added.
		"""
		exsclaim_dict[article_name] = article_dict
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
		name = journal.get_article_name_from_url(article)
		self.display_info(f">>> Extracting figures from: {name}")
		url = journal.domain + article

		try:
			article_dict = await journal.get_article_figures(url, html_directory)

			if article_dict:
				async with lock:
					self._update_exsclaim(exsclaim_json, name, article_dict)
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

		self.display_info("Running Journal Scraper\n")

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

	def _update_exsclaim(self, search_query, exsclaim_dict, article_id, figure_name, caption_dict: dict[str, str],
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
			exsclaim_dict[article_id]["figures"][figure_name]["unassigned"]["captions"].append(master_image)
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

	async def _task(self, exsclaim_json: dict, search_query: dict, article_id: str, figure: str, new_separated: set, lock: asyncio.Lock,
					 semaphore: OptionalSemaphore):
		async with semaphore:
			try:
				caption_text = exsclaim_json[article_id]["figures"][figure]["full_caption"]

				caption_dict, keywords, usage = await self.llm.parse_captions(caption_text)

				if caption_dict is not None:
					self.logger.debug(f"Full caption dict: \"{caption_dict}\".")
					async with lock:
						self._update_exsclaim(search_query, exsclaim_json, article_id, figure, caption_dict, keywords, usage)
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
		self.display_info("Running Caption Distributor\n")

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
			(article_id, figure["figure_name"])
			for article_id, article_json in exsclaim_json.items()
			for figure in article_json.get("figures", dict()).values()
			if figure["figure_name"] not in separated
		]

		lock = asyncio.Lock()
		semaphore = OptionalSemaphore(self.llm)

		async with asyncio.TaskGroup() as tg:
			tasks = [tg.create_task(self._task(exsclaim_json, search_query, article_id, _path, new_separated, lock, semaphore))
			         for article_id, _path in figures]

			await self._await_task_completions(tasks, t0, "captions", "Distributing captions from {}".format)

		self._appendJSON(exsclaim_json, data=new_separated, filename="_captions")
		return exsclaim_json


class FigureSeparator(ExsclaimTool):
	"""
	FigureSeparator object.
	Separate subfigure images from full figure image
	using CNN trained on crowdsourced labeled figures
	Parameters:
	None
	"""

	def __init__(self, search_query: dict, yolov11_subfigure_bbox: Optional[Path] = None,
	             yolov11_subfigure_label: Optional[Path] = None,
				 yolov11_classifier: Optional[Path] = None, **kwargs):
		kwargs.setdefault("logger_name", __name__ + ".FigureSeparator")
		super().__init__(search_query, **kwargs)
		self.exsclaim_json = dict()
		self._get_unrecognized_image_folders()

		checkpoint_path = settings.CHECKPOINTS_PATH

		self._yolov11_subfigure_bbox_path = yolov11_subfigure_bbox or checkpoint_path / "yolov11_finetuned_augmentation_best.pt"
		self._yolov11_subfigure_label_path = yolov11_subfigure_label or checkpoint_path / "yolov11_label.pt"
		self._yolov11_classifier_path = yolov11_classifier or checkpoint_path / "yolov11_classification.pt"

	def _get_unrecognized_image_folders(self):
		self.undetected_path = settings.UNDETECTED_SUBFIGURES_PATH
		self.unclassified_path = settings.UNCLASSIFIED_SUBFIGURES_PATH

		for path in (self.undetected_path, self.unclassified_path):
			if path is not None:
				path.mkdir(parents=True, exist_ok=True)

	async def check_search_query(self, query_dict: dict[str, Any]):
		try:
			for model_file in (self._yolov11_subfigure_bbox_path, self._yolov11_subfigure_label_path,
			                   self._yolov11_classifier_path):
				if not model_file.is_file():
					await download_model_checkpoint(model_file)
		except (FileNotFoundError, ConnectionError) as e:
			raise PipelineConfigError("Could not download the YOLO models from the server.", keys=None) from e

	async def load(self):
		"""Load relevant models for the object detection tasks"""
		from ultralytics import YOLO
		from torchvision.models.detection import fasterrcnn_resnet50_fpn
		from torchvision.models.detection.faster_rcnn import FastRCNNPredictor, FasterRCNN_ResNet50_FPN_Weights

		# Set configuration variables
		figures_path = Path(__file__).parent.resolve() / "figures"
		self.cuda = torch.cuda.is_available()

		self.dtype = torch.cuda.FloatTensor if self.cuda else torch.FloatTensor
		if self.cuda:
			self.logger.info("Using CUDA.")

		self.device = torch.device("cuda" if self.cuda else "cpu")

		try:
			self.subfigure_bbox = YOLO(self._yolov11_subfigure_bbox_path)
			self.subfigure_bbox.to(self.device)
			self.logger.info("Subfigure bounding box model has been loaded.")

			self.subfigure_label = YOLO(self._yolov11_subfigure_label_path)
			self.subfigure_label.to(self.device)
			self.logger.info("Subfigure label bounding box model has been loaded.")

			self.classification_model = YOLO(self._yolov11_classifier_path)
			self.classification_model.to(self.device)
			self.logger.info("Subfigure classification model has been loaded.")
		except BaseException as e:
			self.logger.exception("Error loading YOLO models.")
			raise ExsclaimToolException from e

		# Common YOLO settings if needed
		self.confidence_threshold = 0.25  # Default confidence threshold
		self.image_size = 640  # Default YOLO image size

		# Load scale bar detection model
		# load an object detection model pre-trained on COCO
		scale_bar_detection_model = fasterrcnn_resnet50_fpn(weights=FasterRCNN_ResNet50_FPN_Weights.DEFAULT)

		input_features = scale_bar_detection_model.roi_heads.box_predictor.cls_score.in_features

		number_classes = 3  # background, scale bar, scale bar label
		scale_bar_detection_model.roi_heads.box_predictor = FastRCNNPredictor(input_features, number_classes)

		self.scale_bar_detection_model = await load_model_from_checkpoint(
			scale_bar_detection_model, "scale_bar_detection_model.pt", self.device,
		)

		# Load scale label recognition model
		config_path = figures_path / "config" / "scale_label_reader.json"
		with open(config_path, "r") as f:
			from orjson import loads
			configuration_file = loads(f.read())

		configuration = configuration_file["theta"]
		scale_label_recognition_model = CRNN(configuration=configuration)

		self.scale_label_recognition_model = await load_model_from_checkpoint(
			scale_label_recognition_model, "scale_label_recognition_model.pt", self.device
		)

	async def unload(self):
		if self.cuda:
			torch.cuda.empty_cache()
			for model in (self.subfigure_bbox, self.classification_model, self.scale_bar_detection_model,
			              self.scale_label_recognition_model):
				# Remove the model from the GPU
				model.to("cpu")
			del model

	def _update_exsclaim(self, exsclaim_dict: dict, article_id: str, figure: dict):
		figure_name = figure["figure_name"].split("/")[-1]

		exsclaim_dict[article_id]["figures"][figure_name]["master_images"].extend(figure["master_images"])

		return exsclaim_dict

	async def run(self, search_query: dict, exsclaim_dict: dict[str, Any]):
		"""Run the models relevant to manipulating article figures"""
		exsclaim_dict = exsclaim_dict or dict()
		append_file = "_figures"
		path = self.results_directory / "figures"

		self.display_info("Running Figure Separator\n")
		self.results_directory.mkdir(exist_ok=True)

		t0 = self._start_timer()
		# List of objects (figures, captions, etc.) that have already been separated
		file = self.results_directory / "_figures"

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
		figures = tuple(
			(article_id, path / figure["figure_name"])
			for article_id, article_json in exsclaim_dict.items()
			for figure in article_json.get("figures", dict()).values()
			if figure["figure_name"] not in separated
		)

		figures_enum = enumerate(figures, start=counter)
		# if settings.DISPLAY_TQDM:
		# 	figures_enum = tqdm.tqdm(figures_enum, total=len(figures), desc="Separating Figures", unit="fig")
		# set_stream_handlers_to_tqdm(self.logger, figures_enum)

		for counter, (article_id, _path) in figures_enum:
			self.display_info(f">>> ({counter:,} of {+len(figures):,}) Extracting images from: {_path}")

			try:
				figure_json = self.extract_image_objects(_path.name)
				if figure_json is None:
					continue
				new_separated.add(_path.name)
				exsclaim_dict = self._update_exsclaim(exsclaim_dict, article_id, figure_json)
			except Exception as e:
				self.display_exception(e, _path)
				raise e

			# Save to file every N iterations (to accommodate restart scenarios)
			if counter % 1_000 == 0:
				self._appendJSON(exsclaim_dict, data=new_separated, filename=append_file)
				new_separated = set()

		# remove_tqdm_from_set_stream_handlers(self.logger)
		self._end_timer(t0, f"{counter:,} figures")
		self._appendJSON(exsclaim_dict, data=new_separated, filename=append_file)
		return exsclaim_dict

	def read_scale_bar(self, cropped_image: Image.Image) -> ctc.CTC_Results:
		"""Outputs the text of an image cropped to a scale bar label bbox

		Args:
			cropped_image (Image): An PIL RGB image cropped to the bounding box
				of a scale bar label.
		Returns:
			label_text (string): The text of the scale bar label
		"""
		image, classes = resize_transform(cropped_image)
		# run image on model
		logps = self.scale_label_recognition_model(image.to(self.device))
		probs = torch.exp(logps)
		probs = probs.squeeze(0)
		yield from ctc.run_ctc(probs, classes, self.logger)

	@staticmethod
	def assign_scale_objects_to_subfigures(master_image: dict, scale_objects: list[dict]) -> tuple[dict, list[dict]]:
		"""Assign scale bar objects to master images

		Args:
			master_image (Master Image Json): A Master Image JSON
			scale_objects (list of Scale Object JSON): candidate scale objects
		Returns:
			master_image (Master Image JSON): updated with scale objects
			scale_objects: updated with assigned objects removed
		"""
		geometry = master_image["geometry"]
		x1, y1, x2, y2 = boxes.convert_geometry_to_coords(geometry)
		unassigned_scale_objects = []
		assigned_scale_objects = []

		for scale_object in scale_objects:
			if boxes.is_contained(scale_object["geometry"], geometry):
				assigned_scale_objects.append(scale_object)
			else:
				unassigned_scale_objects.append(scale_object)
		master_image["scale_bars"] = assigned_scale_objects

		# find if there is one unique scale bar label
		nm_to_pixel = 0
		label = ""
		scale_labels = set()
		for scale_object in assigned_scale_objects:
			if scale_object["label"]:
				scale_labels.add(scale_object["label"]["nm"])
				nm_to_pixel = scale_object["label"]["nm"] / float(scale_object["length"])
				label = scale_object["label"]["text"]

		if len(scale_labels) == 1:
			master_image.update(dict(
				nm_height=int(nm_to_pixel * master_image.get("height", y2 - y1) * 10) / 10,
				nm_width=int(nm_to_pixel * master_image.get("width", x2 - x1) * 10) / 10,
				scale_label=label
			))
		return master_image, unassigned_scale_objects

	def detect_scale_objects(self, image: torch.Tensor) -> list[ScalebarInfo]:
		"""Detects bounding boxes of scale bars and scale bar labels

		Args:
			image (torch.Tensor): An image tensor
		Returns:
			scale_bar_info (list): A list of lists with the following
				pattern: [[x1,y1,x2,y2, confidence, label],...] where
				label is 1 for scale bars and 2 for scale bar labels
		"""
		# prediction
		self.scale_bar_detection_model.eval()
		with torch.no_grad():
			outputs = self.scale_bar_detection_model([image.to(self.device)])

		# post-process
		scale_bar_info = []
		for i, box in enumerate(outputs[0]["boxes"]):
			confidence = outputs[0]["scores"][i]
			if confidence > 0.5:
				x1, y1, x2, y2 = box
				label = outputs[0]["labels"][i]
				scale_bar_info.append(ScalebarInfo(
					x1.data.cpu(),
					y1.data.cpu(),
					x2.data.cpu(),
					y2.data.cpu(),
					confidence.data.cpu(),
					label.data.cpu(),
				))
		scale_bar_info = non_max_suppression_malisiewicz(
			np.asarray(scale_bar_info), 0.4
		)
		return scale_bar_info

	def determine_scale(self, figure_path: Path, figure_json: dict[str, Any]) -> dict[str, Any]:
		"""Adds scale information to figure by reading and measuring scale bars

		Args:
			figure_path (str): A path to the image (.png, .jpg, or .gif)
				file containing the article figure
			figure_json (dict): A Figure JSON
		Returns:
			figure_json (dict): A dictionary with classified image_objects
				extracted from figure
		"""
		from torchvision import transforms

		convert_to_nm = {
			"a": 0.1,
			"nm": 1.0,
			"um": 1_000.0,
			"mm": 1_000_000.0,
			"cm": 10_000_000.0,
			"m": 1_000_000_000.0,
		}
		unassigned = figure_json.get("unassigned", dict())
		unassigned_scale_labels = unassigned.get("scale_bar_labels", list())
		master_images = figure_json.get("master_images", list())
		image = Image.open(figure_path).convert("RGB")
		tensor_image = transforms.ToTensor()(image)

		# Detect scale bar objects
		scale_bar_info = self.detect_scale_objects(tensor_image)
		label_names = ["background", "scale bar", "scale label"]
		scale_bars = []
		scale_labels = []

		for scale_object in scale_bar_info:
			x1, y1, x2, y2, confidence, classification = scale_object
			geometry = boxes.convert_coords_to_geometry(int(x1), int(y1), int(x2), int(y2))

			match label_names[int(classification)]:
				case "scale bar":
					scale_bars.append(dict(  # Scale bar JSON
						geometry=geometry,
						confidence=float(confidence),
						length=int(x2 - x1),
					))
				case "scale label":
					scale_bar_label_image = image.crop((int(x1), int(y1), int(x2), int(y2)))

					# Read Scale Text
					for (magnitude, unit, label_confidence) in self.read_scale_bar(scale_bar_label_image):
						# 0 is never correct and -1 is the error value
						if magnitude <= 0:
							continue

						length_in_nm = magnitude * convert_to_nm[unit.strip().lower()]
						scale_labels.append(dict(
							geometry=geometry,
							text=f"{magnitude} {unit}",
							label_confidence=float(label_confidence),
							box_confidence=float(confidence),
							nm=int(length_in_nm * 100) / 100,
						))

		# Match scale bars to labels and to subfigures (master images)
		scale_bar_jsons, unassigned_labels = create_scale_bar_objects(scale_bars, scale_labels)
		if len(scale_bar_jsons) > 0:
			for master_image in master_images:
				master_image, scale_bar_jsons = self.assign_scale_objects_to_subfigures(master_image, scale_bar_jsons)

		# Save info to JSON
		unassigned["scale_bar_labels"] = unassigned_scale_labels
		unassigned["scale_bar_lines"] = scale_bar_jsons
		figure_json["unassigned"] = unassigned
		figure_json["master_images"] = master_images

		return figure_json

	def get_bounding_boxes(self, figure_path: Path, model):
		# Run YOLO detection with higher confidence threshold
		results = model.predict(
			source=figure_path,
			imgsz=self.image_size,
			conf=0.6,
			iou=0.45,
			max_det=100,
			agnostic_nms=False,
			stream=False,
			verbose=settings.DEBUG
		)
		result = results[0]

		# Process detections
		detections_per_class = dict()

		for box in result.boxes:
			cls_id = int(box.cls[0])
			conf = box.conf[0]
			if cls_id not in detections_per_class or conf > detections_per_class[cls_id].conf[0]:
				detections_per_class[cls_id] = box
		# print(f"{detections_per_class=}")
		return detections_per_class

	def extract_image_objects(self, figure_path: str) -> dict:
		"""Separate and classify subfigures in an article figure

		Args:
			figure_path (str): A path to the image (.png, .jpg, or .gif)
				file containing the article figure
		Returns:
			figure_json (dict): A dictionary with classified image_objects
				extracted from figure
		"""
		# Get full path to figure
		figure_path = self.results_directory / "figures" / figure_path

		img: np.ndarray = cv2.imread(figure_path, cv2.IMREAD_COLOR)
		if img is None:
			self.logger.warning(f"Could not read the image from {figure_path.resolve()}.")
			return None

		height, width, _ = img.shape
		binary_img = np.zeros((height, width, 1))

		# Get figure name without extension for directory naming
		figure_base_name = figure_path.stem

		detections_per_class = self.get_bounding_boxes(figure_path, self.subfigure_bbox)
		subfigures_per_class = self.get_bounding_boxes(figure_path, self.subfigure_label)

		# Initialize variables
		figure_name = figure_path.name
		figure_json = self.exsclaim_json.get(figure_name, dict())
		figure_json.update(dict(
			figure_name=figure_name,
			master_images=[]
		))

		if len(detections_per_class) == 0:
			self.logger.info(f"{figure_path} could not detect any subfigures.")
			if self.undetected_path is not None:
				cv2.imwrite(self.undetected_path / figure_path.name, img)

		# Process each final detection
		for cls_id, box in detections_per_class.items():
			x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
			label_box = subfigures_per_class.get(cls_id, None)
			if label_box is not None:
				lx1, ly1, lx2, ly2 = label_box.xyxy[0].cpu().numpy()
			else:
				lx1, ly1, lx2, ly2 = None, None, None, None
			conf = float(box.conf[0])

			# Ensure coordinates are within bounds and boxes aren't too small
			x1 = int(min(max(x1, 0), width - 1))
			y1 = int(min(max(y1, 0), height - 1))
			x2 = int(min(max(x2, 0), width))
			y2 = int(min(max(y2, 0), height))

			dx = x2 - x1  # Change in x coordinates (width)
			dy = y2 - y1  # Change in y coordinates (height)

			if dx <= 5 or dy <= 5:
				continue

			# Get the label
			label = self.subfigure_bbox.names[cls_id]  # This will be 'a', 'b', 'c', etc.

			# Add to binary mask for visualization if small enough
			if dx < 64 and dy < 64:
				binary_img[y1:y2, x1:x2] = 255

			# Get the subfigure classification
			classification_results = self.classification_model.predict(
				source=img[y1:y2, x1:x2],
				imgsz=self.image_size,
				conf=0.6,
				iou=0.45,
				max_det=100,
				agnostic_nms=False,
				stream=False,
				verbose=settings.DEBUG
			)

			result = classification_results[0]
			if result.probs is not None:
				classification = result.names[result.probs.top1]
				class_conf = float(result.probs.top1conf)
			else:
				self.logger.exception(
					f"Could not classify subfigure {figure_path} (label {label}) -- result.probs is None.")
				classification = "unclear"
				class_conf = 0
				if self.unclassified_path is not None:
					cv2.imwrite(self.unclassified_path / f"{figure_path.stem}-{label}{figure_path.suffix}", img)

			# Create master_image_info
			master_image_info = {
				"classification": classification,
				"classification_confidence": float(class_conf),
				"confidence": float(conf),
				"height": dy,
				"width": dx,
				"geometry": dict(
					x0=x1,
					y0=y1,
					x1=x2,
					y1=y2
				),
				"subfigure_label": {
					"text": label,
					"geometry": dict(
						x0=int(lx1),
						y0=int(ly1),
						x1=int(lx2),
						y1=int(ly2)
					)
				}
			}

			# Create output directory structure using figure_base_name (without extension)
			subfigure_directory = self.results_directory / "images" / figure_base_name / label
			subfigure_directory.mkdir(parents=True, exist_ok=True)

			# Crop and save using base name for output filename
			cropped_img = img[y1:y2, x1:x2]
			cv2.imwrite(str(subfigure_directory / f"{figure_base_name}_{label}.png"), cropped_img)
			figure_json["master_images"].append(master_image_info)

		try:
			figure_json = self.determine_scale(figure_path, figure_json)
		except TypeError as e:
			self.logger.warning(f"An error occurred when finding the scales for {figure_path}.", exc_info=e)

		return figure_json
