# Copyright 2019 MaterialEyes
# (see accompanying license files for details).

"""Definition of the ExsclaimTool classes.
This module defines the central objects in the EXSCLAIM!
package. All the model classes are independent of each
other, but they expose the same interface, so they are
interchangeable.
"""

from .browser import ExsclaimBrowser
from .caption import safe_summarize_caption, get_context, get_keywords, safe_separate_captions
from .figures import apply_mask
from .journal import journals
from .utilities import initialize_results_dir, PrinterFormatter

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from glob import glob
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain_community.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
from logging import getLogger, StreamHandler
from pathlib import Path
from PIL import Image
from playwright.sync_api import Browser
from time import time_ns as timer, time, sleep

import json
import os
import requests
import shutil
import shutil
import cv2
import numpy as np


__all__ = ["ExsclaimTool", "JournalScraper", "HTMLScraper", "CaptionDistributor"]


class ExsclaimTool(ABC):
	def __init__(self, search_query, logger_name=None):
		self.logger = getLogger(logger_name if logger_name is not None else __name__)
		self.initialize_query(search_query)

	def initialize_query(self, search_query):
		"""initializes search query as instance attribute

		Args:
			search_query (a dict or path to dict): The Query JSON
		"""
		if isinstance(search_query, dict):
			self.search_query = search_query
		else:
			try:
				with open(search_query) as f:
					# Load query file to dict
					self.search_query = json.load(f)
			except Exception as e:
				self.logger.debug(f"Search Query must be a pathlib.Path or dictionary, not {search_query.__class__.__name__}.")
				self.logger.exception(e)

		# Set up file structure
		self.results_directory = initialize_results_dir(self.search_query.get("results_dirs", None)) / self.search_query["name"]

		# set up logging / printing
		if "print" in self.search_query.get("logging", []):
			handler = StreamHandler()
			handler.setFormatter(PrinterFormatter())
			self.logger.addHandler(handler)

	@abstractmethod
	def _load_model(self):
		pass

	@abstractmethod
	def _update_exsclaim(self):
		pass

	@abstractmethod
	def _run_loop_function(self, search_query, exsclaim_json: dict, figure: Path, new_separated:set):
		...

	def _run(self, search_query, exsclaim_dict:dict, display_name:str, subdirectory:str, loop_process_string:str,
			 path:Path=None, N:int=100):
		self.display_info(f"Running {display_name}\n")
		self.results_directory.mkdir(exist_ok=True)

		t0 = timer()
		# List of objects (figures, captions, etc) that have already been separated
		file = self.results_directory / subdirectory

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
			(path / exsclaim_dict[figure]["figure_name"] if path is not None else exsclaim_dict[figure]["figure_name"])
			for figure in exsclaim_dict
			if exsclaim_dict[figure]["figure_name"] not in separated
		]

		for _path in figures:
			self.display_info(f">>> ({counter:,} of {+len(figures):,}) {loop_process_string} from: {figure_path}")

			try:
				exsclaim_dict = self._loop_func(search_query, exsclaim_dict, _path, new_separated)
			except Exception as e:
				self.display_exception(e, _path)

			# Save to file every N iterations (to accommodate restart scenarios)
			if counter % N == 0:
				self._appendJSON(self.exsclaim_json, new_separated)
				new_separated = set()
			counter += 1

		# The timer measures in nanoseconds, this will convert it to seconds
		time_diff = (timer() - t0) / 1e9
		self.display_info(f">>> Time Elapsed: {time_diff:,.2f} sec\t({counter - 1:,} figures)\n")
		self._appendJSON(exsclaim_dict, new_separated)
		return exsclaim_dict

	@abstractmethod
	def run(self, search_query:dict, exsclaim_json:dict):
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
	def __init__(self, search_query:dict):
		super().__init__(search_query, __name__ + ".JournalScraper")
		self.new_articles_visited = set()

	def _load_model(self):
		pass

	def _update_exsclaim(self, exsclaim_dict, article_dict):
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

	def _appendJSON(self, filename, exsclaim_json):
		"""Commit updates to exsclaim json and update list of scraped articles

		Args:
			filename (string): File in which to store the updated EXSCLAIM JSON
			exsclaim_json (dict): Updated EXSCLAIM JSON
		"""
		with open(filename, "w") as f:
			json.dump(exsclaim_json, f, indent=3)
		articles_file = self.results_directory / "_articles"
		with open(articles_file, "a") as f:
			for article in self.new_articles_visited:
				f.write(f"{article.split('/')[-1]}\n")

	def _run_loop_function(self, search_query, exsclaim_json: dict, figure: Path, new_separated: set):
		return exsclaim_json

	def run(self, search_query, exsclaim_json=None):
		"""Run the JournalScraper to find relevant article figures

		Args:
			search_query (dict): A Search Query JSON to guide search
			exsclaim_json (dict): An EXSCLAIM JSON to store results in
		Returns:
			exsclaim_json (dict): Updated with results of search
		"""
		if exsclaim_json is None:
			exsclaim_json = {}
		self.display_info("Running Journal Scraper\n")
		# Checks that user inputted journal family has been defined and
		# grabs instantiates an instance of the journal family object
		journal_family_name = search_query["journal_family"]
		if journal_family_name not in journals:
			raise NameError(f"Journal family {journal_family_name} is not defined.")
		journal_subclass = journals[journal_family_name]
		journal = journal_subclass(search_query)

		self.results_directory.mkdir(exist_ok=True)
		t0 = timer()

		articles = journal.get_article_extensions()
		print(f"{articles=}")
		# Extract figures, captions, and metadata from each article
		counter = 1
		for counter, article in enumerate(articles, start=1):
			print(counter)
			self.display_info(f">>> ({counter:,} of {len(articles)}) Extracting figures from: " + article.split("/")[-1])
			try:
				request = journal.domain + article
				article_dict = journal.get_article_figures(request)
				exsclaim_json = self._update_exsclaim(exsclaim_json, article_dict)
				self.new_articles_visited.add(article)
			except Exception:
				pass
						# Save to file every N iterations (to accommodate restart scenarios)
			if counter % 1_000 == 0:
				self._appendJSON(
					self.results_directory / "exsclaim.json", exsclaim_json
				)

		time_diff = (timer() - t0) / 1e9
		self.display_info(f">>> Time Elapsed: {time_diff:,.2f} sec\t({counter - 1:,} articles)\n")

		self._appendJSON(self.results_directory / "exsclaim.json", exsclaim_json)
		return exsclaim_json


