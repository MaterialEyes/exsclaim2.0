from .base import JournalFamilyDynamic, DynamicHtml, DOI_REGEX
from ..exceptions import JournalScrapeError

import math
import re

from playwright._impl import _errors as playwright_errors

__all__ = ["RSC"]


class RSC(JournalFamilyDynamic):
	def __init__(self, search_query: dict, **kwargs):
		name_patterns = (
			(re.compile(fr"(\w{2})/article/doi/{DOI_REGEX}/(\d+)/.+", re.I), 3),
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
		self._extra_key = "/image/article"
		self._search_path = "/search-results"
		self._page_param = ""  # pagination through JavaScript
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

	def get_search_params(self, terms: tuple[str]) -> dict[str, str | bool]:
		"""Generate the URL parameters for the search in the necessary order"""
		params = {
			"q": terms[0],
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
		return len(await article.select("i.icon-availability_open")) > 0

	async def get_articles_from_search_page(self, html: DynamicHtml) -> tuple[DynamicHtml]:
		return await html.select("div.sr-list.al-article-box.al-normal.clearfix.content-type-journal-articles")

	async def get_link_for_article(self, article: DynamicHtml) -> str:
		return await article.select_one("a[href]").get("href")

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
			return await elements[0].get_surface_text()

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
		caption_elements = [await caption.get_inner_contents() for caption in caption_elements]
		return "".join([caption.strip() for caption in caption_elements if caption is not None])

	async def get_large_figure_url(self, figure: DynamicHtml) -> str:
		locator = figure.locator
		try: # RSC has a "large" image URL, but everytime I tried to go to it, I was stuck in an authentication loop that wouldn't let me see it.
			url = await locator.get_by_text("View large").get_attribute("href")
			if url is None:
				raise playwright_errors.TimeoutError("Couldn't get the large version, going for the original.")
			return self.domain + url
		except playwright_errors.TimeoutError:
			return await self.get_figure_url(figure)

	async def get_figure_url(self, figure: DynamicHtml) -> str:
		url = await figure.select_one("a.fig-link").get("href")
		if "cdn" in url:
			return url

		return await figure.select_one("img.content-image.lazyLoadInit").get_data_value("src")
