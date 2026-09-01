from .base import JournalFamilyStatic, StaticHtml, default_predicate, DOI_REGEX, Author, ORCID_REGEX
from ..config import settings

import math
import re

from bs4 import BeautifulSoup
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Response
from playwright._impl import _errors as playwright_errors
from playwright_stealth import Stealth
from typing import Any, Optional, Sequence

__all__ = ["Wiley"]


@asynccontextmanager
async def get_temporary_playwright_context():
	async with Stealth().use_async(async_playwright()) as p:
		browser = await p.firefox.launch(headless=settings.PLAYWRIGHT_HEADLESS)
		context = await browser.new_context()
		page = await context.new_page()

		yield context, page

		await page.close()
		await context.close()
		await browser.close()


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
	extra_key = " "

	def __init__(self, search_query: dict, **kwargs):
		name_patterns = (
			(re.compile(fr"/doi/{DOI_REGEX}/(\d+)", re.I), 3),
		)
		super().__init__(search_query, name_patterns=name_patterns, **kwargs)

	async def load(self):
		if await super().load():
			return True

		urls = (
			".onlinelibrary.wiley.com",
			".scienceconnect.io",
			".wiley.com",
			"onlinelibrary.wiley.com",
			"wiley.scienceconnect.io",
		)
		headers, cookies = await self._get_cloudflare_headers(urls=urls)

		self.client.headers.update(headers)
		for cookie in cookies:
			self.client.cookies.set(
				name=cookie["name"],
				value=cookie["value"],
				domain=cookie["domain"],
				path=cookie["path"],
				secure=cookie["secure"],
			)
		self.logger.info(f"Loaded {self.name()}.")
		return False

	async def _get_cloudflare_headers(self, attempts: int = 3, urls: Sequence[str] = tuple()) -> tuple[dict[str, str], list[Cookie]]:
		url = self.domain

		def predicate(resp: Response) -> bool:
			return default_predicate(self.logger, resp, url, "")

		async with get_temporary_playwright_context() as (context, page):
			for attempt in range(attempts):
				try:
					async with page.expect_response(predicate, timeout=60_000) as resp2:
						await page.goto(url)
						try:
							await self.click_on_cloudflare(page)
						except playwright_errors.Error as e:
							self.logger.error("An error occurred while trying to bypass CloudFlare in Wiley.", exc_info=e)

					response = await resp2.value
					headers = dict(filter(lambda header: "cf" in header[0].lower(), response.headers.items()))
					cookies = await context.cookies(urls=urls)
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

		soup = BeautifulSoup(response.text, "html.parser")
		return StaticHtml(soup)

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
		return [], {}, []

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
		await html.close()
		return await self.get(new_url)

	async def get_license(self, html: StaticHtml):
		no_license = (False, "unknown")
		open_access = html.select_one("div.doi-access")

		if not open_access:
			return no_license

		text = (await open_access.get_text()).strip()
		if "Open Access" in text:
			return True, text

		return no_license

	async def get_title(self, html: StaticHtml, url: str) -> str:
		elements = await html.select("h1.citation__title")
		if len(elements) > 0:
			title = await elements[0].get_surface_text(logger=self.logger)
			return title.strip()

		title = await super().get_title(html, url)
		self.logger.warning(f"Could not find title for {url}.")
		return title

	async def get_authors(self, html: StaticHtml) -> tuple[Author]:
		author_line = html.select_one("div.loa-wrapper.loa-authors.hidden-xs.desktop-authors")
		authors = await author_line.select("span.accordion-tabbed__tab-mobile")

		values = [None] * len(authors)
		for i, author in enumerate(authors):
			name = await author.select_one("p.author-name").get_text()
			orcid = None
			for orcid_tag in await author.select("a.sm-account__link[href]"):
				href = await orcid_tag.get("href")
				if href is None:
					continue

				match = ORCID_REGEX.search(href)
				if match is None:
					continue

				orcid = match.group(1)
				break

			values[i] = Author(name=name, orcid=orcid)

		return tuple(values)

	async def get_articles_from_search_page(self, html: StaticHtml) -> tuple[StaticHtml]:
		return await html.select("li.clearfix.separator.search__item.bulkDownloadWrapper")

	async def get_link_for_article(self, article: StaticHtml) -> str:
		return await article.select_one("a.publication_title.visitable").get("href")

	async def get_figure_list(self, html: StaticHtml):
		figure_subtrees = await html.select("figure.figure")
		return figure_subtrees

	async def get_caption(self, figure_subtree: StaticHtml) -> str:
		caption_elements = await figure_subtree.select("div.figure__caption.figure__caption-text")
		return "".join([(await caption.get_inner_contents()).strip() for caption in caption_elements])

	async def get_figure_url(self, figure: StaticHtml) -> str:
		href = await figure.select_one("a[href]").get("href")
		return self.domain + href