class HTMLScraper(ExsclaimTool, ExsclaimBrowser):
	"""
	HTMLScraper object.
	Extract scientific figures from user provided html articles
	a json-style search query to the run method
	Parameters:
	None
	"""

	def __init__(self, search_query, browser:Browser=None): # provide the location with the folder with the html files
		super().__init__(search_query, logger_name=__name__ + ".HTMLScraper")
		ExsclaimBrowser.__init__(self, browser=browser)
		# self.new_articles_visited = set()
		self.search_query = search_query
		self.open = search_query.get("open", False)
		self.order = search_query.get("order", "relevant")

		# Set up file structure
		base_results_dir = initialize_results_dir(
			self.search_query.get("results_dirs", None)
		)
		self.results_directory = base_results_dir / self.search_query["name"]
		figures_directory = self.results_directory / "figures"
		figures_directory.mkdir(exist_ok=True)

	def extract_figures_from_html(self, soup):
		figure_list = soup.find_all("figure")
		return figure_list

	def save_figures_rsc(self, filename):
		# Load the HTML file and create a BeautifulSoup object
		with open(filename, "r", encoding="utf-8") as file:
			soup = BeautifulSoup(file.read(), "html.parser")

		url_tag = soup.find("link", rel="canonical")

		if url_tag is not None:
			image_url = url_tag.get("href")
			article_name = image_url.split("/")[-1].split("?")[0]
		else:
			article_name = filename.split(".")[0]

		figures = soup.find_all('div', class_='img-tbl')
		article_json = {}
		figure_number = 1

		for figure in figures:
			try:
				img_url = figure.find('a')['href']
			except:
				img_tags = figure.find('img')['data-original']
				img_url = f"https://pubs.rsc.org/{img_tags}"

			figure_caption = figure.find('figcaption').get_text(strip=True)

			if img_url is not None:
				self.page.goto(img_url)

			figure_name = f"{article_name}_fig{figure_number}.png"
			figure_path = Path("output") / "figures" / figure_name

			# initialize the figure's json
			figure_json = {
				"title": soup.find("title").get_text(),
				"article_name": article_name,
				"image_url": image_url,
				"figure_name": figure_name,
				"full_caption": figure_caption,
				"figure_path": str(figure_path),
				"master_images": [],
				"article_url":[],
				"license": [],
				"open": [],
				"unassigned": {
					"master_images": [],
					"dependent_images": [],
					"inset_images": [],
					"subfigure_labels": [],
					"scale_bar_labels": [],
					"scale_bar_lines": [],
					"captions": [],
				},
			}
			# add all results
			article_json[figure_name] = figure_json
			figure_number += 1  # increment figure number
			# Open a file in write binary mode, and write to it
			figure_path = self.results_directory / "figures" / figure_name

			sleep(3)
			self.page.screenshot(path=figure_path)

			apply_mark(figure_path)
			print(f"image saved as: {figure_path}")

		return article_json

	def save_figures_wiley(self, filename):
		# Load the HTML file and create a BeautifulSoup object
		with open(filename, "r", encoding="utf-8") as file:
			html_content = file.read()

		soup = BeautifulSoup(html_content, "html.parser")
		# url_tag = soup.find("link", rel="canonical")
		url_tag = soup.find('meta', attrs={'name': 'pbContext'})
		content = url_tag['content']
		doi_str = [s for s in content.split(';') if 'doi' in s]
		article_doi_list = [doi for doi in doi_str if doi.startswith('article')]
		article_name = article_doi_list[0].split('\\:')[1].split("/")[1]
		# Extract figures from the HTML

		figures = soup.find_all("figure")
		# print(figures)
		article_json = {}
		figure_number = 1

		for figure in figures:

			img = figure.find('img')
			if img:
				img_tags = img['src']
			else:
				source = figure.find('source')
				if source:
					img_tags = source['srcset']
				else:
					img_tags = None

			if img_tags is not None:
				img_url = f"https://onlinelibrary.wiley.com/{img_tags}"
				self.page.goto(img_url)

				# Extract caption
				figure_caption = ""
				caption_tag = figure.find('figcaption')
				if caption_tag:
					# Remove unwanted child elements to avoid redundant text
					for unwanted in caption_tag.find_all(class_="figure-extra"):
						unwanted.extract()

					# Separate figure title and description
					figure_title = caption_tag.find(class_="figure__title")
					if figure_title:
						title_text = figure_title.get_text(strip=True) + ':'
						figure_title.extract()  # remove it from the caption
					else:
						title_text = ''

					caption = title_text + caption_tag.get_text(strip=True)

				else:
					caption_tag = figure.find('p', class_='caption-style')
					if caption_tag:
						caption = caption_tag.get_text(strip=True)
					else:
						caption = None


				# figure_caption = ""
				# caption_tag = figure.find('figcaption')
				# if caption_tag:
				#	 # Remove unwanted child elements to avoid redundant text
				#	 for unwanted in caption_tag.find_all(class_="figure-extra"):
				#		 unwanted.extract()

				#	 # Separate figure title and description
				#	 figure_title = caption_tag.find(class_="figure__title")
				#	 if figure_title:
				#		 title_text = figure_title.get_text(strip=True) + '. '
				#		 figure_title.extract()  # remove it from the caption
				#	 else:
				#		 title_text = ''

				#	 caption = title_text + caption_tag.get_text(strip=True)

				# else:
				#	 caption_tag = figure.find('p', class_='caption-style')
				#	 if caption_tag:
				#		 caption = caption_tag.get_text(strip=True)
				#	 else:
				#		 caption = None

				if caption_tag:
					figure_caption += caption_tag.get_text()


					figure_name = article_name + "_fig" + str(figure_number) + ".png"
					figure_path = (
							Path("output")  / "figures" / figure_name
					)
					# print('init_figurepath',figure_path )

					# initialize the figure's json
					figure_json = {
						"title": soup.find("title").get_text(),
						"article_name": article_name,
						"image_url": img_url,
						"figure_name": figure_name,
						"full_caption": figure_caption,
						"figure_path": str(figure_path),
						"master_images": [],
						"article_url":[],
						"license": [],
						"open": [],
						"unassigned": {
							"master_images": [],
							"dependent_images": [],
							"inset_images": [],
							"subfigure_labels": [],
							"scale_bar_labels": [],
							"scale_bar_lines": [],
							"captions": [],
						},
					}
					# add all results
					article_json[figure_name] = figure_json
					figure_number += 1  # increment figure number
					# Open a file with write binary mode, and write to it
					figures_directory = self.results_directory / "figures"
					figure_path = os.path.join(figures_directory , figure_name)
					# print('figurepath',figure_path )

					with open(figure_path, 'wb') as out_file:
						sleep(3)
						self.page.screenshot(path=figure_path)

						# Load the image
						img = cv2.imread(figure_path, cv2.IMREAD_UNCHANGED)

						# Convert the image to RGBA (just in case the image is in another format)
						img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)

						# Define a 2D filter that will turn black (also shades close to black) pixels to transparent
						low = np.array([0, 0, 0, 0])
						high = np.array([50, 50, 50, 255])

						# Apply the mask (this will turn 'black' pixels to transparent)
						mask = cv2.inRange(img, low, high)
						img[mask > 0] = [0, 0, 0, 0]

						# Convert the image back to PIL format and save the result
						img_pil = Image.fromarray(img)
						img_pil.save(figure_path)
						print(f"image saved as: {figure_path}")
		return article_json

	def save_figures_acs(self, filename):
		# Load the HTML file and create a BeautifulSoup object
		with open(filename, "r", encoding="utf-8") as file:
			html_content = file.read()

		soup = BeautifulSoup(html_content, "html.parser")
		url_tag = soup.find("link", rel="canonical")

		if url_tag is not None:
			image_url = url_tag.get("href")
			article_name = image_url.split("/")[-1].split("?")[0]
		else:
			article_name = filename.split(".")[0]

		# Extract figures from the HTML
		figures = self.extract_figures_from_html(soup)
		unique_figures = []
		unique_data_indices = set()

		for figure in figures:
			data_index = figure.get('data-index')
			if data_index not in unique_data_indices:
				unique_data_indices.add(data_index)
				unique_figures.append(figure)
		figures = unique_figures

		article_json = {}
		figure_number = 1

		for figure in figures:
			img_tags = figure.find_all("img")
			for img_tag in img_tags:
				img_url = img_tag.get("src")
				img_url = img_url.replace("medium", "large").replace("gif", "jpeg")
				img_url = f"https://pubs.acs.org{img_url}"
				captions = figure.find_all("p")

				figure_caption = ""
				for caption in captions:
					if caption is not None:
						figure_caption += caption.get_text()

				if img_url is not None:
					self.page.goto(img_url)
					# response = requests.get(img_url, stream=True)

					figure_name = f"{article_name}_fig{figure_number}.png"
					figure_path = Path("output") / "figures" / figure_name

					# initialize the figure's json
					figure_json = {
						"title": soup.find("title").get_text(),
						"article_name": article_name,
						"image_url": image_url,
						"figure_name": figure_name,
						"full_caption": figure_caption,
						"figure_path": str(figure_path),
						"master_images": [],
						"article_url": [],
						"license": [],
						"open": [],
						"unassigned": {
							"master_images": [],
							"dependent_images": [],
							"inset_images": [],
							"subfigure_labels": [],
							"scale_bar_labels": [],
							"scale_bar_lines": [],
							"captions": [],
						},
					}
					# add all results
					article_json[figure_name] = figure_json
					figure_number += 1  # increment figure number
					# Open a file with write binary mode, and write to it
					figures_directory = self.results_directory / "figures"
					figure_path = os.path.join(figures_directory, figure_name)

					with open(figure_path, 'wb') as out_file:
						sleep(3)
						self.page.screenshot(path=figure_path)

						# Load the image
						img = cv2.imread(figure_path, cv2.IMREAD_UNCHANGED)

						# Convert the image to RGBA (just in case the image is in another format)
						img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)

						# Define a 2D filter that will turn black (also shades close to black) pixels to transparent
						low = np.array([0, 0, 0, 0])
						high = np.array([50, 50, 50, 255])

						# Apply the mask (this will turn 'black' pixels to transparent)
						mask = cv2.inRange(img, low, high)
						img[mask > 0] = [0, 0, 0, 0]

						# Convert the image back to PIL format and save the result
						img_pil = Image.fromarray(img)
						img_pil.save(figure_path)
						print('image saved as: ', figure_path)
		return article_json  # return outside of the for loop to make sure all figures are included

	def save_figures_nature(self, filename):
		# Load the HTML file and create a BeautifulSoup object
		with open(filename, "r", encoding="utf-8") as file:
			html_content = file.read()

		soup = BeautifulSoup(html_content, "html.parser")
		url_tag = soup.find("link", rel="canonical")
		if url_tag is not None:
			image_url = url_tag.get("href")
			article_name = image_url.split("/")[-1].split("?")[0]
		else:
			article_name = filename.split(".")[0]

		# Extract figures from the HTML
		figures = self.extract_figures_from_html(soup)
		article_json = {}
		figure_number = 1

		for figure in figures:
			img_tags = figure.find_all("img")

			for img_tag in img_tags:
				img_url = img_tag.get("src")
				captions = figure.find_all("p")

				figure_caption = ""
				for caption in captions:
					figure_caption += caption.get_text()

				if img_url is not None:
					response = requests.get("https:" + img_url, stream=True)

					figure_name = f"{article_name}_fig{figure_number}.jpg"
					figure_path = Path("output") / "figures" / figure_name
					# print('init_figurepath',figure_path )
					# initialize the figure's json
					figure_json = {
						"title": soup.find("title").get_text(),
						"article_name": article_name,
						"image_url": img_url,
						"figure_name": figure_name,
						"full_caption": figure_caption,
						"figure_path": str(figure_path),
						"master_images": [],
						"article_url":[],
						"license": [],
						"open": [],
						"unassigned": {
							"master_images": [],
							"dependent_images": [],
							"inset_images": [],
							"subfigure_labels": [],
							"scale_bar_labels": [],
							"scale_bar_lines": [],
							"captions": [],
						},
					}
					# add all results
					article_json[figure_name] = figure_json
					figure_number += 1  # increment figure number
					# Open a file with write binary mode, and write to it
					figures_directory = self.results_directory / "figures"
					figure_path = figures_directory / figure_name
					# print(f"{figure_path=}")
					with open(figure_path, 'wb') as out_file:
						shutil.copyfileobj(response.raw, out_file)
		return article_json

	def _load_model(self):
		pass

	def get_journal(self, filename):
		keywords = ['acs', 'nature', 'wiley', 'rsc']
		category = None

		with open(filename, "r", encoding="utf-8") as file:
			html_content = file.read()

		soup = BeautifulSoup(html_content, "html.parser")
		# Find all 'a' tags

		for link in soup.find_all('a'):
			url = link.get('href')
			for keyword in keywords:
				if keyword in url:
					category = keyword
					break
			if category:
				break
		return category

	def _update_exsclaim(self, exsclaim_dict, article_dict):
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

	def _appendJSON(self, filename, exsclaim_json):
		"""Commit updates to exsclaim json and update list of scraped articles

		Args:
			filename (string): File in which to store the updated EXSCLAIM JSON
			exsclaim_json (dict): Updated EXSCLAIM JSON
		"""
		with open(filename, "w") as f:
			json.dump(exsclaim_json, f, indent=3)
		articles_file = self.results_directory / "_articles"

	def _run_loop_function(self, search_query, exsclaim_json: dict, figure: Path, new_separated: set):
		...

	def run(self, search_query, exsclaim_json=None):
		"""Run the HTMLScraper to retrieve figures from user provided htmls

		Args:
			search_query (dict): A Search Query JSON to guide search
			exsclaim_json (dict): An EXSCLAIM JSON to store results in
		Returns:
			exsclaim_json (dict): Updated with results of search
		"""
		if exsclaim_json is None:
			exsclaim_json = {}
		directory_path = search_query["html_folder"]

		articles = glob(os.path.join(directory_path, '*.html'))

		html_directory = self.results_directory / "html"
		html_directory.mkdir(exist_ok=True)

		counter = 1
		t0 = timer()
		# Extract figures, captions, and metadata from each article
		for counter, article in enumerate(articles, start=1):
			with open(article, "r", encoding="utf-8") as file:
				html_article = file.read()
			soup = BeautifulSoup(html_article, "html.parser")
			url_tag = soup.find("link", rel="canonical")
			# print('url_tag', url_tag)
			if url_tag is not None:
				url = url_tag.get("href")
				with open(html_directory / (url.split("/")[-1] + ".html"), "w", encoding="utf-8") as file:
					file.write(str(soup))
			else:
				soup = BeautifulSoup(html_article, 'html.parser')
				meta_tag = soup.find('meta', attrs={'name': 'pbContext'})
				content = meta_tag['content']
				doi_str = [s for s in content.split(';') if 'doi' in s]
				article_doi_list = [doi for doi in doi_str if doi.startswith('article')]
				article_name = article_doi_list[0].split('\\:')[1].split("/")[1]
				with open(html_directory / (article_name + ".html"), "w", encoding="utf-8") as file:
					file.write(str(soup))


			self.display_info(f">>> ({counter} of {len(articles)}) Extracting figures from: {article.split('/')[-1]}")
			journal_name = self.get_journal(article)

			if journal_name == 'nature':
				article_dict = self.save_figures_nature(article)

			if journal_name == 'acs':
				article_dict = self.save_figures_acs(article)

			if journal_name == 'wiley':
				article_dict = self.save_figures_wiley(article)

			if journal_name == 'rsc':
				article_dict = self.save_figures_rsc(article)

			exsclaim_json = self._update_exsclaim(exsclaim_json, article_dict)

			if counter % 1000 == 0:
				self._appendJSON(self.results_directory / "exsclaim.json", exsclaim_json)

		time_diff = (timer() - t0) / 1e9
		self.display_info(f">>> Time Elapsed: {time_diff:,.2f} sec\t({counter - 1:,} articles)\n")
		self._appendJSON(self.results_directory / "exsclaim.json", exsclaim_json)
		return exsclaim_json

		# return self._run(search_query,
		# 				 exsclaim_json,
		# 				 "HTML Scraper",
		# 				 "_captions",
		# 				 "Parsing captions")


