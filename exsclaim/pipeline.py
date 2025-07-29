from .figure import FigureSeparator
from .pdf import PDFScraper
from .exceptions import *
from .notifications import *
from .tool import ExsclaimTool, CaptionDistributor, JournalScraper
from .utilities import paths, PrinterFormatter, ExsclaimFormatter, convert_labelbox_to_coords
from .db import Database

import cv2
import logging
import numpy as np

from asyncio import gather
from csv import writer
from datetime import datetime as dt
from enum import Flag, auto
from functools import reduce
from json import load, dump
from operator import or_
from os.path import isfile, splitext
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from re import sub
from sqlalchemy.exc import SQLAlchemyError
from textwrap import wrap, dedent
from typing import Any, Callable
from uuid_utils import uuid7


__all__ = ["Pipeline", "SaveMethods", "PipelineInterruptionException"]


class SaveMethods(Flag):
	SUBFIGURES = auto()
	VISUALIZATION = auto()
	BOXES = auto()
	POSTGRES = auto()
	CSV = auto()

	@classmethod
	def from_str(cls, string:str):
		match(string):
			case "save_subfigures" | "subfigures":
				return cls.SUBFIGURES
			case "visualization" | "visualize":
				return cls.VISUALIZATION
			case "boxes":
				return cls.BOXES
			case "postgres":
				# Postgres requires the csv method to have been run
				return cls.POSTGRES | cls.CSV
			case "csv":
				return cls.CSV
			case _:
				raise ValueError(f"There is no corresponding save_method to: {string}.")

	@classmethod
	def from_list(cls, lst:list[str]):
		def get_values(value:str):
			try:
				return cls.from_str(value)
			except ValueError:
				return None
		return reduce(or_, filter(lambda x: x is not None, map(get_values, lst)))
		# return reduce(lambda x, y: x | y, filter(lambda x: x is not None, map(get_values, lst)))


def chmod(path:Path, permissions=None):
	if permissions is None:
		permissions = path.stat().st_mode
	else:
		path.chmod(permissions)

	for directory, _, files in path.walk():
		directory.chmod(permissions)
		for file in files:
			new_path = directory / file
			new_path.chmod(permissions)


