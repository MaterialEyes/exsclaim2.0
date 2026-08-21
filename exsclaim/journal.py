from .exceptions import JournalScrapeError
from .utilities import paths

import asyncio
import cairosvg
import curl_cffi
import httpx2
import inspect
import json
import logging
import math
import re
import sys
import urllib.parse

from abc import ABC, abstractmethod, ABCMeta
from bs4 import BeautifulSoup
from datetime import datetime
from itertools import product
from pathlib import Path
from playwright.async_api import Playwright, Locator, async_playwright, Response, PlaywrightContextManager, Cookie
from playwright._impl import _errors as playwright_errors
from playwright_stealth import Stealth
from starlette.datastructures import URL
from typing import Any, Awaitable, Callable, Iterable, Literal, Optional, Self, Type, overload


__all__ = ["JournalFamily", "JournalFamilyStatic", "JournalFamilyDynamic", "ACS", "Nature", "RSC", "Wiley", "COMPATIBLE_JOURNALS"]

URLParams = dict[str, Any]
DOI_REGEX = r"(10\.\d{4,9})/([-.;()/:\w]+)"
ResponseFunction = str | re.Pattern[str] | Callable[[Response], bool | Awaitable[bool]]


class JournalMeta(ABCMeta):
	subclasses: dict[str, Type] = dict()

	def __new__(cls, name, bases, dct):
		_new = super().__new__(cls, name, bases, dct)

		if name != "JournalFamily" and name != "JournalFamilyStatic" and name != "JournalFamilyDynamic":
			JournalMeta.subclasses[name] = _new
		return _new

	def __call__(cls, *args, **kwargs):
		if cls != JournalFamily:
			return super().__call__(*args, **kwargs)

		journal_name, *args = args
		journal_name = journal_name.lower()
		for name, subclass in JournalMeta.subclasses.items():
			if journal_name == name.lower() or journal_name == subclass.name().lower():
				return subclass.__call__(*args, **kwargs)

		raise NameError(f"Journal family {journal_name} is not defined.")

	def __iter__(cls):
		return iter(JournalMeta.subclasses.items())


class JournalHtml(ABC):
	"""A base class to create a general base on manipulating HTML without removing any functionality of the browser types."""
	@abstractmethod
	async def select(self, selector: str) -> tuple["JournalHtml"]:
		"""Select all HTML elements that match the given CSS selector."""

	@abstractmethod
	def select_one(self, selector: str) -> "JournalHtml":
		"""Select the first (or only) HTML element that matches the given CSS selector"""

	@abstractmethod
	async def get_text(self) -> str:
		"""Gets the internal text within an element."""

	@abstractmethod
	async def get_html(self) -> str:
		"""Gets the html within an element."""

	@abstractmethod
	async def get(self, attribute: str) -> str:
		"""Gets the value of a given attribute."""

	@abstractmethod
	async def prettify(self) -> str:
		"""Returns the HTML is a legible manner."""

	@abstractmethod
	async def contains(self, text: str) -> bool:
		"""Checks if the given text is in the element's HTML."""

	@abstractmethod
	async def is_visible(self) -> bool:
		"""Checks if a given element is visible."""

	@abstractmethod
	async def get_data_value(self, attribute: str) -> str:
		"""Returns the attribute from the element's dataset."""

	async def __aenter__(self) -> Self:
		return self

	async def __aexit__(self, *args, **kwargs):
		await self.close()

	async def close(self):
		...


class StaticHtml(JournalHtml):
	__slots__ = ("soup")

	def __init__(self, soup: BeautifulSoup):
		self.soup = soup

	async def select(self, selector: str) -> tuple["StaticHtml"]:
		return tuple((StaticHtml(html) for html in self.soup.select(selector)))

	def select_one(self, selector: str) -> "StaticHtml":
		return StaticHtml(self.soup.select_one(selector))

	async def get_text(self) -> str:
		return self.soup.get_text()

	async def get_html(self) -> str:
		return str(self.soup)

	async def get(self, attribute: str) -> Optional[str]:
		return self.soup.get(attribute)

	async def prettify(self) -> str:
		return self.soup.prettify()

	def __contains__(self, text) -> bool:
		return text in str(self.soup)

	async def contains(self, text: str) -> bool:
		return text in self

	async def is_visible(self) -> bool:
		return (self.soup is not None) and (self.soup.contents is not None)

	async def get_data_value(self, attribute: str) -> str:
		value = self.soup.get(attribute)
		if value is None:
			raise AttributeError(f"Could not find data attribute value for {attribute}.")
		return value

	def __bool__(self) -> bool:
		return bool(self.soup)

	def __str__(self) -> str:
		return str(self.soup)

	async def __aexit__(self, *args, **kwargs):
		del self.soup


class DynamicHtml(JournalHtml):
	__slots__ = ("locator")

	def __init__(self, locator: Locator):
		if not isinstance(locator, Locator):
			raise ValueError(f"DynamicHTML objects need to be given a Locator object to work with.")
		self.locator = locator

	def __del__(self):
		if not hasattr(self, "locator"):
			logging.getLogger("exsclaim").warning("DynamicHTML object has no locator when trying to delete parent object.")
			return

		page_references = sys.getrefcount(self.locator.page)
		if page_references > 1:
			return

		if not self.locator.page.is_closed():
			asyncio.get_event_loop().create_task(self.locator.page.close())

	async def select(self, selector: str) -> tuple["DynamicHtml"]:
		return tuple(map(DynamicHtml, await self.locator.locator(selector).all()))

	def select_one(self, selector: str) -> "DynamicHtml":
		return DynamicHtml(self.locator.locator(selector).nth(0))
		# all_locators = await self.locator.locator(selector).all()
		# if not all_locators:
		# 	raise Attr("No locators available")
		# return DynamicHtml(all_locators[0])

	async def get_text(self) -> str:
		return await self.locator.inner_text()

	async def get_html(self) -> str:
		return await self.locator.inner_html()

	async def get(self, attribute: str) -> str:
		return await self.locator.get_attribute(attribute)

	async def prettify(self) -> str:
		page = self.locator.page
		html: str = await page.locator("html").inner_html()
		del page
		return html

	async def contains(self, text: str) -> bool:
		return text in await self.locator.inner_html()

	async def is_visible(self) -> bool:
		return await self.locator.is_visible()

	@staticmethod
	def convert_dataset_name(attribute: str) -> str:
		attribute = attribute.split("-")
		if attribute[0] == "data":
			attribute = attribute[1:]

		for i, part in enumerate(attribute):
			if i == 0:
				attribute[i] = part.lower()
			else:
				attribute[i] = part[0].upper() + part[1:].lower()

		return "".join(attribute)

	async def get_data_value(self, attribute: str) -> str:
		if attribute.startswith("data-"):
			attribute = self.convert_dataset_name(attribute)
		value = await self.locator.evaluate(f"el => el.dataset.{attribute}")
		if value is None:
			raise AttributeError(f"Could not find data attribute value for {attribute}.")
		return value

	def __bool__(self) -> bool:
		return bool(self.locator)

	def __str__(self) -> str:
		return str(self.locator)

	async def close(self):
		await self.locator.page.close()
		del self.locator