class CaptionDistributor(ExsclaimTool):
	"""
	CaptionDistributor object.
	Distribute subfigure caption chunks from full figure captions
	in an exsclaim_dict using custom caption nlp tools
	Parameters:
	model_path: str
		Absolute path to caption nlp model
	"""

	def __init__(self, search_query:dict=None):
		super().__init__(search_query if search_query is not None else {}, __name__ + ".CaptionDistributor")
		self.model_path = ""

	def _load_model(self):
		if "" in self.model_path:
			self.model_path = os.path.dirname(__file__) + "/captions/models/"
		# return caption.load_models(self.model_path) # TODO: Find out where load_models comes from

	def _update_exsclaim(self, search_query, exsclaim_dict, figure_name, delimiter, caption_dict):
		from exsclaim import caption

		llm = search_query["llm"]
		api = search_query["openai_API"]
		exsclaim_dict[figure_name]["caption_delimiter"] = delimiter
		html_filename = exsclaim_dict[figure_name]["article_name"]
		embeddings = OpenAIEmbeddings( openai_api_key=api)
		loader = UnstructuredHTMLLoader(os.path.join("output", search_query["name"], "html", f'{html_filename}.html'))
		documents = loader.load()
		# loader = UnstructuredHTMLLoader(os.path.join("exsclaim", "output", exsclaim_dict["name"], "html", f'{html_filename}.html'))
		for label in caption_dict.keys():

			# figure_name_part = (exsclaim_dict[figure_name]["figure_name"].split('.')[0]).split('_')[-1]
			# label_str = str(label)  # Ensure label is a string
			# caption = str(caption_dict.get(label, ''))  # Safely get the caption as a string
			# query = figure_name_part + label_str + " " + caption

			query = (exsclaim_dict[figure_name]["figure_name"].split('.')[0]).split('_')[-1] + str(label) + " " + str(caption_dict.get(label, ''))# caption_dict[label]
			# print(query)
			master_image = {
				"label": label,
				"description": caption_dict[label],  # ["description"],
				"keywords": safe_summarize_caption(query, api, llm).split(', '),
				# "context": get_context(query, documents, embeddings),
				# "general": get_keywords(get_context(query, documents, embeddings), api, llm).split(', '),
			}
			exsclaim_dict[figure_name]["unassigned"]["captions"].append(master_image)
		return exsclaim_dict

	def _appendJSON(self, exsclaim_json, captions_distributed):
		"""Commit updates to EXSCLAIM JSON and updates list of ed figures

		Args:
			results_directory (string): Path to results directory
			exsclaim_json (dict): Updated EXSCLAIM JSON
			figures_separated (set): Figures which have already been separated
		"""
		with open(self.results_directory / "exsclaim.json", "w") as f:
			json.dump(exsclaim_json, f, indent=3)
		with open(self.results_directory / "_captions", "a+") as f:
			for figure in captions_distributed:
				f.write("%s\n" % figure.split("/")[-1])

	def _run_loop_function(self, search_query, exsclaim_json:dict, figure:Path, new_separated:set):
		caption_text = exsclaim_json[figure_name]["full_caption"]
		# print('full caption',caption_text)
		delimiter = 0
		llm = search_query["llm"]
		# print(f"{llm=}")
		api = search_query["openai_API"]
		# print('api',api)
		caption_dict = safe_separate_captions(caption_text, api, llm="gpt-3.5-turbo")
		# caption.associate_caption_text( # here add the gpt3 code separate_captions(caption_text) #
		#  model, caption_text, search_query["query"]
		# )
		print(f"full caption dict: {caption_dict}")
		exsclaim_json = self._update_exsclaim(search_query,
											  exsclaim_json, figure, delimiter, caption_dict
											  )
		new_captions_distributed.add(figure_name)
		return exsclaim_json

	def run(self, search_query, exsclaim_json):
		"""Run the CaptionDistributor to distribute subfigure captions

		Args:
			search_query (dict): A Search Query JSON to guide search
			exsclaim_json (dict): An EXSCLAIM JSON to store results in
		Returns:
			exsclaim_json (dict): Updated with results of search
		"""
		return self._run(search_query,
						 exsclaim_json,
						 "Caption Separator",
						 "_captions",
						 "Parsing captions")
