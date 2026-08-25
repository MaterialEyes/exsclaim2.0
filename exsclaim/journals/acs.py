from .base import JournalFamilyDynamic, DynamicHtml, DOI_REGEX
from ..exceptions import JournalScrapeError

import math
import re

from bs4 import BeautifulSoup
from playwright.async_api import Response
from playwright._impl import _errors as playwright_errors

__all__ = ["ACS"]


class ACS(JournalFamilyDynamic):
	def __init__(self, search_query: dict, **kwargs):
		name_patterns = (
			(re.compile(r"/(\w{6})/article/doi/(10\.\d{4,9})/([-._;()/:A-Z0-9]+)/(\d+)/.+", re.I), 3),
			(re.compile(r"/(\w{6})/article/(\d+)/(\d+)/(\d+)/(\d+)/.+", re.I), 5),
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

		self._extra_key = "inline-fig internalNav"
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
			return (await elements[0].get_surface_text()).strip()

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
		caption_elements = [await caption.get_inner_contents() for caption in caption_elements]
		return "".join([caption.strip() for caption in caption_elements if caption is not None])

	async def get_figure_url(self, figure: DynamicHtml) -> str:
		return await figure.select_one("img").get("src")