class JournalFamily[T: JournalHtml](ABC, metaclass=JournalMeta):
	"""Base class to represent journals and provide scraping methods.
	This class defines the interface for interacting with JournalFamilies.
	A JournalFamily is a collection of academic journals with articles
	hosted on a single domain. For example *Nature* is a single journal
	family that serves articles from both *Scientific Reports* and
	*Nature Communications* (and many others) on nature.com.
	The attributes defined mainly consist of documenting the format
	of urls in the journal family. Two urls are of interest:
		* search_results_url: the url one goes to in order to query
		journal articles, and the associated url parameters to filter
		those queries
		* article_url: the general form of the url path containing **html**
		versions of article
	The methods of this class are focused on parsing the html structure
	of the page types returned by the two url types above.
	There are two major types of JournalFamilies (in the future, these
	may make sense to be split into separate subclasses of JournalFamily):
	static and dynamic. Static journal families serve all results using
	static HTML. Nature is an example. These are simpler as GET requests
	alone will return all the relevant data. Dynamic families utilize
	JavaScript to populate results so a browser emulator like selenium
	is used. RSC is an example of a dynamic journal.
	**Contributing**: If you would like to add a new JournalFamily, decide
	whether a static or dynamic one is needed and look to an existing
	subclass to base your efforts. Create an issue before you start so your
	efforts are not duplicated and submit a PR upon completion. Thanks!
	"""
	# journal attributes -- these must be defined for each journal
	# family based on the explanations provided here

	@classmethod
	def name(cls) -> str:
		return cls.__name__

	@property
	def domain(self) -> str:
		"""The domain name of journal family"""
		return self._domain

	# the next 6 fields determine the url of journals search page
	@property
	def search_path(self) -> str:
		"""URL portion from the end of top level domain to query parameters"""
		return self._search_path

	# params should include trailing '='
	@property
	def page_param(self) -> str:
		"""URL parameter noting current page number"""
		return self._page_param

	@property
	def max_page_size(self) -> str:
		"""URL parameter and value requesting max results per page
		Used to limit total number of requests.
		"""
		return self._max_page_size

	@property
	def order_param(self) -> str:
		"""URL parameter noting results order"""
		return self._order_param

	@property
	def author_param(self) -> str:
		"""URL parameter noting results order"""
		return self._author_param

	@property
	def journal_param(self) -> str:
		"""URL parameter noting journal to search"""
		return self._journal_param

	@property
	def date_range_param(self) -> str:
		"""URL parameter noting range of dates to search"""
		return self._date_range_param

	@property
	def order_values(self) -> dict:
		"""Dictionary with journal parameter values for sorting results
		'relevant' for ordering results in order of relevance
		'recent' for ordering results most recent first
		'old' for ordering results oldest first
		"""
		return self._order_values

	@property
	def join(self) -> str:
		"""Separator in URL between multiple search terms"""
		return self._join

	@property
	def max_query_results(self) -> int:
		"""Maximum results journal family will return for single query
		Certain journals will restrict a given search to ~1000 results
		"""
		return self.__max_query_results

	# used for get_article_delimiters
	@property
	def articles_path(self) -> str:
		"""The journal's url path to articles.
		Articles are located at domain.name/articles_path/article
		"""
		return self._articles_path

	@property
	def articles_path_length(self) -> int:
		"""Number of / separated segments to articles path"""
		return self._articles_path_length

	@property
	def prepend(self) -> str:
		return self._prepend or self._domain

	@property
	def extra_key(self) -> str:
		return self._extra_key

	def __init__(self, search_query: dict, name_patterns: Iterable[tuple[re.Pattern, int]] = (), **kwargs):
		"""Creates an instance of a journal family search using a query
		Args:
			search_query: a query json (python dictionary)
			name_patterns: A list of tuples containing a regex pattern used to extract the id from a link, and the group number that ID exists in
		Returns:
			An initialized instance of a search on a journal family
		"""
		self.search_query = search_query
		self._name_patterns = name_patterns
		self.open = search_query.get("open", False)
		self.order = search_query.get("sortby", "relevant")
		self.logger = kwargs.get("logger", logging.getLogger(__name__))

		# Set up file structure
		base_results_dir = paths.initialize_results_dir(search_query.get("results_dir", None))
		self.results_directory = base_results_dir / self.search_query["name"]
		figures_directory = self.results_directory / "figures"
		figures_directory.mkdir(exist_ok=True, parents=True)

		# Check if any articles have already been scraped by checking
		# results_dir/_articles
		articles_visited: set[str] = set()
		articles_file = self.results_directory / "_articles"
		if articles_file.is_file():
			with open(articles_file, "r") as f:
				articles_visited = {a.strip() for a in f.readlines()}
		self.articles_visited = articles_visited
		self.include_hidden_figures = kwargs.get("include_hidden_figures", False)

	async def load(self):
		if hasattr(self, "_loaded"):
			return True
		self._loaded = True
		return False

	async def __aenter__(self) -> Self:
		await self.load()
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		await self.close()

	@staticmethod
	async def get_cloudflare_headers(url: str, logger: logging.Logger, playwright: Optional[Playwright] = None) -> tuple[dict[str, str], list[dict[str, str]]]:
		"""
		Uses playwright to pass Cloudflare's checks, then returns the headers for use with other session types.
		Args:
			url (str): The URL that is blocked by Cloudflare
			playwright (Playwright, optional): The playwright to pass Cloudflare's checks):

		Returns:

		"""
		stealth = None
		if playwright is None:
			stealth = Stealth().use_async(async_playwright())
			playwright = await stealth.start()

		browser = await playwright.chromium.launch()
		page = await browser.new_page()

		response = await page.goto(url)

		if response.status >= 400:
			timeout = 35
			logger.info(f"Playwright could not immediately bypass Cloudflare's checks. Waiting {timeout} seconds to see if it passes.")
			page.expect_response(lambda response: response.url == url and 200 <= response.status < 300,
								 timeout=timeout * 1000)
			response = await page.goto(url)
			if response.status >= 400:
				html = await response.text()
				raise JournalScrapeError("Could not get passed Cloudflare defense page.", response.status, response.headers.copy(),
										 url, html)

		headers = dict(filter(lambda header: "cf" in header[0].lower(), response.headers.items()))
		cookies = await page.context.cookies()

		if stealth is not None:
			await stealth.__aexit__()

		return headers, cookies

	# Helper Methods for retrieving relevant article URLS

	@abstractmethod
	async def get_page_info(self, html: T) -> tuple[int, int, int]:
		"""Retrieve details on total results from search query
		:param JournalHtml html: An HTML object representing the search results page
		:rtype: tuple[int, int, int]
		:returns: (index origin, total page count in search, total results from search)
		"""

	@abstractmethod
	def get_search_params(self, terms: tuple[str]) -> dict[str, Any]:
		"""Generate the URL parameters for the search in the necessary order"""
		...

	async def turn_page(self, html: T, url: str, page_number: int) -> T:
		"""Return page_number page of search results
		Args:
			html: the HTML of the page, if the turning happens through JavaScript
			url: the url to a search results page
			page_number: page number to search on
		Returns:
			soup of next page
		"""
		if self.page_param not in url:
			url = f"{url}&{self.page_param}={page_number}"
		else:
			_url = urllib.parse.urlsplit(url)
			_query = urllib.parse.parse_qs(_url.query)
			_query[self.page_param] = [str(page_number)]
			query_string = urllib.parse.urlencode(_query, doseq=True)
			url = _url._replace(query=query_string).geturl()

		return await self.get(url)

	@abstractmethod
	async def get_additional_url_arguments(self, html: T) -> tuple[list[str], set[str], list[str]]:
		"""Get lists of additional search url parameters.
		Some JournalFamilies limit the number of articles returned by a single search.
		In order to retrieve articles beyond this, we create additional search
		non-overlapping sets, and execute them individually.
		:param bs4.BeautifulSoup html: initial search result for search term
		:rtype: tuple[list[str], set[str], list[str]]
		:returns:
			(years, journal_codes, orderings): where:
			    years is a list of strings of desired date ranges
			    journal_codes is a set of strings of desired journal codes
			    orderings is a list of strings of desired results ordering
			Each of these should be in order of precedence.
		"""

	# Helper Methods for retrieving figures from articles
	@abstractmethod
	async def get_license(self, html: T) -> tuple[bool, str]:
		"""Checks the article license and whether it is open access
		Args:
			html: representation of page HTML
		Returns:
			is_open (a bool): True if article is open
			license (a string): Required text of article license
		"""
		return False, "unknown"

	@abstractmethod
	async def get_authors(self, html: T) -> tuple[str]:
		"""Retrieve list of authors from search results

		:param JournalHtml html: A soup object representing the article page.
		:rtype: tuple[str]
		:returns: A list of each author's name
		"""
		...

	@abstractmethod
	async def get_figure_url(self, figure: T) -> str:
		"""Returns the absolute url of figure from figure's html subtree
		:param JournalHtml figure: subtree containing an article figure
		:returns: The URL source for the image
		:rtype: str
		"""
		...

	async def get_figure_list(self, html: T) -> tuple[T]:
		"""
		Returns list of figures in the given url
		Args:
			html: a JournalHtml object representing the page
		Returns:
			A list of all figures in the article as BeautifulSoup Tag objects
		"""
		figures = []
		for figure in await html.select("figure"):
			if await figure.contains(self.extra_key):
				if not self.include_hidden_figures and not await figure.is_visible():
					continue
				figures.append(figure)
		return tuple(figures)

	async def get_caption(self, figure_subtree: T) -> str:
		"""
		Returns all captions associated with a given figure
		Args:
			figure_subtree: an bs4 parse tree
		Returns:
			all captions for the given figure
		"""
		caption_elements = await figure_subtree.select("p")
		return "".join([(await caption.get_html()).strip() for caption in caption_elements])

	# @abstractmethod
	async def is_link_to_open_article(self, article: T) -> bool:
		"""Checks if link is to an open access article
		:param bs4.Tag article: A tag containing an href attribute that links to an article, or the direct link to the article:
		:returns: True if the article is open_access
		:rtype: bool
		"""
		return self.open

	@staticmethod
	async def _get_image(url: str, client: curl_cffi.AsyncClient, *args, **kwargs) -> bytes:
		response = await client.get(url)
		response.raise_for_status()

		return await response.aread()

	async def _get_image_stream(self, client: curl_cffi.AsyncClient | httpx2.AsyncClient, image_url: str, save_file: Path, chunk_size: int = 1_024,
								sleep_time: float = 30, retries: int = 5):
		for retry in range(retries):
			async with client.stream("GET", image_url) as response:
				response.raise_for_status()

				content_type = response.headers["Content-Type"]
				if not content_type.startswith("image/"):
					retry += 1
					if retry == retries:
						html = await response.aread()
						raise JournalScrapeError(f"The image url did not return image information, instead the content is of type {content_type}.", response.status_code,
												 headers=response.headers, url=image_url, html=html)

					self.logger.info(f"Attempt {retry}/{retries} {image_url} responded with content type: {content_type}. Waiting for {sleep_time} seconds before retrying.")
					await asyncio.sleep(sleep_time)
					continue

				if isinstance(response, httpx2.Response):
					iter_method = response.aiter_bytes
				elif isinstance(response, curl_cffi.Response):
					iter_method = response.aiter_content
				else:
					raise TypeError(f"Unknown response type returned when trying to stream the image: {type(response).__name__}.")

				with open(save_file, "wb") as f:
					async for chunk in iter_method(chunk_size=chunk_size):
						f.write(chunk)

				return

	async def save_figure(self, figure_name: str, image_url: str, chunk_size: int = 1_024) -> Path:
		"""
		Saves figure at img_url to local machine
		Args:
			figure_name: name of figure
			image_url: url to image
		"""
		out_file = self.results_directory / "figures" / figure_name

		try:
			if hasattr(self, "client"):
				await self._get_image_stream(self.client, image_url, out_file, chunk_size=chunk_size)
				return out_file
		except httpx2.HTTPStatusError as e:
			response = e.response
			raise JournalScrapeError(f"Could not save figure by streaming from {image_url}. Attempting to load the full image.",
									 response.status_code, response.headers, image_url, response.url) from e

		try:
			image_source = await self.get_image_source(image_url)
		except httpx2.HTTPStatusError as e:
			response = e.response
			raise JournalScrapeError(f"Could not save figure by streaming from {image_url}. Attempting to load the full image.",
									 response.status_code, response.headers, image_url, response.url) from e

		with open(out_file, 'wb') as f:
			f.write(image_source)

		return out_file

	async def get_search_query_urls(self) -> tuple[str, list[URLParams]]:
		"""Create list of search query urls based on input query json

		Returns:
			A list of urls (as strings)
		"""
		search_query = self.search_query
		# creates a list of search terms
		try:
			search_list = [
				[value["term"]] + value.get("synonyms", list()) for key, value in search_query["query"].items()
			]
		except TypeError as e:
			self.logger.exception(f"{search_query=}", exc_info=e)
			raise e
		search_product = product(*search_list)

		search_url = self.domain + self.search_path
		search_url_args = []
		for term in search_product:
			url_parameters = self.get_search_params(term)
			soup = await self.get(search_url, params=url_parameters)

			years, journal_codes, orderings = await self.get_additional_url_arguments(soup)
			starting_length = len(search_url_args)

			for year_value, journal_value, order_value in product(years, journal_codes, orderings):
				params = url_parameters.copy()
				params.update({
					self.date_range_param: year_value,
					self.journal_param: journal_value,
					self.order_param: order_value
				})
				search_url_args.append(params)

			if len(search_url_args) == starting_length:
				search_url_args.append(url_parameters)

		return search_url, search_url_args

	@abstractmethod
	async def get_articles_from_search_page(self, html: T) -> tuple[T]: ...

	@abstractmethod
	async def get_link_for_article(self, article: T) -> str: ...

	async def get_articles_from_search_url(self, search_url: str, search_query_args: URLParams) -> set[str]:
		"""Generates a list of articles from a single search term"""
		max_scraped = self.search_query["maximum_scraped"]
		html = await self.get(search_url, params=search_query_args)

		article_paths = set()

		try:
			start_page, stop_page, total_articles = await self.get_page_info(html)
		except (AttributeError, playwright_errors.TimeoutError, ValueError) as e:
			with open(self.results_directory / "new_error.html", 'w') as f:
				f.write(await html.prettify())
			raise JournalScrapeError(str(e), url=search_url, html=html) from e

		for page_number in range(start_page, stop_page + 1):
			articles = await self.get_articles_from_search_page(html)
			if len(articles) == 0:
				with open(self.results_directory / f"page_{page_number}.html", 'w') as f:
					f.write(await html.prettify())
				continue

			for article in articles:
				url = await self.get_link_for_article(article)
				raw_url = url.split("?")[0]

				if raw_url in self.articles_visited or (
						self.open and not (await self.is_link_to_open_article(article))
				):
					# It is an article but we are not interested
					continue

				article_paths.add(raw_url)
				if len(article_paths) >= max_scraped:
					return article_paths
			# Get next page at end of loop since page 1 is obtained from
			# search_url
			html = await self.turn_page(html, search_url, page_number + 1)

		await html.close()
		return article_paths

	async def get_article_extensions(self) -> tuple[str]:
		"""Retrieves a list of article url paths from a search query"""
		# This returns urls based on the combinations of desired search terms.
		article_paths: set[str] = set()
		search_url, search_query_args = await self.get_search_query_urls()

		for search_arg in search_query_args:
			new_article_paths = await self.get_articles_from_search_url(search_url, search_arg)
			article_paths.update(new_article_paths)
			if len(article_paths) >= self.search_query["maximum_scraped"]:
				break

		return tuple(article_paths)

	@staticmethod
	def _get_figure_name(article_name: str, figure_idx: int, extension: str = "jpg") -> str:
		return f"{article_name}_fig{figure_idx}.{extension}"

	def get_article_name_from_url(self, url: str) -> str:
		if url.startswith("/"):
			url = self.prepend + url

		for pattern, group_number in self._name_patterns:
			if (match := pattern.search(url)) is not None:
				return match.group(group_number)

		self.logger.info(f"Could not find the article ID for article: {url}.")
		return url.split("/")[-1].split("?")[0]

	async def get_figures(self, figure: T, figure_json: dict, url: str) -> tuple[dict, str]:
		image_url = await self.get_figure_url(figure)

		if not re.match("https?://.+", image_url):
			image_url = "https://" + image_url

		article_name = self.get_article_name_from_url(url)

		# initialize the figure's json
		figure_json |= dict(
			article_name=article_name,
			image_url=image_url,
			master_images=[],
			unassigned=dict(
				master_images=[],
				dependent_images=[],
				inset_images=[],
				subfigure_labels=[],
				scale_bar_labels=[],
				scale_bar_lines=[],
				captions=[],
			),
		)
		# add all results
		return figure_json, image_url

	async def get_title(self, html: T, url: str) -> str:
		return (await html.select_one("title").get_text()).strip()

	@staticmethod
	def convert_svg_to_image(image_path: Path, new_extension: str = "png"):
		new_path = image_path.with_suffix(f".{new_extension}")
		match new_extension:
			case "png":
				cairosvg.svg2png(url=str(image_path), write_to=str(new_path))
			case _:
				raise NotImplementedError("JournalScraper can only convert svg graphics to png images at the moment.")

	async def get_article_figures(self, url: str, html_directory: Path, save_html: bool = True, svg_extension: str = "png") -> dict:
		"""Get all figures from an article.
		:param str url: The url to the journal article.
		:param pathlib.Path html_directory: The path where any HTML files should be written.
		:param bool save_html: If the HTML for the page should be saved to the results directory. Default is False.
		:param str svg_extension: The extension that SVG images should be converted to. Default is "png".
		:returns: A dictionary of figure_jsons from an article
		"""
		try:
			html = await self.get(url)
		except JournalScrapeError as e:
			self.logger.error(f"Could not scrape {url} (HTTP Status Code: {e.status}). Reason: \"{e.message}\".")
			return dict()

		_id = self.get_article_name_from_url(url)
		if save_html:
			with open(html_directory / f"{_id}.html", 'w') as f:
				f.write(await html.prettify())

		try:
			is_open, _license = await self.get_license(html)
		except playwright_errors.TimeoutError as e:
			self.logger.error(f"Could not get license for {url}.")
			raise JournalScrapeError(f"Could not get license for: {url}.", url=url, html=html) from e

		title = await self.get_title(html, url)
		authors = await self.get_authors(html)
		figure_subtrees = await self.get_figure_list(html)

		self.logger.info(f"Number of subfigures: {len(figure_subtrees):,} for {_id}.")
		article_json = dict()

		for figure_number, figure_subtree in enumerate(figure_subtrees, start=1):
			figure_caption = await self.get_caption(figure_subtree)

			if len(figure_caption) == 0 or figure_caption.isspace():
				continue

			figure_json = {
				"title": title,
				"authors": authors,
				"article_url": url,
				"license": _license,
				"open": is_open,
				"full_caption": figure_caption,
			}

			try:
				figure_json, image_url = await self.get_figures(figure_subtree, figure_json, url)
			except ValueError as e:
				self.logger.exception(f"An error occurred trying to get the figures for {url}.", exc_info=e)
				raise e

			image_extension = image_url.split(".")[-1].split("?")[0]
			true_figure_name = self._get_figure_name(figure_json["article_name"], figure_number, image_extension)
			if image_extension == "svg":
				figure_name = self._get_figure_name(figure_json["article_name"], figure_number, svg_extension)
			else:
				figure_name = true_figure_name

			figure_path = Path(self.search_query["name"]) / "figures" / figure_name
			figure_json |= dict(
				image_url=image_url,
				figure_name=figure_name,
				figure_path=str(figure_path),
			)

			# save figure as image
			try:
				saved_image = await self.save_figure(true_figure_name, image_url)
				if image_extension == "svg":
					try:
						self.convert_svg_to_image(saved_image, svg_extension)
					except BaseException as e:
						self.logger.error(f"An error occurred when trying to convert {saved_image} into a(n) {image_extension} file.", exc_info=e)
			except JournalScrapeError as e:
				self.logger.error(f"Could not download figure \"{figure_name}\" from {image_url} (HTTP Status Code: {e.status}). Reason: {e.message}")
				continue

			article_json[figure_name] = figure_json

		await html.close()
		return article_json

	# region HTTP methods defined by JournalFamilyDynamic and JournalFamilyStatic
	@abstractmethod
	async def close(self):
		...

	@abstractmethod
	async def get(self, url: str, params: Optional[URLParams] = None) -> T:
		"""Get a BeautifulSoup parse tree (lxml parser) from a URL request
		:param str url: The requested URL.
		:param dict[str, Any] | None params: A dictionary of URL parameters that should be passed with the request.
		:rtype: bs4.BeautifulSoup
		:returns: A BeautifulSoup parse tree.
		:raises: exsclaim.exceptions.JournalScrapeError: If an error occurs while making the request.
		"""
		message = f"GET request: {url}"
		if params is not None:
			message += f"?{'&'.join(map(lambda p: f'{p[0]}={p[1]}', params.items()))}"
		self.logger.info(message)

	@abstractmethod
	async def get_image_source(self, url: str, **kwargs) -> bytes:
		...