class Pipeline:
	"""Defines the exsclaim! pipeline"""

	def __init__(self, query_path):
		"""initialize a Pipeline to run on query path and save to exsclaim path

		Args:
			query_path (dict or path to json): An EXSCLAIM user query JSON
		"""
		# Load Query on which Pipeline will run
		if "test" == query_path:
			query_path = Path(__file__).resolve().parent / "tests" / "data" / "nature_test.json"

		if isinstance(query_path, dict):
			self.query_dict = query_path
			self.query_path = ""
		else:
			assert isfile(query_path), f"query path must be a dict, query path, or 'test', was {query_path}."
			self.query_path = query_path
			with open(self.query_path) as f:
				# Load query file to dict
				self.query_dict = load(f)

		# Set up file structure
		base_results_dir = paths.initialize_results_dir(self.query_dict.get("results_dir", None))
		self.query_dict.setdefault("run_id", str(uuid7()))

		self.results_directory = base_results_dir / self.query_dict["name"]
		self.results_directory.mkdir(exist_ok=True)

		# region Set up logging
		handlers = []
		for log_output in self.query_dict.get("logging", []):
			if log_output.lower() == "print":
				handler = logging.StreamHandler()
				handler.setFormatter(PrinterFormatter())
			else:
				log_output = self.results_directory / log_output
				handler = logging.FileHandler(filename=log_output, mode="w+")
				handler.setFormatter(ExsclaimFormatter())
			handlers.append(handler)

		logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)
		self.logger = logging.getLogger(__name__)
		self.logger.info(f"Results will be located in: `{self.results_directory}` with run id {self.query_dict['run_id']}.")
		# endregion

		# region Check for an existing exsclaim json
		self.exsclaim_path = self.results_directory / "exsclaim.json"

		if self.exsclaim_path.exists():
			with open(self.exsclaim_path, "r") as f:
				# Load configuration file values
				self.exsclaim_dict = load(f)
		else:
			self.logger.info("No exsclaim.json file found, starting a new one.")
			# Keep preset values
			self.exsclaim_dict = {}
		# endregion

		# region Set up notifications
		exsclaim_notifications = self.query_dict.get("notifications", {})
		notifications = (_class.from_json(json)
						 for key, _class in Notifications.notifiers().items()
						 for json in exsclaim_notifications.get(key, []))
		self.notifications:tuple[Notifications] = tuple(notifications)

	# endregion

	def display_info(self, info):
		"""Display information to the user as the specified in the query

		Args:
			info (str): A string to display (either to stdout, a log file)
		"""
		self.logger.info(info)

	async def run(self, tools:list[type[ExsclaimTool]] = None, journal_scraper=True, pdf_scraper=True,
				  caption_distributor=True, figure_separator=True) -> dict:
		"""Run EXSCLAIM pipeline on Pipeline instance's query path

		Args:
			tools (list of ExsclaimTools): list of ExsclaimTool objects
				to run on query path in the order they will run. Default
				argument is JournalScraper, CaptionDistributor,
				FigureSeparator
			journal_scraper (boolean): True if JournalScraper should
				be included in tools list. Overridden by a tools argument
			pdf_scraper (boolean): True if PDFScraper should
				be included in tools list. Overridden by a tools argument
			caption_distributor (boolean): True if CaptionDistributor should
				be included in tools list. Overridden by a tools argument
			figure_separator (boolean): True if FigureSeparator should
				be included in tools list. Overridden by a tools argument
		Returns:
			exsclaim_dict (dict): an exsclaim json
		Modifies:
			self.exsclaim_dict
		Raises:
			PipelineInterruptionException: Raises if another exception stops the pipeline from properly completing
		Examples:
			>>> from exsclaim import Pipeline, PipelineInterruptionException
			>>> pipeline = Pipeline({})
			>>> try:
			>>>	    results = await pipeline.run(journal_scraper=True, pdf_scraper=False, figure_separator=True, caption_distributor=True)
			>>>	    print(f"{results=}.")
			>>> except PipelineInterruptionException as e:
			>>>	    print(f"The EXSCLAIM! pipeline could not finish due to the following issue: {e}.")
			>>>	    print(f"The only results are: {results}.")
		"""
		self.display_info(dedent("""
			@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
			@@@@@@@@@@@@@@@@@@@&   /&@@@(   /@@@@@@@@@@@@@@@@@@@
			@@@@@@@@@@@@@@@ %@@@@@@@@@@@@@@@@@@@ *@@@@@@@@@@@@@@
			@@@@@@@@@@@@ @@@@@@@@@@@@@@,  .@@@@@@@@ *@@@@@@@@@@@
			@@@@@@@@@.#@@@@@@@@@@@@@@@@,    @@@@@@@@@@ @@@@@@@@@
			@@@@@@@&,@@@@@@@@@@@@@@@@@@.    @@@@@@@@@@@@ @@@@@@@
			@@@@@@ @@@@@@@@@@@@@@@@@@@@     @@@@@@@@@@@@@ @@@@@@
			@@@@@ @@@@@@@@@@@@@@@@@@@@@    *@@@@@@@@@@@@@@/@@@@@
			@@@@ @@@@@@@@@@@@@@@@@@@@@@    @@@@@@@@@@@@@@@@,@@@@
			@@@ @@@@@@@@@@@@@@@@@@@@@@&    @@@@@@@@@@@@@@@@@ @@@
			@@@,@@@@@@@@@@@@@@@@@@@@@@*   (@@@@@@@@@@@@@@@@@@%@@
			@@.@@@@@@@@@@@@@@@@@@@@@@@    @@@@@@@@@@@@@@@@@@@ @@
			@@ @@@@@@@@@@@@@@@@@@@@@@@    @@@@@@@@@@@@@@@@@@@ @@
			@@ @@@@@@@@@@@@@@@@@@@@@@/   &@@@@@@@@@@@@@@@@@@@ @@
			@@,@@@@@@@@@@@@@@@@@@@@@@    @@@@@@@@@@@@@@@@@@@@ @@
			@@@.@@@@@@@@@@@@@@@@@@@@&   @@@@@@@@@@@@@@@@@@@@@%@@
			@@@ @@@@@@@@@@@@@@@@@@@@@  /@@@@@@@@@@@@@@@@@@@@ @@@
			@@@@ @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@,@@@@
			@@@@@ @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@*@@@@@
			@@@@@@ @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ @@@@@@
			@@@@@@@@ @@@@@@@@@@@@    @@@@@@@@@@@@@@@@@@@ @@@@@@@
			@@@@@@@@@.(@@@@@@@@@@     @@@@@@@@@@@@@@@@ @@@@@@@@@
			@@@@@@@@@@@@ @@@@@@@@@#   #@@@@@@@@@@@@ /@@@@@@@@@@@
			@@@@@@@@@@@@@@@ ,@@@@@@@@@@@@@@@@@@@ &@@@@@@@@@@@@@@
			@@@@@@@@@@@@@@@@@@@@   ,%@@&/   (@@@@@@@@@@@@@@@@@@@
			@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
		"""))
		_id = self.query_dict.get("id", None)
		exsclaim_dict = self.exsclaim_dict
		query_dict = self.query_dict
		message = f"EXSCLAIM! query{f' `{_id}`' if _id is not None else ''} failed without a message."

		try:
			# set default values
			if tools is None:
				tools: list[ExsclaimTool] = []
				if journal_scraper:
					tools.append(JournalScraper(self.query_dict, logger=self.logger))
				if pdf_scraper:
					tools.append(PDFScraper(self.query_dict, logger=self.logger))
				if caption_distributor:
					tools.append(CaptionDistributor(self.query_dict, logger=self.logger))
				if figure_separator:
					tools.append(FigureSeparator(self.query_dict, logger=self.logger))
			else:
				tools: list[ExsclaimTool] = [cls(self.query_dict, logger=self.logger) for cls in tools]

			# Ensure that any save methods that need to load something before hand do it before pipeline runs
			save_methods = SaveMethods.from_list(query_dict.get("save_format", []))

			if SaveMethods.POSTGRES in save_methods:
				try:
					await Database().ensure_connection()
				except BaseException as e:
					raise PipelineInterruptionException("Save method \"postgres\" cannot be used since a connection to the server cannot be made.") from e

			# run each ExsclaimTool on search query
			for tool in tools:
				await tool.load()
				exsclaim_dict = await tool.run(query_dict, exsclaim_dict)
				await tool.unload()

			self.exsclaim_dict = exsclaim_dict

			# group unassigned objects
			self.group_objects()
			# self.exsclaim_dict["subfigures"] = sum(map(lambda x: len(x["master_images"]), self.exsclaim_dict.values()))

			# Save results as specified
			if SaveMethods.SUBFIGURES in save_methods:
				self.to_file()

			if SaveMethods.VISUALIZATION in save_methods:
				extractions = self.results_directory / "extractions"
				extractions.mkdir(exist_ok=True)

				await gather(*[self.make_visualization(name, json, extractions) for name, json in self.exsclaim_dict.items()])

			if SaveMethods.BOXES in save_methods:
				for figure in self.exsclaim_dict:
					self.draw_bounding_boxes(figure)

			if SaveMethods.CSV in save_methods or SaveMethods.POSTGRES in save_methods:
				csv_info = self.to_csv()

				if SaveMethods.POSTGRES in save_methods:
					db = Database()
					try:
						await db.upload(csv_info, run_id=self.query_dict["run_id"])
					except SQLAlchemyError as e:
						self.logger.exception("An error occurred while uploading the results to the database, but the pipeline finished running.")
						raise PipelineInterruptionException("The results could not be saved to the database, but the pipeline finished running before this happened.") from e

			# Creates success messages to be sent to the notifiers
			message = f"EXSCLAIM! query{f' `{_id}`' if _id is not None else ''} finished at: {dt.now():%Y-%m-%dT%H:%M%z}."
		except BaseException as e:
			self.logger.exception(e)
			message = f"An error occurred at {dt.now():%Y-%m-%dT%H:%M%z} running{' the' if _id is None else ''} EXSCLAIM! query{f' `{_id}`' if _id is not None else ''}."
			raise PipelineInterruptionException from e
		finally:
			chmod(tools[0].results_directory, query_dict.get("permissions", 0o775))
			for notifier in self.notifications:
				try:
					await notifier.notify(message, name=self.query_dict["name"])
				except CouldNotNotifyException:
					self.logger.exception(f"Could not send notification regarding the completion of \"{self.query_dict['name']}\".")

			return self.exsclaim_dict

	@staticmethod
	def assign_captions(figure:dict) -> tuple[list[dict], dict]:
		"""Assigns all captions to master_images JSONs for single figure

		Args:
			figure (dict): a Figure JSON
		Returns:
			masters (list of dicts): list of master_images JSONs
			unassigned (dict): the updated unassigned JSON
		"""
		unassigned = figure.get("unassigned", {})
		masters = []

		captions = unassigned.get("captions", {})
		not_assigned = {a["label"] for a in captions}

		for index, master_image in enumerate(figure.get("master_images", [])):
			label_json = master_image.get("subfigure_label", {})
			subfigure_label = label_json.get("text", index)

			# remove periods or commas from around subfigure label
			processed_label = sub(r"[().,]", "", subfigure_label).lower()
			paired = False

			for caption_label in captions:
				# remove periods or commas from around caption label
				processed_caption_label = sub(r"[().,]", "", caption_label["label"]).lower()

				# check if caption label and subfigure label match and caption label has not already been matched
				if processed_caption_label != processed_label or processed_caption_label not in [a.lower() for a in not_assigned]:
					continue

				master_image |= {
					"caption": caption_label["description"], # .replace("\n", " ").strip()
					"keywords": caption_label["keywords"],
					# "context": caption_label["context"],
					# "general": caption_label["general"],
				}

				masters.append(master_image)

				not_assigned.remove(caption_label["label"])
				# break to next master image if a pairing was found
				paired = True
				break

			if paired:
				continue
			# no pairing found, create empty fields
			master_image.setdefault("caption", [])
			master_image.setdefault("keywords", [])
			# master_image.setdefault("context", [])
			# master_image.setdefault("general", [])
			masters.append(master_image)

		# update unassigned captions
		unassigned["captions"] = [caption_label for caption_label in captions if caption_label["label"] in not_assigned]
		# unassigned["captions"] = list(filter(lambda caption_label: caption_label["label"] in not_assigned, not_assigned))

		return masters, unassigned

	def group_objects(self):
		"""Pair captions with subfigures for each figure in exsclaim json"""
		self.display_info("Matching Image Objects to Caption Text\n")
		figures = len(self.exsclaim_dict)
		for counter, figure in enumerate(self.exsclaim_dict, start=1):
			self.display_info(f">>> ({counter:,} of {figures:,}) Matching objects from figure: {figure}")

			figure_json = self.exsclaim_dict[figure]
			masters, unassigned = self.assign_captions(figure_json)

			figure_json |= {
				"master_images": masters,
				"unassigned": unassigned
			}

		self.display_info(">>> SUCCESS!\n")
		with open(self.results_directory / "exsclaim.json", "w") as f:
			dump(self.exsclaim_dict, f, indent='\t')

		return self.exsclaim_dict

	# ## Save Methods ## #

	def to_file(self):
		""" Saves data to a csv and saves subfigures as individual images

		Modifies:
			Creates directories to save each subfigure
		"""
		from .utilities import convert_labelbox_to_coords

		# TODO: Figure_extension and figure should be getting passed into this function
		def write(figure:np.ndarray, image:dict, directory:Path, figure_extension:str, name_generator:Callable[[str], list[str]], order_c_copy=False):
			"""
			An inner function designed to reduce the amount of needed code in the to_file function.

			:param np.ndarray figure: The cv2 image.
			:param dict image: The image JSON object.
			:param pathlib.Path directory: The directory where the image should be written.
			:param Callable[[str], list[str]] name_generator: How the names of the image files should be generated.
			The only parameter is the determined classification of the image.
			:param bool order_c_copy: If the path should be copied with order='C' as the only parameter.
			Added so the call for the master image would be the same as before.
			"""
			directory.mkdir(exist_ok=True, parents=True)
			_class = image.get("classification", "uas")[:3].lower()
			_name = '_'.join(name_generator(_class)) + figure_extension

			# save image to file
			x1, y1, x2, y2 = convert_labelbox_to_coords(image['geometry'])
			patch = figure[y1:y2, x1:x2]
			if order_c_copy:
				patch = patch.copy(order='C')

			try:
				cv2.imwrite(str(directory / _name), patch)
			except Exception as err:
				self.logger.exception((f"Error in saving cropped master image of figure: {figure_root_name}. {err}"))

		self.display_info(f"Printing Master Image Objects to: {self.results_directory / 'images'}\n")
		for figure_name in self.exsclaim_dict:
			figure_root_name, figure_extension = splitext(figure_name) # figure_name is <figure_root_name>.<figure_extension>
			try:
				figure = cv2.imread(self.results_directory / "figures" / figure_name)
			except Exception as e:
				self.logger.exception(f"Error printing {figure_name} to file. It may be damaged! {e}")
				continue

			# save each master, inset, and dependent image as their own file in a directory according to label
			figure_dict = self.exsclaim_dict[figure_name]
			for master_image in figure_dict.get("master_images", []):
				master_class = master_image['classification'][0:3].lower() if master_image['classification'] is not None else 'uas'

				# create a directory for each master image in <results_dir>/images/<figure_name>/<subfigure_label>
				directory = self.results_directory / "images" / figure_root_name / master_image['subfigure_label']['text']
				write(figure, master_image, directory, figure_extension,
					  lambda _class: [figure_root_name,
									  master_image['subfigure_label']['text'],
									  _class],
					  order_c_copy=True)

				# Repeat for dependents of the master image to file
				for dependent_id, dependent_image in enumerate(master_image.get("dependent_images", [])):
					dependent_root_name = directory / "dependent"
					write(figure, dependent_image, dependent_root_name, figure_extension,
						  lambda _class: [figure_root_name,
										  master_image['subfigure_label']['text'],
										  f"dep{dependent_id}", _class])

					# Repeat for insets of dependents of master image to file
					for inset_id, inset_image in enumerate(dependent_image.get("inset_images", [])):
						inset_root_name = dependent_root_name / "inset"
						write(figure, inset_root_name, inset_image, figure_extension,
							  lambda _class: [figure_root_name,
											  master_image['subfigure_label']['text'],
											  f"ins{inset_id}", _class])

				# Write insets of masters to file
				for inset_id, inset_image in enumerate(master_image.get("inset_images", [])):
					inset_root_name = directory / "inset"
					write(figure, inset_root_name, inset_image, figure_extension,
						  lambda _class: [figure_root_name,
										  master_image['subfigure_label']['text'],
										  f"ins{inset_id}", _class])

		self.display_info(">>> SUCCESS!\n")

	async def make_visualization(self, figure_name:str, figure_json:dict, extractions):
		"""Save subfigures and their labels as images

		Args:
			figure_name (str): A path to the image (.png, .jpg, or .gif)
				file containing the article figure
		Modifies:
			Creates images and text files in <save_path>/extractions folders
			showing details about each subfigure
		"""
		def draw_box(draw_full_figure, geometry, width=2, outline="green", **kwargs):
			coords = convert_labelbox_to_coords(geometry)
			bounding_box = tuple(map(int, coords))
			draw_full_figure.rectangle(bounding_box, width=width, outline=outline, **kwargs)

		# def draw_box(image, geometry, thickness=2, outline=(0, 255, 0), **kwargs):
		# 	x1, y1, x2, y2 = tuple(map(int, convert_labelbox_to_coords(geometry)))
		# 	cv2.rectangle(image, (x1, y1), (x2, y2), outline, thickness=thickness, **kwargs)

		master_images = figure_json.get("master_images", [])

		# to handle older versions that didn't store height and width
		for master_image in master_images:
			if "height" not in master_image or "width" not in master_image:
				x1, y1, x2, y2 = convert_labelbox_to_coords(master_image["geometry"])
				master_image["height"] = y2 - y1
				master_image["width"] = x2 - x1

		image_buffer = 150
		height = int(sum((master["height"] + image_buffer for master in master_images)))
		width = int(max((master["width"] for master in master_images)))
		image_width = max(width, 500)
		image_height = height

		# Make and save images
		labeled_image = Image.new(mode="RGB", size=(image_width, image_height))
		draw = ImageDraw.Draw(labeled_image)
		try:
			font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
		except OSError as e:
			self.display_info(f"Could not create font DejaVuSans.ttf, using default. {e}")
			font = ImageFont.load_default()

		labeled_image = np.zeros(shape=(image_height, image_width, 3), dtype=np.uint8)
		font = cv2.freetype.createFreeType2()
		font.loadFontData(fontFileName="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", id=0)

		figures_path = self.results_directory / "figures"
		full_figure = Image.open(figures_path / figure_json["figure_name"]).convert("RGB")
		draw_full_figure = ImageDraw.Draw(full_figure)
		# full_figure = cv2.imread(str(figures_path / figure_json["figure_name"]))

		image_y = 0
		for subfigure_json in master_images:
			x1, y1, x2, y2 = tuple(map(int, convert_labelbox_to_coords(subfigure_json["geometry"])))
			classification = subfigure_json["classification"]
			caption: str = subfigure_json.get("caption", "")
			caption = "\n".join(wrap(caption, width=100))

			subfigure_label = subfigure_json["subfigure_label"]["text"]
			scale_bar_label = subfigure_json.get("scale_label", "None")
			scale_bars = subfigure_json.get("scale_bars", [])

			# Draw bounding boxes on detected objects
			for scale_bar in scale_bars:
				draw_box(draw_full_figure, scale_bar["geometry"])
				if scale_bar["label"]:
					draw_box(draw_full_figure, scale_bar["label"]["geometry"])

			label_geometry = subfigure_json["subfigure_label"]["geometry"]
			if label_geometry:
				draw_box(draw_full_figure, label_geometry)

			# Draw image
			subfigure = full_figure.crop((int(x1), int(y1), int(x2), int(y2)))
			# subfigure = full_figure[y1:y2, x1:x2]
			text = f"Subfigure Label: {subfigure_label}\nClassification: {classification}\nScale Bar Label: {scale_bar_label}\nCaption:\n{caption}"
			text.encode("utf-8")

			labeled_image.paste(subfigure, box=(0, image_y))
			labeled_image[image_y:, 0:] = subfigure
			image_y += int(subfigure_json["height"])

			draw.text((0, image_y), text, fill="white", font=font)
			# font.text(labeled_image, text, (0, image_y), color=(255, 255, 255))
			image_y += image_buffer

		labeled_image.save(extractions / figure_name)
	# cv2.imwrite(str(extractions / figure_name), labeled_image)

	def draw_bounding_boxes(self, figure_name:str, draw_scale=False, draw_labels=False, draw_subfigures=True):
		"""Save figures with bounding boxes drawn

		Args:
			figure_name (str): A path to the image (.png, .jpg, or .gif) file containing the article figure
			draw_scale (bool): If True, draws scale object bounding boxes
			draw_labels (bool): If True, draws subfigure label bounding boxes
			draw_subfigures (bool): If True, draws subfigure bounding boxes
		Modifies:
			Creates images and text files in <save_path>/boxes folders
			showing details about each subfigure
		"""
		def append_bbox(geometry, lst:list):
			coords = convert_labelbox_to_coords(geometry)
			bounding_box = tuple(map(int, coords))
			lst.append(bounding_box)

		boxes_directory = self.results_directory / "boxes"
		boxes_directory.mkdir(exist_ok=True)
		figure_json = self.exsclaim_dict[figure_name]
		master_images = figure_json.get("master_images", [])

		figures_path = self.results_directory / "figures"
		full_figure = Image.open(figures_path / figure_json["figure_name"]).convert("RGB")
		draw_full_figure = ImageDraw.Draw(full_figure)

		scale_objects = []
		subfigure_labels = []
		subfigures = []
		for subfigure_json in master_images:
			# collect subfigures
			subfigures.append(convert_labelbox_to_coords(subfigure_json["geometry"]))

			# Collect scale bar objects
			for scale_bar in subfigure_json.get("scale_bars", []):
				append_bbox(scale_bar["geometry"], scale_objects)
				if scale_bar["label"]:
					append_bbox(scale_bar["label"]["geometry"], scale_objects)

			# Collect subfigure labels
			label_geometry = subfigure_json["subfigure_label"]["geometry"]
			if label_geometry:
				append_bbox(label_geometry, subfigure_labels)

		unassigned_scale = figure_json.get("unassigned", {}).get("scale_bar_lines", [])
		for scale_object in unassigned_scale:
			if "geometry" in scale_object:
				geometry = scale_object["geometry"]
			elif scale_object.get("label") is not None:
				geometry = scale_object["label"]["geometry"]
			else:
				continue

			append_bbox(geometry, scale_objects)

		# Draw desired bounding boxes
		if draw_scale:
			for bounding_box in scale_objects:
				draw_full_figure.rectangle(bounding_box, width=2, outline="green")

		if draw_labels:
			for bounding_box in subfigure_labels:
				draw_full_figure.rectangle(bounding_box, width=2, outline="green")

		if draw_subfigures:
			for bounding_box in subfigures:
				draw_full_figure.rectangle(bounding_box, width=5, outline="red")

		del draw_full_figure
		full_figure.save(boxes_directory / figure_name)

	def to_csv(self) -> dict[str, list[Any]]:
		"""Places data in a set of csv's ready for database upload

		Modifies:
			Creates csv/ folder with article, figure, scalebar, scalebarlabel, subfigure, and subfigurelabel csvs.
		"""
		exsclaim_json = self.exsclaim_dict
		csv_dir = self.results_directory / "csv"
		csv_dir.mkdir(exist_ok=True)

		articles = set()
		subfigures = set()
		classification_codes = {
			"microscopy": "MC",
			"diffraction": "DF",
			"graph": "GR",
			"basic_photo": "PH",
			"illustration": "IL",
			"unclear": "UN",
			"parent": "PT",
			"subfigure": "SB"
		}

		csv_info = {
			"article": [],
			"figure": [],
			"subfigure": [],
			"subfigure_label": [],
			"scale_label": [],
			"scale": []
		}

		for figure_name, figure_json in exsclaim_json.items():
			# create row for unique articles
			article_id = figure_json["article_name"]
			if article_id not in articles:
				csv_info["article"].append([
					article_id,
					figure_json["title"],
					figure_json["article_url"],
					figure_json["license"],
					figure_json["open"],
					figure_json.get("authors", []),
					figure_json.get("abstract", ""),
				])
				articles.add(article_id)

			base_name = ".".join(figure_name.split(".")[:-1])
			figure_id = sub("_fig", "-fig", base_name)

			# create row for figure.csv
			csv_info["figure"].append([
				figure_id,
				figure_json["full_caption"],
				figure_json["caption_delimiter"],
				figure_json["image_url"],
				figure_json["figure_path"],
				figure_json["article_name"],
			])

			# loop through subfigures
			for master_image in figure_json.get("master_images", []):
				subfigure_label = master_image["subfigure_label"]["text"]
				subfigure_coords = convert_labelbox_to_coords(master_image["geometry"])
				subfigure_id = f"{figure_id}-{subfigure_label}"
				if subfigure_id in subfigures:
					continue

				subfigures.add(subfigure_id)
				csv_info["subfigure"].append([
					subfigure_id,
					classification_codes[master_image["classification"]],
					master_image.get("height", None),
					master_image.get("width", None),
					master_image.get("nm_height", None),
					master_image.get("nm_width", None),
					*subfigure_coords,
					str(master_image.get("caption", "")),
					master_image.get("keywords", []),
					figure_id,
				])

				if master_image["subfigure_label"].get("geometry", None):
					subfigure_label_coords = convert_labelbox_to_coords(master_image["subfigure_label"]["geometry"])
					csv_info["subfigure_label"].append([
						master_image["subfigure_label"]["text"],
						*subfigure_label_coords,
						master_image["subfigure_label"].get("label_confidence", None),
						master_image["subfigure_label"].get("box_confidence", None),
						subfigure_id,
					])

				for i, scale_bar in enumerate(master_image.get("scale_bars", [])):
					scale_bar_id = f"{subfigure_id}-{i}"
					scale_bar_coords = convert_labelbox_to_coords(scale_bar["geometry"])
					csv_info["scale"].append([
						scale_bar_id,
						*scale_bar_coords,
						scale_bar.get("length", None),
						scale_bar.get("label_line_distance", None),
						scale_bar.get("confidence", None),
						subfigure_id,
					])

					if scale_bar.get("label", None) is None:
						continue

					scale_label = scale_bar["label"]
					scale_label_coords = convert_labelbox_to_coords(scale_label["geometry"])
					csv_info["scale_label"].append([
						scale_label["text"],
						*scale_label_coords,
						scale_label.get("label_confidence", None),
						scale_label.get("box_confidence", None),
						scale_label.get("nm", None),
						scale_bar_id,
					])

		# Save lists of rows to csvs
		for _type, rows in csv_info.items():
			with open(csv_dir / f"{sub('_', '', _type)}.csv", "w", encoding="utf-8", newline="") as file:
				csv_writer = writer(file)
				csv_writer.writerows(rows)

		return csv_info
