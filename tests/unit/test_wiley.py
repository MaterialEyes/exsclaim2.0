import logging

from exsclaim import Wiley, Author
from typing import Any
from unidecode import unidecode # Converts Unicode characters to their closest ASCII equivalent, which helps pass the author even if it's a different character used


class WileyTest(Wiley):
	async def save_figure(self, figure_name: str, image_url: str, chunk_size: int = 1_024):
		# Don't want to actually try to download the images because that would point to the actual servers
		return None


async def get_article_information(article: str, http_server: str, search_query: dict[str, Any], logger: logging.Logger) -> dict[str, Any]:
	wiley = WileyTest(search_query, logger=logger)
	url = f"{http_server}/wiley/{article}"

	# async with wiley:
	article_json = await wiley.get_article_figures(url, save_html=False)
	return article_json


async def test_article_1(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("7093071.html", http_server, default_search_query, default_logger)

	title_answer = "XPS and GDOES Characterization of Porous Coating Enriched with Copper and Calcium Obtained on Tantalum via Plasma Electrolytic Oxidation"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Krzysztof Rokosz", orcid="0000-0002-1040-7213"),
		Author(name="Tadeusz Hryniewicz", orcid="0000-0002-6425-7273"),
		Author(name="Patrick Chapon"),
		Author(name="Steinar Raaen"),
		Author(name="Hugo Ricardo Zschommler Sandim"),
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	# FIXME: This article has the subfigures already separated
	# num_articles = len(article_json["figures"])
	# assert num_articles == 9, f"There should be 18 figures for this article, but {num_articles:,} were found."


async def test_article_2(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("304308.html", http_server, default_search_query, default_logger)

	title_answer = "Optical, XPS and XRD Studies of Semiconducting Copper Sulfide Layers on a Polyamide Film"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Valentina Krylova"),
		Author(name="Mindaugas Andrulevicius") # Mindaugas Andrulevičius
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 5, f"There should be 5 figures for this article, but {num_articles:,} were found."


async def test_article_3(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("smll.75324.html", http_server, default_search_query, default_logger)

	title_answer = "Silver-Modulated Copper Dynamics Under Pulsed Tandem Electrochemical CO<sub>2</sub> Reduction"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Blaz Tomc", orcid="0009-0004-5644-3190"), # Blaž Tomc
		Author(name="Rajeena Uruniyengal"),
		Author(name="Matjaz Finsgar", orcid="0000-0002-8302-9284"), # Matjaž Finšgar
		Author(name="Mitja Kostelec"),
		Author(name="Matic Plut"),
		Author(name="Piotr Dobron"), # Piotr Dobroń
		Author(name="Adam Debski"), # Adam Dębski
		Author(name="Agata Radziwonko", orcid="0000-0001-9256-3895"),
		Author(name="Pawel Jozwik"), # Paweł Jóźwik
		Author(name="Marjan Bele"),
		Author(name="Martin Sala", orcid="0000-0001-7845-860X"), # Martin Šala
		Author(name="Mohammed Azeezulla Nazrulla", orcid="0000-0001-7591-7663"),
		Author(name="Malgorzata Norek", orcid="0000-0002-0460-486X"), # Małgorzata Norek
		Author(name="Francisco Ruiz-Zepeda", orcid="0000-0002-2637-3433"),
		Author(name="Ana Rebeka Kamsek", orcid="0009-0008-6247-3256"), # Ana Rebeka Kamšek
		Author(name="Nejc Hodnik", orcid="0000-0002-7113-9769"),
		Author(name="Wojciech J. Stepniowski", orcid="0000-0002-5251-6901"), # Wojciech J. Stępniowski
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 6, f"There should be 6 figures for this article, but {num_articles:,} were found."


async def test_search(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	wiley = WileyTest(default_search_query, logger=default_logger)
	url = f"{http_server}/wiley/search_page.html"

	html = await wiley.get(url)
	start_page, stop_page, total_articles = await wiley.get_page_info(html)
	assert start_page == 1, "The wrong start page was returned."
	assert stop_page == 1_797, "The wrong stop page was returned."
	assert total_articles == 35_960, "The wrong number of articles was returned."

	articles = await wiley.get_articles_from_search_page(html)
	urls = set()
	for article_num, article in enumerate(articles):
		url = await wiley.get_link_for_article(article)
		raw_url = url.split("?")[0]

		is_open = await wiley.is_link_to_open_article(article)
		if article_num in {7, 17}:
			assert is_open, f"Article number: {article_num} should be open but wasn't."
		else:
			assert not is_open, f"Article number: {article_num} should not be open but was."
		urls.add(raw_url)

	assert len(urls) == 20, "Not all URLs were found."