# endregion


class JournalFamilyStatic(JournalFamily[StaticHtml], ABC):
	def __init__(self, search_query: dict, **kwargs):
		super().__init__(search_query, **kwargs)
		self.client = curl_cffi.AsyncSession(impersonate="chrome")

	async def close(self):
		await self.client.close()

	async def get(self, url: str, params: Optional[dict[str, Any]] = None, *args, **kwargs) -> StaticHtml:
		await super().get(url, params)
		response = await self.client.get(url, params=params)
		response.raise_for_status()

		return StaticHtml(BeautifulSoup(response.text, "html.parser"))

	async def get_image_source(self, url: str, *args, **kwargs) -> bytes:
		return await self._get_image(url, self.client, *args, **kwargs)


class JournalFamilyDynamic(JournalFamily[DynamicHtml], ABC):
	def __init__(self, search_query: dict, playwright: Optional[PlaywrightContextManager] = None, **kwargs):
		"""creates an instance of a journal family search using a query
		Args:
			search_query: a query json (python dictionary)
		"""
		from asyncio import Lock
		super().__init__(search_query, **kwargs)
		self.cache = dict()
		self.lock = Lock()
		self._given_playwright = playwright
		self._image_client = httpx2.AsyncClient()

	async def load(self):
		if await super().load():
			return True
		if self._given_playwright:
			playwright = self._given_playwright
		else:
			playwright = async_playwright()
			self._playwright = playwright

		self._stealth = Stealth().use_async(playwright)
		self._playwright = await self._stealth.start()
		self._browser = await self._playwright.chromium.launch(headless=True)
		await self.get_cloudflare_headers(self.domain, self.logger, self._playwright)
		return False

	async def __aenter__(self) -> Self:
		await self.load()
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		await self._stealth.__aexit__(exc_type, exc_val, exc_tb)

	async def close(self):
		await self._browser.close()
		if hasattr(self, "_playwright"):
			await self._playwright.stop()

	async def response_handler(self, response: Response):
		if response.status >= 400:
			return

		url = response.url
		if url.startswith("https://pubs.rsc.org/image/article/"):
			async with self.lock:
				self.cache[url] = await response.body()

	@overload
	async def get(self, url: str, params: Optional[URLParams] = None, return_html: Literal[True] = True,
				  response_handlers: Optional[Iterable[Callable[[Response], Any]]] = None,
				  final_response_handlers: Optional[Iterable[Callable[[Response], Any]]] = None,
				  predicate: Optional[ResponseFunction] = None,
				  *args, **kwargs) -> DynamicHtml:
		...

	@overload
	async def get(self, url: str, params: Optional[URLParams] = None, return_html: Literal[False] = False,
				  response_handlers: Optional[Iterable[Callable[[Response], Any]]] = None,
				  final_response_handlers: Optional[Iterable[Callable[[Response], Any]]] = None,
				  predicate: Optional[ResponseFunction] = None,
				  *args, **kwargs) -> None:
		...

	async def get(self, url: str, params: Optional[URLParams] = None, return_html: bool = True,
				  response_handlers: Optional[Iterable[Callable[[Response], Any]]] = None,
				  final_response_handlers: Optional[Iterable[Callable[[Response], Any]]] = None,
				  predicate: Optional[ResponseFunction] = None,
				  *args, **kwargs) -> Optional[DynamicHtml]:
		await super().get(url, params=params)
		page = await self._browser.new_page()
		page.on("response", self.response_handler)

		attempts = kwargs.get("attempts", 3)

		if params is not None:
			url = URL(url)
			url = url.include_query_params(**params)
			url = str(url)

		if response_handlers is not None:
			for response_handler in response_handlers:
				page.on("response", response_handler)

		def default_predicate(resp: Response):
			self.logger.debug(f"[{resp.status}] {resp.url=}")
			return resp.url == url and resp.status < 300

		for attempt in range(attempts):
			try:
				async with page.expect_response(predicate or default_predicate, timeout=60_000) as resp2:
					await page.goto(url)

				response = await resp2.value
				break
			except playwright_errors.TimeoutError as e:
				if attempt + 1 == attempts:
					raise
				else:
					self.logger.warning(f"[{attempt+1:,}/{attempts:,}] {url} could not connect within a minute. Trying again.", exc_info=e)

		if final_response_handlers is not None:
			for response_handler in final_response_handlers:
				if inspect.iscoroutinefunction(response_handler):
					await response_handler(response)
				else:
					response_handler(response)

		if response.status >= 400:
			html = StaticHtml(BeautifulSoup(await response.text(), "html.parser"))
			raise JournalScrapeError(f"Could not get {url}.", response.status, response.headers, url=url, html=html)

		if return_html:
			return DynamicHtml(page.locator("html"))

		return None

	async def save_figure(self, figure_name: str, image_url: str, chunk_size: int = 1_024) -> Path:
		"""
		Saves figure at img_url to local machine
		Args:
			figure_name: name of figure
			image_url: url to image
		"""
		out_file = self.results_directory / "figures" / figure_name

		try:
			await self._get_image_stream(self._image_client, image_url, out_file, chunk_size=chunk_size)
			return out_file
		except httpx2.HTTPStatusError as e:
			self.logger.warning(f"Could not save figure by streaming from {image_url}. Attempting to load the full image.", exc_info=e)

		async def write_image_from_response(response: Response):
			body = await response.body()
			with open(out_file, "wb") as f:
				f.write(body)

		await self.get(image_url, return_html=False, final_response_handlers=[write_image_from_response])
		return out_file

	async def get_image_source(self, url: str, *args, **kwargs) -> bytes:
		await super().get(url)
		async with self.lock:
			if url in self.cache:
				self.logger.info(f"Using cached {url}.")
				return self.cache[url]

		page = await self._browser.new_page()
		response = await page.goto(url)
		if response.status >= 400:
			raise JournalScrapeError(await response.text(), response.status, response.headers, url=url)

		return await response


