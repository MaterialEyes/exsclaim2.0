from .base import JournalFamilyStatic, StaticHtml

import json
import re

from datetime import datetime

__all__ = ["Nature"]


class Nature(JournalFamilyStatic):
	def __init__(self, search_query, **kwargs):
		name_patterns = (
			(re.compile(r"/articles/(s\d{5}-\d{3}-\d{5}-\d)"), 1),
		)

		super().__init__(search_query, name_patterns=name_patterns, **kwargs)
		self._domain = "https://www.nature.com"
		self._search_path = "/search"
		self._page_param = "page"
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
		await html.close()
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
			return await elements[0].get_surface_text()

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
