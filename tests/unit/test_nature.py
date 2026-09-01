import asyncio
import logging

from exsclaim import Nature, Author
from typing import Any
from unidecode import unidecode # Converts Unicode characters to their closest ASCII equivalent, which helps pass the author even if it's a different character used


class NatureTest(Nature):
	async def save_figure(self, figure_name: str, image_url: str, chunk_size: int = 1_024):
		# Don't want to actually try to download the images because that would point to the actual servers
		return None


async def get_article_information(article: str, http_server: str, search_query: dict[str, Any], logger: logging.Logger) -> dict[str, Any]:
	nature = NatureTest(search_query, logger=logger)
	url = f"{http_server}/nature/{article}"

	async with nature:
		article_json = await nature.get_article_figures(url, save_html=False)
		return article_json


async def test_article_1(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("s41529-021-00168-3.html", http_server, default_search_query, default_logger)

	title_answer = "Molecular scale insights into interaction mechanisms between organic inhibitor film and copper"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Xiaocui Wu", orcid="0000-0002-4404-9573"),
		Author(name="Frederic Wiame", orcid="0000-0002-1422-6858"), # Frédéric Wiame
		Author(name="Vincent Maurice"),
		Author(name="Philippe Marcus", orcid="0000-0002-9140-0047"),
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 9, f"There should be 9 figures for this article, but {num_articles:,} were found."


async def test_article_2(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("s41467-026-72690-4.html", http_server, default_search_query, default_logger)

	title_answer = "Amide-engineered copper nitride for shortcut-pathway-locked electroreduction of concentrated hydroxymethylfurfural"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Ju Huang"),
		Author(name="Jianqiu Zhu"),
		Author(name="Bowen Liu"),
		Author(name="Chencheng Dai", orcid="0000-0003-4215-0552"),
		Author(name="Zhimin Chen", orcid="0000-0003-3861-3016"),
		Author(name="Hao Wu"),
		Author(name="Gang Li"),
		Author(name="Shichao Du"),
		Author(name="Jian-Qiang Wang", orcid="0000-0003-4123-7592"),
		Author(name="Zhiyu Ren"),
		Author(name="Zhichuan J. Xu", orcid="0000-0001-7746-5920"),
		Author(name="Honggang Fu", orcid="0000-0002-5800-451X"),
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 6, f"There should be 6 figures for this article, but {num_articles:,} were found."


async def test_article_3(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("s41467-025-65314-w.html", http_server, default_search_query, default_logger)

	title_answer = "Direct observation of the on-site oxygen 2<i>p</i> two-hole Coulomb energy in La<sub>2</sub>CuO<sub>4</sub>"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Danilo Kuhn", orcid="0009-0008-4776-4928"), # Danilo Kühn
		Author(name="Swarnshikha Sinha"),
		Author(name="Fredrik O. L. Johansson", orcid="0000-0002-6471-1093"), # Fredrik O. L. Johansson
		Author(name="Katarzyna Siewierska"),
		Author(name="Antonello Tebano"),
		Author(name="Nils Martensson"), # Nils Mårtensson
		Author(name="Andreas Lindblad", orcid="0000-0002-9188-9604"),
		Author(name="Daniele Di Castro"),
		Author(name="Alexander Fohlisch", orcid="0000-0003-4126-8233"), # Alexander Föhlisch
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 4, f"There should be 4 figures for this article, but {num_articles:,} were found."


async def test_search(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	nature = NatureTest(default_search_query, logger=default_logger)
	url = f"{http_server}/nature/search_page.html"

	async with nature:
		html = await nature.get(url)
		start_page, stop_page, total_articles = await nature.get_page_info(html)
		assert start_page == 1, "The wrong start page was returned."
		assert stop_page == 24, "The wrong stop page was returned."
		assert total_articles == 1_190, "The wrong number of articles was returned."

		articles = await nature.get_articles_from_search_page(html)
		urls = set()
		for article_num, article in enumerate(articles):
			url = await nature.get_link_for_article(article)
			raw_url = url.split("?")[0]

			is_open = await nature.is_link_to_open_article(article)
			if article_num == 22:
				assert not is_open, f"Article number: {article_num} should not be open but was."
			else:
				assert is_open, f"Article number: {article_num} should be open but wasn't."
			urls.add(raw_url)

	assert len(urls) == 50, "Not all URLs were found."


if __name__ == "__main__":
	asyncio.run(main())