# ############# JOURNAL FAMILY SPECIFIC INFORMATION ################
# To add a new journal family, create a new subclass of JournalFamily.
# Fill out the methods and attributes according to their descriptions in the JournalFamily class.
# Then add an entry to the journals dictionary with the journal family's name in all lowercase as the key and
# the new class as the value.
# ##################################################################


class ACS(JournalFamilyDynamic):
	def __init__(self, search_query: dict, **kwargs):
		name_patterns = (
			(re.compile(r"/(\w{6})/article/doi/(10\.\d{4,9})/([-._;()/:A-Z0-9]+)/(\d+)/.+", re.I), 3),
			(re.compile(r"/(\w{6})/article/(\d+)", re.I), 2)
		)
		super().__init__(search_query, name_patterns=name_patterns, **kwargs)
		self._domain = "https://pubs.acs.org"
		self._search_path = "/search-results"
		self._max_page_size = "pageSize=100"
		self._page_param = "startPage="
		self._order_param = "sortBy"
		self._journal_param = "SeriesKey"
		self._date_range_param = "Earliest"

		# order options
		self._order_values = {
			"relevant": "relevancy",
			"old": "Earliest_asc",
			"recent": "Earliest",
		}
		self._join = '"+"'

		self._articles_path = "/doi/"
		self._prepend = "https://pubs.acs.org"
		self._extra_key = "inline-fig internalNav"
		self._articles_path_length = 3
		self._max_query_results = 1_000

	def get_search_params(self, terms: tuple[str]) -> dict[str, str | int]:
		"""Generate the URL parameters for the search in the necessary order"""
		params = {
			"page": 1,
			"q": terms[0]
		}

		if self.open:
			params["openAccess"] = 1
			params["accessType"] = "openAccess"

		return params

	async def get_additional_url_arguments(self, html: DynamicHtml):
		# rsc allows unlimited results, so no need for additional args
		return [], {}, []

	async def get_page_info(self, html: DynamicHtml):
		total_results = html.select_one("div.sr-statistics.at-sr-statistics")
		text_ = await total_results.get_text()
		results_match = re.search(r"\s*(\d+)-(\d+)\s*of\s*(\d+)", text_)
		if results_match is None:
			raise JournalScrapeError("Could not find total number of articles found for the ASC search.", html=await html.prettify())

		start_article_num = int(results_match.group(1))
		end_article_num = int(results_match.group(2))
		total = int(results_match.group(3))

		articles_per_page = (1 + end_article_num - start_article_num)
		total_pages = math.ceil(total / articles_per_page)

		return 1, total_pages, total

	async def is_link_to_open_article(self, article: DynamicHtml) -> bool:
		return len(await article.select("i.icon-availability_open")) > 0

	async def get_articles_from_search_page(self, html: DynamicHtml) -> tuple[DynamicHtml]:
		return await html.select("div.sr-list.al-article-box.al-normal.clearfix.content-type-journal-articles")

	async def get_link_for_article(self, article: DynamicHtml) -> str:
		return await article.select_one("h4").select_one("a[href]").get("href")

	async def old_get_articles_from_search_url(self, search_url: str, search_query_args: URLParams):
		"""Generates a list of articles from a single search term"""
		max_scraped = self.search_query["maximum_scraped"]
		html = await self.get(search_url, params=search_query_args)
		async with html:
			article_paths = set()

			# if "Verifying you are human" in html.select_one("p"):
			# 	raise JournalScrapeError("ACS blocked scraping the results page.", 403, url=search_url, html=html)

			start_page, stop_page, total_articles = await self.get_page_info(html)

			for page_number in range(start_page, stop_page + 1):
				for article in await html.select("div.sr-list.al-article-box.al-normal.clearfix.content-type-journal-articles"):
					search_url = await article.select_one("h4").select_one("a[href]").get("href")
					raw_url = search_url.split('?')[0]

					if raw_url.split("/")[-1] in self.articles_visited:
						# No need to revisit this article
						continue

					if search_url.startswith('/doi/full/') or search_url.startswith('/en/content/articlehtml/') or await self.is_link_to_open_article(article):
						article_paths.add(raw_url)

					if len(article_paths) >= max_scraped:
						return article_paths

				# Get next page at end of loop since page 1 is obtained from the search_url
				await self.turn_page(html, search_url, page_number + 1)
		return article_paths

	async def turn_page(self, html: DynamicHtml, url: str, page_number: int) -> DynamicHtml:
		try:
			for next_page_button in await html.select("button.btn-as-link.sr-nav-next.al-nav-next"):
				if await next_page_button.is_visible():
					await next_page_button.locator.click()
					return html
		except playwright_errors.TimeoutError as e:
			raise JournalScrapeError("Couldn't turn ASC search page.", html=await html.prettify()) from e

	@staticmethod
	def get_license_type(soup: BeautifulSoup):
		unknown_license = (False, "unknown")
		open_access = soup.select_one("li.access__control--item")

		if not open_access:
			return unknown_license

		button = open_access.select_one("img")
		if not button:
			return unknown_license

		button_text = button["alt"]

		match button_text.lower():
			case "open access" | "free to read":
				return (True, button_text)
			case "subscribed" | "token access":
				return (False, button_text)

		return unknown_license

	async def get_license(self, html: DynamicHtml):
		permissions_link = await html.select_one("a#PermissionsLink").get("href")
		param_encoded_doi_regex = DOI_REGEX.replace("/", "%2F")
		doi_match = re.search(rf"https://marketplace.copyright.com/rs-ui-web/(\w{{2}})/search/all/{param_encoded_doi_regex}", permissions_link)

		if doi_match is None:
			self.logger.warning("Could not get the permissions link for ...")
			return (False, "unknown")

		doi = f"{doi_match.group(2)}/{doi_match.group(3)}"

		license_info = (False, "unknown")

		async def predicate(response: Response) -> bool:
			finished = response.request.method == "POST" and response.url == "https://marketplace.copyright.com/rs-ui-web/mp/rest/rights/openAccess"
			if not finished:
				return finished

			content = await response.json()
			info = content["response"]["content"]
			work_id = tuple(info.keys())[0]
			info = info[work_id]

			if info.get("licenseType") is None:
				return finished # There isn't a license, so there's no need to edit the return value

			nonlocal license_info
			license_info = (True, info["url"])

			return finished

		await self.get("https://marketplace.copyright.com/rs-ui-web/mp/search", return_html=False, predicate=predicate, params={
			"type": "all",
			"q": doi
		})
		return license_info

	async def get_title(self, html: DynamicHtml, url: str) -> str:
		elements = await html.select("h1.wi-article-title.article-title-main")
		if len(elements) > 0:
			return (await elements[0].get_text()).strip()

		title = await super().get_title(html, url)
		self.logger.warning(f"Could not find title for {url}.")
		return title

	async def get_authors(self, html: DynamicHtml) -> tuple[str]:
		authors = await html.select("a.linked-name.js-linked-name.stats-author-info-trigger")
		author_list = [await author.get_text() for author in authors]
		return tuple(author_list)

	async def get_figure_list(self, html: DynamicHtml) -> tuple[DynamicHtml]:
		return await html.select("div.fig.fig-section")

	async def get_caption(self, figure_subtree: DynamicHtml) -> str:
		caption_elements = await figure_subtree.select("div.caption.fig-caption > p")
		return "".join([(await caption.get_html()).strip() for caption in caption_elements])

	async def get_figure_url(self, figure: DynamicHtml) -> str:
		return await figure.select_one("img").get("src")


