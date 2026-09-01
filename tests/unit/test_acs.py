import logging

from exsclaim import ACS, DynamicHtml, Author
from typing import Any
from unidecode import unidecode # Converts Unicode characters to their closest ASCII equivalent, which helps pass the author even if it's a different character used


class ACSTest(ACS):
	async def save_figure(self, figure_name: str, image_url: str, chunk_size: int = 1_024):
		# Don't want to actually try to download the images because that would point to the actual servers
		return None

	async def get_license(self, html: DynamicHtml): # FIXME
		return (True, "unknown")


async def get_article_information(article: str, http_server: str, search_query: dict[str, Any], logger: logging.Logger) -> dict[str, Any]:
	acs = ACSTest(search_query, logger=logger)
	url = f"{http_server}/acs/{article}"

	async with acs:
		article_json = await acs.get_article_figures(url, save_html=False)
		return article_json


async def test_article_1(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("acs.jpcc.6c03486.html", http_server, default_search_query, default_logger)

	title_answer = "Unveiling the Role of the Central Metal in Electron Delocalization Dynamics at Phthalocyanine/ReS<sub>2</sub> Interfaces Probed by Resonant Photoemission Spectroscopy"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Yunier Garcia-Basabe", orcid="0000-0001-5683-0108"),
		Author(name="Neileth Stand", orcid="0000-0003-2921-2608"),
		Author(name="Jorge Arce-Molina", orcid="0000-0003-3614-8990"),
		Author(name="Flavio C. Vicentin"),
		Author(name="Luiz C. de Carvalho"),
		Author(name="David Steinberg"),
		Author(name="Dunieskys G. Larrude"),
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 9, f"There should be 9 figures for this article, but {num_articles:,} were found."


async def test_article_2(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("jacs.6c12039.html", http_server, default_search_query, default_logger)

	title_answer = "Decoupling CO<sub>2</sub> Availability from Bulk Solubility via Biohybrid Reaction–Diffusion Nanoconfinement"
	assert article_json["title"] == article_json["title"].strip(), "The title still has extra whitespace"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Fhysmelia F. Albuquerque", orcid="0000-0001-8897-187X"), # Fhysmélia F. Albuquerque
		Author(name="Artur C. Souza"),
		Author(name="Matheus S Corsino", orcid="0009-0004-2391-2982"),
		Author(name="Lucas D. Paquini"),
		Author(name="Graziela C. Sedenho", orcid="0000-0001-8696-5978"),
		Author(name="Rafael N. P. Colombo", orcid="0000-0001-8126-4398"),
		Author(name="Fabio H. B. Lima", orcid="0000-0001-5501-2429"),
		Author(name="Frank N. Crespilho", orcid="0000-0003-4830-652X"),
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 5, f"There should be 5 figures for this article, but {num_articles:,} were found."


async def test_article_3(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("5262186.html", http_server, default_search_query, default_logger)

	title_answer = "Different Conditions, Different Composition: Reactive Environment-Induced Surface Composition Dynamics in Pt-Based Bimetallic Alloys"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Jan Kucera"), # Jan Kučera
		Author(name="Athira Lekshmi Mohandas Sandhya"),
		Author(name="Michael Vorochta"),
		Author(name="Iva Matolinova", orcid="0000-0001-6808-7809"), # Iva Matolínová
		Author(name="Ivan Khalakhan", orcid="0000-0003-2929-4148"),
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 4, f"There should be 4 figures for this article, but {num_articles:,} were found."


async def test_search(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	acs = ACSTest(default_search_query, logger=default_logger)
	url = f"{http_server}/acs/search_page.html"

	async with acs:
		html = await acs.get(url)
		start_page, stop_page, total_articles = await acs.get_page_info(html)
		assert start_page == 1, "The wrong start page was returned."
		assert stop_page == 1_592, "The wrong stop page was returned."
		assert total_articles == 31_821, "The wrong number of articles was returned."

		articles = await acs.get_articles_from_search_page(html)
		urls = set()
		for article_num, article in enumerate(articles):
			url = await acs.get_link_for_article(article)
			raw_url = url.split("?")[0]

			is_open = await acs.is_link_to_open_article(article)
			if article_num in {0, 1, 5, 11}:
				assert is_open, f"Article number: {article_num} should be open but wasn't."
			else:
				assert not is_open, f"Article number: {article_num} should not be open but was."
			urls.add(raw_url)

	assert len(urls) == 15, "Not all URLs were found."
