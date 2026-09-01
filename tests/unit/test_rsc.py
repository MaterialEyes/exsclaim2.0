import asyncio
import logging

from exsclaim import RSC, Author
from typing import Any
from unidecode import unidecode # Converts Unicode characters to their closest ASCII equivalent, which helps pass the author even if it's a different character used


class RSCTest(RSC):
	async def save_figure(self, figure_name: str, image_url: str, chunk_size: int = 1_024):
		# Don't want to actually try to download the images because that would point to the actual servers
		return None


async def get_article_information(article: str, http_server: str, search_query: dict[str, Any], logger: logging.Logger) -> dict[str, Any]:
	rsc = RSCTest(search_query, logger=logger)
	url = f"{http_server}/rsc/{article}"

	async with rsc:
		article_json = await rsc.get_article_figures(url, save_html=False)
		return article_json


async def test_article_1(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("d6ma00179c.html", http_server, default_search_query, default_logger)

	title_answer = "Engineered Cu/Cu<sub>2</sub>O–C nanohybrids for superior electrocatalytic performance in direct ethanol fuel cells"
	assert article_json["title"] == title_answer, f"Title is incorrect, {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Gauri S. Mishra"),
		Author(name="Somnath C. Dhawale", orcid="0000-0002-0881-5517"),
		Author(name="Balaji B. Mulik", orcid="0000-0002-3454-6488"),
		Author(name="George Jacob"),
		Author(name="Bhaskar R. Sathe", orcid="0000-0001-8989-0967"),
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 9, f"There should be 9 figures for this article, but {num_articles:,} were found."


async def test_article_2(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("d6ra05923f.html", http_server, default_search_query, default_logger)

	title_answer = "Tuning surface electronic properties of Ni doped Cu<sub>2</sub>O catalyst toward highly selective nitrate-to-ammonia electroreduction"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Thi Kim Cuong Phu", orcid="0000-0002-1987-5451"),
		Author(name="Thanh Ngoc Pham"),
		Author(name="Ngan Nguyen Le", orcid="0000-0001-7717-2538"),
		Author(name="Yoshiyuki Kawazoe", orcid="0000-0002-2369-7045"),
		Author(name="Phi Long Nguyen", orcid="0000-0002-3788-8731"),
		Author(name="Tam Duy Nguyen"),
		Author(name="Thi Viet Bac Phung", orcid="0000-0001-7717-2538"),
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 7, f"There should be 7 figures for this article, but {num_articles:,} were found."


async def test_article_3(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	article_json = await get_article_information("d6ra05522b.html", http_server, default_search_query, default_logger)

	title_answer = "Green hydrogen generation from seawater based on the plasmonic activation induced by Ti<sub>3</sub>C<sub>2</sub> MXene in oxygen-deficient CuO<sub>1−<em>X</em></sub>–poly(<em>N</em>-methylpyrrole) photocathodes"
	assert article_json["title"] == title_answer, f"Title is incorrect: {repr(article_json["title"])}"

	authors = set(map(lambda author: Author(name=unidecode(author.name), orcid=author.orcid), article_json["authors"]))
	known_authors = [
		Author(name="Amira Ben Gouider Trabelsi"),
		Author(name="Fatemah H. Alkallas"),
		Author(name="K. S. Almugren"),
		Author(name="Mohamed Rabia", orcid="0000-0001-6263-0604"),
	]
	for author in known_authors:
		assert author in authors, f"{author} is missing from the article JSON."

	assert article_json["open"], "Article should be open access but isn't recorded as such."

	num_articles = len(article_json["figures"])
	assert num_articles == 7, f"There should be 7 figures for this article, but {num_articles:,} were found."


async def test_search(http_server: str, default_search_query: dict[str, Any], default_logger: logging.Logger):
	rsc = RSCTest(default_search_query, logger=default_logger)
	url = f"{http_server}/rsc/search_page.html"

	async with rsc:
		html = await rsc.get(url)
		start_page, stop_page, total_articles = await rsc.get_page_info(html)
		assert start_page == 1, "The wrong start page was returned."
		assert stop_page == 828, "The wrong stop page was returned."
		assert total_articles == 16_544, "The wrong number of articles was returned."

		articles = await rsc.get_articles_from_search_page(html)
		urls = set()
		for article_num, article in enumerate(articles):
			url = await rsc.get_link_for_article(article)
			raw_url = url.split("?")[0]

			is_open = await rsc.is_link_to_open_article(article)
			if article_num in {2, 3, 5, 8, 10, 11, 12}:
				assert is_open, f"Article number: {article_num} should be open but wasn't."
			else:
				assert not is_open, f"Article number: {article_num} should not be open but was."
			urls.add(raw_url)

	assert len(urls) == 18, "Not all URLs were found."


if __name__ == "__main__":
	asyncio.run(main())