class Nature(JournalFamilyStatic):
	def __init__(self, search_query, **kwargs):
		name_patterns = (
			(re.compile(r"/articles/(s\d{5}-\d{3}-\d{5}-\d)"), 1),
		)

		super().__init__(search_query, name_patterns=name_patterns, **kwargs)
		self._domain = "https://www.nature.com"
		self._search_path = "/search"
		self._page_param = "page="
		self._max_page_size = ""  # not available for nature
		self._order_param = "order"
		self._date_range_param = "date_range"
		self._journal_param = "journal"
		self._author_param = "author="
		# order options
		self._order_values = {"relevant": "relevance", "old": "date_asc", "recent": "date_desc"}
		# codes for journals most relevant to materials science
		self._materials_journals = {
			"",
			"nature",
			"nmat",
			"ncomms",
			"sdata",
			"nnano",
			"natrevmats",
			"am",
			"npj2dmaterials",
			"npjcompumats",
			"npjmatdeg",
			"npjquantmats",
			"commsmat",
		}

		self._join = "\"%20\""  # " "
		self._articles_path = "/articles/"
		self._articles_path_length = 2
		self._prepend = ""
		self._extra_key = " "
		self._max_query_results = 1_000

	def get_search_params(self, terms: tuple[str]) -> dict[str, str]:
		"""Generate the URL parameters for the search in the necessary order"""
		return {
			"q": terms[0],
			"journal": ""
		}

	async def turn_page(self, html: StaticHtml, url: str, page_number: int) -> StaticHtml:
		next_button = html.select_one("li[data-page=next]")
		new_url = await next_button.select_one("a[href]").get("href")
		return await self.get(self.domain + new_url)

	async def get_additional_url_arguments(self, html: StaticHtml):
		current_year = datetime.now().year
		earliest_year = 1845
		non_exhaustive_years = 25
		# If the search is exhaustive, search all 161 nature journals, for all years since 1845, in relevance, oldest, and youngest order.
		if self.order == "exhaustive":
			new_html = await self.get("https://www.nature.com/search/advanced")
			journal_tags = await new_html.select("li[data-action='filter-remove-btn']")
			journal_codes = {(await tag.get_text()).strip() for tag in journal_tags}

			years = [f"{year}-{year}" for year in range(current_year, earliest_year, -1)]
			orderings = set(self.order_values.values())
			await new_html.close()
		# If the search is not exhaustive, search the most relevant materials journals, for the past 25 years, ordered by self.order.
		else:
			journal_codes = self._materials_journals
			years = [f"{year}-{year}" for year in range(current_year - non_exhaustive_years, current_year)]
			orderings = [self.order_values[self.order]]
		years = [""] + years
		# author =
		return years, journal_codes, orderings

	async def get_page_info(self, html: StaticHtml):
		page_re = re.compile(r"\s*page\s*(\d+)\s*")

		async def page_regex(locator: StaticHtml) -> int:
			if not locator:
				raise ValueError("Could not find page numbers.")

			match_ = page_re.search(await locator.get_text())
			if match_ is None:
				raise ValueError("Could not extract page numbers.")

			return int(match_.group(1))

		total_results = html.select_one("span[data-test=results-data]")
		if not total_results:
			if len(await html.select("h1[data-test='no-results']")) == 1:
				return 0, 0, 0

			raise ValueError("No articles were found, try to modify the search criteria")

		results_match = re.search(r"Showing\s*(\d+)–(\d+)\s*of\s*(\d+) results", await total_results.get_text())
		if results_match is None:
			raise ValueError(f"Cannot extract the number of results from the Nature article: `{await html.select_one("title").get_text()}`.")

		total_results = int(results_match.group(3))

		pages = await html.select("li.c-pagination__item")
		if not pages:
			if not total_results:
				with open("/opt/project/error.html", 'w') as f:
					f.write(str(await html.prettify()))
				raise ValueError("Could not find page information.")

			total_pages, current_page = 1, 1
		else:
			total_pages = await html.select("a.c-pagination__link")
			total_pages = await page_regex(total_pages[len(total_pages) - 2])
			current_page = await page_regex(html.select_one(".c-pagination__link.c-pagination__link--active"))

		return current_page, total_pages, total_results

	async def is_link_to_open_article(self, article: StaticHtml) -> bool:
		return len(await article.select("c-meta__item c-meta__item--block-at-lg")) > 0

	async def get_license(self, html: StaticHtml) -> tuple[bool, str]:
		data_layer = html.select_one("script[data-test='dataLayer']")
		data_layer_string = await data_layer.get_text()
		data_layer_json = "{" + data_layer_string.split("[{", 1)[1].split("}];", 1)[0] + "}"
		parsed = json.loads(data_layer_json)

		# try to get whether the journal is open
		_copyright = parsed.get("content", dict()).get("attributes", dict()).get("copyright")
		if _copyright is None:
			return False, "unknown"

		is_open = _copyright.get("open", False)

		# try to get the license
		try:
			_license = _copyright["legacy"]["webtrendsLicenceType"]
		except KeyError:
			_license = "unknown"
		return is_open, _license

	async def get_title(self, html: StaticHtml, url: str) -> str:
		elements = await html.select("h1.c-article-title")
		if len(elements) > 0:
			return await elements[0].get_text()

		title = await super().get_title(html, url)
		self.logger.warning(f"Could not find title for {url}.")
		return title

	async def get_authors(self, html: StaticHtml) -> tuple[str]:
		if isinstance(html, str):
			html = await self.get(html)
			close_html = True
		else:
			close_html = False
		locators = await html.select("a[data-test=\"author-name\"]")

		authors = [None] * len(locators)
		for i, author in enumerate(locators):
			text = await author.get_text()
			authors[i] = text.strip().replace("\n", '')

		if close_html:
			await html.close()
		return tuple(authors)

	async def get_articles_from_search_page(self, html: StaticHtml) -> tuple[StaticHtml]:
		return await html.select("li.app-article-list-row__item")

	async def get_link_for_article(self, article: StaticHtml) -> str:
		return await article.select_one("a.c-card__link.u-link-inherit").get("href")

	async def get_figure_url(self, figure: StaticHtml) -> str:
		image_tag = figure.select_one("img")
		image_url = await image_tag.get("src")
		if image_url is None:
			image_url = await image_tag.get("data-src")
			if image_url is None:
				raise ValueError("No image url found.")
		image_url = image_url.lstrip(r"/")
		return re.sub(r"(.+.com/)lw\d+(/.+)", r"\1full\2", image_url)


class RSC(JournalFamilyDynamic):
	def __init__(self, search_query: dict, **kwargs):
		name_patterns = (
			(re.compile(r"(\w{2})/article/doi/(10\.\d{4,9}/([-._;()/:A-Z0-9]+))/(\d+)/.+", re.I), 3),
			(re.compile(r"(\w{2})/article/(\d+)/(\d+)/(\d+)/(\d+)/(.+)", re.I), 5),
			(re.compile(r"(\w{2})/article/(\d+)?searchresult=1#(\d+)", re.I), 2),
		)
		super().__init__(search_query, name_patterns=name_patterns, **kwargs)
		self._domain = "https://pubs.rsc.org"
		self._relevant = "Relevance"
		self._recent = "Latest%20to%20oldest"
		self._join = '"%20"'
		self._pre_sb = "\"&SortBy"
		self._open_pre_sb = "\"&SortBy"
		self._article_path = ('/en/content/articlehtml/', '')
		self._prepend = "https://pubs.rsc.org"
		self._extra_key = "/image/article"
		self._search_path = "/search-results"
		self._page_param = ""  # pagination through javascript
		self._max_page_size = "PageSize=1000"
		self._order_param = "SortBy"
		self._date_range_param = "DateRange"
		self._journal_param = "Journal"
		# order options
		self._order_values = {
			"relevant": "Relevance",
			"old": "Oldest to latest",
			"recent": "Latest to oldest",
		}
		self._articles_path = "/doi/"

	def get_search_params(self, terms: tuple[str]) -> dict[str, str | bool]:
		"""Generate the URL parameters for the search in the necessary order"""
		params = {
			"q": terms[0].replace(" ", "%20"),
			"hd": "advancedAny",
			"searchType": "advanced",
		}
		if self.open:
			params["access_openaccess"] = True
			params["access_unlocked"] = True
			params["access_free"] = True
		return params

	async def get_additional_url_arguments(self, html: DynamicHtml):
		# rsc allows unlimited results, so no need for additional args
		return [], {}, []

	async def get_page_info(self, html: DynamicHtml):
		try:
			info = html.select_one("div.sr-statistics")
			# total = await info.get_data_value("data-total-item-count")
		except (playwright_errors.TimeoutError, AttributeError) as e:
			raise JournalScrapeError("Could not find total number of articles found for the RSC search.", html=await html.prettify()) from e

		inner_text = await info.get_text()
		match_ = re.search(r"\s*(\d+)-(\d+)\sof\s(\d+)\s*", inner_text)
		if not match_:
			raise JournalScrapeError("Could not find page info for RSC.", html=await html.prettify())

		start_article_num = int(match_.group(1))
		end_article_num = int(match_.group(2))
		total = int(match_.group(3))

		articles_per_page = (1 + end_article_num - start_article_num)
		total_pages = math.ceil(total / articles_per_page)

		return 1, total_pages, total

	async def is_link_to_open_article(self, article: DynamicHtml) -> bool:
		return len(await article.select("i.icon-availability_open")) == 0

	async def get_articles_from_search_page(self, html: DynamicHtml) -> tuple[DynamicHtml]:
		return await html.select("div.sr-list.al-article-box.al-normal.clearfix.content-type-journal-articles")

	async def get_link_for_article(self, article: DynamicHtml) -> str:
		return await article.select_one("a[href]").get("href")

	async def old_get_articles_from_search_url(self, search_url: str, search_query_args: URLParams) -> set:
		"""Generates a list of articles from a single search term"""
		max_scraped = self.search_query["maximum_scraped"]
		html = await self.get(search_url, params=search_query_args)

		async with html:
			try:
				start_page, stop_page, total_articles = await self.get_page_info(html)
			except (AttributeError, playwright_errors.TimeoutError) as e:
				with open(self.results_directory / "new_error.html", 'w') as f:
					f.write(await html.prettify())
				raise JournalScrapeError(str(e), url=search_url, html=html) from e

			article_paths = set()

			for page_number in range(start_page, stop_page + 1):
				articles = await html.select("div.sr-list.al-article-box.al-normal.clearfix.content-type-journal-articles")
				if len(articles) == 0:
					with open(self.results_directory / f"page_{page_number}.html", 'w') as f:
						f.write(await html.prettify())
					continue

				for article in articles:
					tag = article.select_one("a[href]")
					url = await tag.get("href")
					raw_url = url.split("?")[0]
					if raw_url in self.articles_visited:
						# It is an article but we are not interested
						continue

					if not self.open and not (await self.is_link_to_open_article(article)):
						continue

					article_paths.add(raw_url)
					if len(article_paths) >= max_scraped:
						return article_paths

				# Get next page at end of loop since page 1 is obtained from search_url

				if page_number == stop_page:
					return article_paths

				await self.turn_page(html, search_url, page_number+1)
			return article_paths

	async def turn_page(self, html: DynamicHtml, url: str, page_number: int):
		try:
			for next_page_button in await html.select("button.btn-as-link.sr-nav-next.al-nav-next"):
				if await next_page_button.is_visible():
					await next_page_button.locator.click()
					return html
		except playwright_errors.TimeoutError as e:
			raise JournalScrapeError("Couldn't turn RSC search page.", html=await html.prettify()) from e

	async def get_license(self, html: DynamicHtml) -> tuple[bool, str]:
		license_ = await html.select("div.license.license-creative-commons.hide")
		if not license_:
			return False, "unknown"

		return True, await license_[0].select_one("a[href]").get("href")

	async def get_title(self, html: DynamicHtml, url: str) -> str:
		elements = await html.select("h1.wi-article-title.article-title-main")
		if len(elements) > 0:
			return await elements[0].get_text()

		title = await super().get_title(html, url)
		self.logger.warning(f"Could not find title for {url}.")
		return title

	async def get_authors(self, html: DynamicHtml) -> tuple[str]:
		authors = []
		for author in await html.select("div.al-author-name"):
			author = await author.select_one("div.name-role-wrap").get_text()
			author = author.strip().split("\n")[0]
			authors.append(author)

		return tuple(authors)

	async def get_figure_list(self, html: DynamicHtml) -> tuple[DynamicHtml]:
		return await html.select("div.fig.fig-section")

	async def get_caption(self, figure_subtree: DynamicHtml) -> str:
		caption_elements = await figure_subtree.select("div.caption.fig-caption > p")
		return "".join([(await caption.get_html()).strip() for caption in caption_elements])

	async def get_large_figure_url(self, figure: DynamicHtml) -> str:
		locator = figure.locator
		try: # RSC has a "large" image URL, but everytime I tried to go to it, I was stuck in an authentication loop that wouldn't let me see it.
			url = await locator.get_by_text("View large").get_attribute("href")
			if url is None:
				raise playwright_errors.TimeoutError("Couldn't get the large version, going for the original.")
			return self.prepend + url
		except playwright_errors.TimeoutError:
			return await self.get_figure_url(figure)

	async def get_figure_url(self, figure: DynamicHtml) -> str:
		url = await figure.select_one("a.fig-link").get("href")
		if "cdn" in url:
			return url

		return await figure.select_one("img.content-image.lazyLoadInit").get_data_value("src")


class Wiley(JournalFamilyStatic):
	domain = "https://onlinelibrary.wiley.com"
	search_path = "/action/doSearch"
	page_param = "startPage="
	max_page_size = "pageSize=20"
	order_param = "sortBy"
	journal_param = "SeriesKey"
	date_range_param = "AfterYear"
	# order options
	order_values = {"relevant": "relevancy", "recent": "Earliest", "old": ""}
	# join is for terms in search query
	join = '"+"'
	max_query_results = 2000
	articles_path = "/doi/"
	prepend = "https://onlinelibrary.wiley.com"
	extra_key = " "
	articles_path_length = 3

	async def load(self):
		if await super().load():
			return True

		headers, cookies = await self._get_cloudflare_headers()

		self.client.headers.update(headers)
		valid_cookie_domains = {
			".onlinelibrary.wiley.com",
			".scienceconnect.io",
			".wiley.com",
			"onlinelibrary.wiley.com",
			"wiley.scienceconnect.io",
		}
		for cookie in cookies:
			if cookie["domain"] not in valid_cookie_domains:
				continue

			self.client.cookies.set(
				name=cookie["name"],
				value=cookie["value"],
				domain=cookie["domain"],
				path=cookie["path"],
				secure=cookie["secure"],
			)
		self.logger.info(f"Loaded {self.name()}.")
		return False

	async def _get_cloudflare_headers(self, attempts: int = 3) -> tuple[dict[str, str], list[Cookie]]:
		url = self.domain

		async def predicate(resp: Response):
			self.logger.info(f"[{resp.status}] {resp.url=}")
			return resp.url == url and resp.status < 300

		async with Stealth().use_async(async_playwright()) as p:
			browser = await p.chromium.launch()
			page = await browser.new_page()

			for attempt in range(attempts):
				try:
					async with page.expect_response(predicate, timeout=60_000) as resp2:
						await page.goto(url)

					response = await resp2.value
					headers = dict(filter(lambda header: "cf" in header[0].lower(), response.headers.items()))
					cookies = await page.context.cookies()
					return headers, cookies
				except playwright_errors.TimeoutError as e:
					if attempt + 1 == attempts:
						raise
					else:
						self.logger.warning(f"[{attempt+1:,}/{attempts:,}] {url} could not connect within a minute. Trying again.", exc_info=e)

	async def get(self, url: str, params: Optional[dict[str, Any]] = None, *args, **kwargs) -> StaticHtml:
		# await super().get(url, params)
		response = await self.client.get(url, params=params)
		if response.status_code == 403:
			if (ray_header := response.headers.get("Cf-Ray")) is None:
				response.raise_for_status()

			ray_header, _ = ray_header.split("-")
			challenge_response = await self.client.get(f"https://onlinelibrary.wiley.com/cdn-cgi/challenge-platform/h/g/orchestrate/chl_page/v1?ray={ray_header}",
												 headers={"Referer": "https://onlinelibrary.wiley.com/?__cf_chl_rt_tk=dEE_5DgrP1N1taMnWjjwf9j5uKm5JfxRWfnjgj6v_Ws-1786984108-1.0.1.1-CLoH6.aaCeL6K3bvZE2dOxJJEQdA6Qba6mUfWHeVS9c"})
			challenge_response.raise_for_status()

			response = await self.client.get(url, params=params)
			response.raise_for_status()

		return StaticHtml(BeautifulSoup(response.text, "html.parser"))

	def get_search_params(self, terms: tuple[str]) -> dict[str, str | int]:
		"""Generate the URL parameters for the search in the necessary order"""
		params = {}
		for i, term in enumerate(terms, start=1):
			params[f"field{i}"] = "AllField"
			params[f"text{i}"] = term

		params["publication"] = ""
		params["Ppub"] = ""

		if self.open:
			params["ConceptID"] = 15941

		return params

	async def get_additional_url_arguments(self, html: StaticHtml):
		return [""], {""}, [""]

	async def old_get_additional_url_arguments(self, html: StaticHtml):
		current_year = datetime.now().year
		journal_list = html.soup.select_one("#Published in").parent.next_sibling
		journal_link_tags = journal_list.select("a[href]")
		journal_link_tags_exh = journal_list.find_all("option", value=True)

		journal_codes = [jlt.attrs["href"].split("=")[-1] for jlt in journal_link_tags]

		if self.order == "exhaustive":
			num_years = 100
			orderings = list(self.order_values.values())
			journal_codes = journal_codes + [
				jlte.attrs["value"].split("=")[-1] for jlte in journal_link_tags_exh
			]
		else:
			num_years = 25
			orderings = [self.order_values[self.order]]
		# the wiley search engine uses 2 different phrases to delineate
		# start and stop year AfterYear=YYYY&BeforeYear=YYYY
		years = [f"{year}&BeforeYear={year}" for year in range(current_year - num_years, current_year)]

		years = [["", ""]] + years
		return years, journal_codes, orderings

	async def get_page_info(self, html: StaticHtml):
		totalResults = await html.select_one("span.result__count").get_text()
		totalResults = int(totalResults.replace(",", ""))

		articles_per_page = len(await html.select("li.clearfix.separator.search__item.bulkDownloadWrapper"))

		totalPages = math.ceil(float(totalResults / articles_per_page)) - 1
		page = 1
		return page, totalPages, totalResults

	async def is_link_to_open_article(self, article: StaticHtml):
		"""Wiley allows filtering for search. Therefore, if self.open is True, all results will be open."""
		return len(await article.select("div.doi-access")) > 0

	async def turn_page(self, html: StaticHtml, url, page_number: int):
		new_url = f"{url.split('&startPage=')[0]}&startPage={page_number}&pageSize=20"
		return await self.get(new_url)

	async def get_license(self, html: StaticHtml):
		open_access = html.select_one("div.doi-access")
		if open_access and "Open Access" in open_access.text:
			return True, open_access.text
		return False, "unknown"

	async def get_authors(self, html: StaticHtml) -> tuple[str]:
		author_line = html.select_one("div.loa-wrapper.loa-authors.hidden-xs.desktop-authors")
		authors = await author_line.select("p.author-name")

		authors = [await author.get_text() for author in authors]
		return tuple(authors)

	async def get_articles_from_search_page(self, html: StaticHtml) -> tuple[StaticHtml]:
		return await html.select("li.clearfix.separator.search__item.bulkDownloadWrapper")

	async def get_link_for_article(self, article: StaticHtml) -> str:
		return await article.select("a.publication_title.visitable").get("href")

	async def get_figure_list(self, html: StaticHtml):
		figure_subtrees = await html.select("figure.figure")
		return figure_subtrees

	async def get_caption(self, figure_subtree: StaticHtml) -> str:
		caption_elements = await figure_subtree.select("div.figure__caption.figure__caption-text")
		return "".join([(await caption.get_html()).strip() for caption in caption_elements])

	async def get_figure_url(self, figure: StaticHtml) -> str:
		href = await figure.select_one("a[href]").get("href")
		return self.prepend + href


COMPATIBLE_JOURNALS = Literal["ACS", "Nature", "RSC", "Wiley"]
