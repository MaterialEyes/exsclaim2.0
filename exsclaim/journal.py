import cv2
import numpy as np
import requests

from .browser import ExsclaimBrowser
from .figures import apply_mask
from .utilities import paths

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup, Tag
from bs4.element import ResultSet
from datetime import datetime
from itertools import product
from json import loads
from logging import getLogger
from math import ceil
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, Browser, Locator
from PIL import Image
from shutil import copyfileobj
from random import randint
from re import compile, search, sub, match
from time import sleep
from typing import Type
from urllib.request import urlretrieve


__all__ = ["JournalFamily", "JournalFamilyDynamic", "ACS", "Nature", "RSC", "Wiley", "journals"]


class JournalFamily(ABC, ExsclaimBrowser):
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
    static html. Nature is an example. These are simpler as GET requests
    alone will return all the relevant data. Dynamic families utilize
    javascript to populate results so a browser emulator like selenium
    is used. RSC is an example of a dynamic journal.
    **Contributing**: If you would like to add a new JournalFamily, decide
    whether a static or dynamic one is needed and look to an existing
    subclass to base your efforts. Create an issue before you start so your
    efforts are not duplicated and submit a PR upon completion. Thanks!
    """

    # journal attributes -- these must be defined for each journal
    # family based on the explanations provided here
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
    def term_param(self) -> str:
        """URL parameter noting search term"""
        return self._term_param

    @property
    def order_param(self) -> str:
        """URL parameter noting results order"""
        return self._order_param

    @property
    def author_param(self) -> str:
        """URL parameter noting results order"""
        return self._author_param

    @property
    def open_param(self) -> str:
        """URL parameter optionally noting open results only"""
        return self._open_param

    @property
    def journal_param(self) -> str:
        """URL parameter noting journal to search"""
        return self._journal_param

    @property
    def date_range_param(self) -> str:
        """URL parameter noting range of dates to search"""
        return self._date_range_param

    @property
    def pub_type(self) -> str:
        """URL parameter noting publication type (specific to Wiley)"""
        return self._pub_type

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
        return self._prepend

    @property
    def extra_key(self) -> str:
        return self._extra_key

    def __init__(self, search_query: dict, **kwargs):
        """creates an instance of a journal family search using a query
        Args:
            search_query: a query json (python dictionary)
        Returns:
            An initialized instance of a search on a journal family
        """
        ExsclaimBrowser.__init__(self, kwargs.get("browser", None))
        self.search_query = search_query
        self.open = search_query.get("open", False)
        self.order = search_query.get("order", "relevant")
        self.logger = kwargs.get("logger", getLogger(__name__))

        # Set up file structure
        base_results_dir = paths.initialize_results_dir(search_query.get("results_dir", None))
        self.results_directory = base_results_dir / self.search_query["name"]
        figures_directory = self.results_directory / "figures"
        figures_directory.mkdir(exist_ok=True)

        # Check if any articles have already been scraped by checking
        # results_dir/_articles
        articles_visited = {}
        articles_file = self.results_directory / "_articles"
        if articles_file.is_file():
            with open(articles_file, "r") as f:
                articles_visited = {a.strip() for a in f.readlines()}
        self.articles_visited = articles_visited

    # Helper Methods for retrieving relevant article URLS

    # @abstractmethod
    def get_page_info(self, page: Page) -> tuple[int, int, int]:
        """Retrieve details on total results from search query
        Args:
            page: a search results page
        Returns:
            (index origin, total page count in search, total results from search)
        """

    # @abstractmethod
    def turn_page(self, url: str, page_number: int) -> str:
        """Return page_number page of search results
        Args:
            url: the url to a search results page
            page_number: page number to search on
        Returns:
            soup of next page
        """
        new_url = f"{url}&{self.page_param}{page_number}"
        return new_url

    # @abstractmethod
    def get_additional_url_arguments(self, page: Page) -> tuple[list[str], set[str], list[str]]:
        """Get lists of additional search url parameters.
        Some JournalFamilies limit the number of articles returned by a single search.
        In order to retrieve articles beyond this, we create additional search
        non-overlapping sets, and execute them individually.
        Args:
            page: initial search result for search term
        Returns:
            (years, journal_codes, orderings): where:
                years is a list of strings of desired date ranges
                journal_codes is a set of strings of desired journal codes
                orderings is a list of strings of desired results ordering
            Each of these should be in order of precedence.
        """
        return [""], {""}, [""]

    # Helper Methods for retrieving figures from articles

    def get_license(self, soup: Page) -> tuple[bool, str]:
        """Checks the article license and whether it is open access
        Args:
            soup: representation of page html
        Returns:
            is_open (a bool): True if article is open
            license (a string): Required text of article license
        """
        return (False, "unknown")

    # @abstractmethod
    def is_link_to_open_article(self, tag: Locator) -> bool:
        """Checks if link is to an open access article
        Args:
            tag (bs4.tag): A tag containing an href attribute that
                links to an article
        Returns:
            True if the article is confirmed open_access
        """
        return self.open

    # @abstractmethod
    def get_figure_subtrees(self, soup: BeautifulSoup) -> list:
        """Retrieves list of bs4 parse subtrees containing figure elements
        Args:
            soup: A beautifulsoup parse tree
        Returns:
            A list of all figures in the article as BeautifulSoup objects
        """
        # figure_list = [
        #     a for a in soup.find_all("figure") if self.extra_key in str(a)
        # ]
        return filter(lambda a: self.extra_key in str(a), soup.find_all("figure"))

    def get_figure_list(self, url:str) -> list[BeautifulSoup]:
        """
        Returns list of figures in the given url
        Args:
            url: a string, the url to be searched
        Returns:
            A list of all figures in the article as BeautifulSoup Tag objects
        """
        def get_figure_list_from_playwright(page:Page, **kwargs):
            # options.add_argument("--disable-dev-shm-usage") # overcome limited resource problems
            # options.binary_location = "/gpfs/fs1/home/avriza/chrome/opt/google/chrome/google-chrome"
            # driver = webdriver.Chrome(service=Service('/gpfs/fs1/home/avriza/chromedriver'), options=options)
            #
            # stealth(driver,
            #       languages=["en-US", "en"],
            #       vendor="Google Inc.",
            #       platform="Win32",
            #       webgl_vendor="Intel Inc.",
            #       renderer="Intel Iris OpenGL Engine",
            #       fix_hairline=True,
            #       )
            page.goto(url)
            figures = [a for a in page.locator("figure").all() if self.extra_key in str(a)]
            return [BeautifulSoup(figure.inner_html(), "html.parser") for figure in figures]

        return self.temporary_browser(get_figure_list_from_playwright) # div.c-article-section__figure-description

    def get_soup_from_request(self, url: str) -> BeautifulSoup:
        """Get a BeautifulSoup parse tree (lxml parser) from a url request
        Args:
            url: A requested url
        Returns:
            A BeautifulSoup parse tree.
        """
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:82.0) Gecko/20100101 Firefox/82.0"
        }
        wait_time = float(randint(0, 50))
        sleep(wait_time / float(10))
        with requests.Session() as session:
            r = session.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "lxml")
        return soup

    # @abstractmethod
    def find_captions(self, figure_subtree: BeautifulSoup) -> ResultSet:
        """
        Returns all captions associated with a given figure
        Args:
            figure_subtree: an bs4 parse tree
        Returns:
            all captions for given figure
        """
        return figure_subtree.find_all("p")

    def save_figure(self, figure_name: str, image_url: str):
        """
        Saves figure at img_url to local machine
        Args:
            figure_name: name of figure
            image_url: url to image
        """
        figures_directory = self.results_directory / "figures"
        response = requests.get(image_url, stream=True)
        figure_path = figures_directory / figure_name
        with open(figure_path, "wb") as out_file:
            copyfileobj(response.raw, out_file)
        del response

    # @abstractmethod
    def get_figure_url(self, figure_subtree: BeautifulSoup) -> str:
        """Returns url of figure from figure's html subtree
        Args:
            figure_subtree (bs4): subtree containing an article figure
        Returns:
            url (str)
        """
        image_tag = figure_subtree.find("img")
        image_url = image_tag.get("src")
        if image_url is None:
            image_url = image_tag.get("data-src")
            if image_url is None:
                raise ValueError("No image url found.")
        image_url = image_url.lstrip("//")
        # Replaces a part of the URL that sets the image as a certain size to its full size
        return sub(r"(.+.com/)lw\d+(/.+)", r"\1full\2", image_url)

    def get_search_query_urls(self) -> list[str]:
        """Create list of search query urls based on input query json

        Returns:
            A list of urls (as strings)
        """
        def get_search_query_urls_from_playwright(page:Page, **kwargs):
            search_query = self.search_query
            # creates a list of search terms
            try:
                search_list = [
                    [search_query["query"][key]["term"]]
                    + search_query["query"][key].get("synonyms", [])
                    for key in search_query["query"]
                ]
            except TypeError as e:
                print(f"{search_query=}")
                raise e
            # print('search list',search_list)
            search_product = list(product(*search_list))
            # print("search_product",search_product)

            search_urls = []
            for term in search_product:
                url_parameters = "&".join(
                    [self.term_param + self.join.join(term), self.max_page_size]
                )
                search_url = self.domain + self.search_path + self.pub_type + url_parameters
                if self.open:
                    search_url += "&" + self.open_param + "&"

                # print('search_url', search_url)

                page.goto(search_url)
                sleep(float(randint(0, 50)) / 10)

                years, journal_codes, orderings = self.get_additional_url_arguments(page)
                search_url_args = []

                for year_value in years:
                    year_param = self.date_range_param + year_value
                    for journal_value in journal_codes:
                        for order_value in orderings:
                            args = "&".join(
                                [
                                    year_param,
                                    self.journal_param + journal_value,
                                    self.order_param + order_value,
                                    ]
                            )
                            search_url_args.append(args)
                search_term_urls = [search_url + url_args for url_args in search_url_args]
                search_urls += search_term_urls
                # search_urls += 'https://www.nature.com/search?q=electrochromic%20polymer&date_range=&journal=&order=relevance&author=reynolds'
            # print('search url', search_urls)
            # TODO: URL Encode the search query urls
            return list(map(lambda url: url.replace(" ", "%20"), search_urls))
        return self.temporary_browser(get_search_query_urls_from_playwright)

    def get_articles_from_search_url(self, search_url: str) -> set:
        """Generates a list of articles from a single search term"""
        max_scraped = self.search_query["maximum_scraped"]
        self.logger.info(f"GET request: {search_url}")

        def get_articles_search_url_from_playwright(page:Page, **kwargs):
            search_url = kwargs["search_url"]
            page.goto(search_url)
            wait_time = randint(0, 50)
            sleep(wait_time / 10.0)

            article_paths = set()

            try:
                start_page, stop_page, total_articles = self.get_page_info(page)
            except ValueError as e:
                if page.locator("h1[data-test='no-results']").count() == 1:
                    # No results were found
                    return article_paths
                raise e

            # raise NameError("journal family {0} is not defined")
            for page_number in range(start_page, stop_page + 1): # TODO: Convert all of the soups to Playwright locators

                # print(soup.find_all("a", href=True))
                with open("test.html", "w") as f:
                    f.write(page.locator("html").inner_html())
                for article in page.locator("article.u-full-height.c-card.c-card--flush").all():
                    tag = article.locator("a[href]")
                    url = tag.get_attribute("href").split('?page=search')[0]

                    # self.logger.debug("Candidate Article: {}".format(url))
                    # if (
                    #    self.articles_path not in url
                    #    or url.count("/") != self.articles_path_length
                    # ):
                    #    # The url does not point to an article
                    #    continue
                    if url.split("/")[-1] in self.articles_visited or (
                            self.open and not self.is_link_to_open_article(tag)
                    ):
                        # It is an article but we are not interested
                        continue
                    # self.logger.debug("Candidate Article: PASS")
                    article_paths.add(url)
                    if len(article_paths) >= max_scraped:
                        return article_paths
                # Get next page at end of loop since page 1 is obtained from
                # search_url
                search_url = self.turn_page(search_url, page_number + 1)
                # print('new search url', search_url)
            # print(article_paths)
            return article_paths

        return self.temporary_browser(get_articles_search_url_from_playwright, search_url=search_url)

    def get_article_extensions(self) -> tuple:
        """Retrieves a list of article url paths from a search query"""
        # This returns urls based on the combinations of desired search terms.
        search_query_urls = self.get_search_query_urls()
        article_paths = set()
        for search_url in search_query_urls:
            new_article_paths = self.get_articles_from_search_url(search_url)
            article_paths |= new_article_paths
            if len(article_paths) >= self.search_query["maximum_scraped"]:
                break
        return tuple(article_paths)

    @staticmethod
    def _get_figure_name(article_name:str, figure_idx:int) -> str:
        return f"{article_name}_fig{figure_idx}.jpg"

    def get_figures(self, figure_idx:int, figure, figure_json:dict, url:str) -> tuple[dict, str]:
        try:
            image_url = self.prepend + self.get_figure_url(figure)  # .replace('_hi-res','')
        except ValueError as e:
            error_dir = self.results_directory / "html" / "errors"
            error_dir.mkdir(exist_ok=True, parents=True)
            with open(error_dir / f"{url}_{figure_idx}.html", "w") as f:
                f.write(f"<!--No image url found-->\n{figure_subtree}")
            raise e

        if not match("https?://.+", image_url):
            image_url = "https://" + image_url

        article_name = url.split("/")[-1].split("?")[0]

        # initialize the figure's json
        figure_json |= {
            "article_name": article_name,
            "caption_delimiter": "",
            "master_images": [],
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
        return figure_json, image_url

    def get_article_figures(self, url: str) -> dict:
        """Get all figures from an article
        Args:
            url: A url to a journal article
        Returns:
            A dict of figure_jsons from an article
        """
        def get_article_figures_from_playwright(page:Page, **kwargs) -> tuple[bool, str, str]:
            page.goto(url)
            wait_time = float(randint(0, 50))
            sleep(wait_time / float(10))

            is_open, _license = self.get_license(page)

            # Uncomment to save html
            html_directory = self.results_directory / "html"
            html_directory.mkdir(exist_ok=True)
            with open(html_directory / (url.split("/")[-1] + ".html"), "w", encoding="utf-8") as file:
                file.write(page.locator("html").inner_html())
            return is_open, _license, page.title()

        is_open, _license, title = self.temporary_browser(get_article_figures_from_playwright)
        figure_subtrees = self.get_figure_list(url)

        self.logger.info(f"Number of subfigures: {len(figure_subtrees):,}.")
        article_json = {}

        for figure_number, figure_subtree in enumerate(figure_subtrees, start=1):
            captions = self.find_captions(figure_subtree)

            # acs captions are duplicated, one version with no captions
            if len(captions) == 0:
                continue

            # get figure caption
            figure_caption = ""
            for caption in captions:
                figure_caption += caption.get_text()

            figure_json = {
                "title": title,
                "article_url": url,
                "license": _license,
                "open": is_open,
                "full_caption": figure_caption,
            }

            try:
                figure_json, image_url = self.get_figures(figure_number, figure_subtree, figure_json, url)
            except ValueError as e:
                self.logger.exception(e)
            # figure_name = self._get_figure_name(figure_json["article_name"], figure_subtree)
            figure_name = self._get_figure_name(figure_json["article_name"], figure_number)

            figure_path = Path(self.search_query["name"]) / "figures" / figure_name
            figure_json |= {
                "image_url": image_url,
                "figure_name": figure_name,
                "figure_path": str(figure_path),
            }

            article_json[figure_name] = figure_json

            # save figure as image
            self.save_figure(figure_name, image_url)

            # increment index
        return article_json


class JournalFamilyDynamic(JournalFamily):
    def __init__(self, search_query: dict, **kwargs):
        """creates an instance of a journal family search using a query
        Args:
            search_query: a query json (python dictionary)
        """
        super().__init__(search_query, **kwargs)

    def get_figures(self, figure_idx:int, figure, figure_json:dict, url:str) -> tuple[dict, str]:
        article_name = url.split("/")[-1]

        # get figure url and name
        if 'rsc' in url.split("."):
            # for image_tag in figure.find_all("a", href=True):
            # for image_tag in [a for a in figure.find_all("a", href=True) if str(a).find(self.extra_key) > -1]:
            for image_tag in filter(lambda a: self.extra_key in str(a), figure.find_all("a", href=True)):
                image_url = image_tag['href']
        else:
            image_tag = figure.find('img')
            image_url = image_tag.get('src')

        image_url = self.prepend + image_url.replace('_hi-res', '')
        if ":" not in image_url:
            image_url = "https:" + image_url

        print(f"{image_url=}")

        figure_json |= {
            "article_name": article_name,
            "image_url": image_url,
            "caption_delimiter": "",
            "master_images": [],
            "unassigned": {
                'master_images': [],
                'dependent_images': [],
                'inset_images': [],
                'subfigure_labels': [],
                'scale_bar_labels': [],
                'scale_bar_lines': [],
                'captions': []
            }
        }

        # add all results
        return figure_json, image_url

# ############# JOURNAL FAMILY SPECIFIC INFORMATION ################
# To add a new journal family, create a new subclass of JournalFamily.
# Fill out the methods and attributes according to their descriptions in the JournalFamily class.
# Then add an entry to the journals dictionary with the journal family's name in all lowercase as the key and
# the new class as the value.
# ##################################################################


# FIXME: ACS Can tell that Playwright is a bot and is giving 403 Unauthorized
class ACS(JournalFamilyDynamic):
    def __init__(self, search_query: dict, **kwargs):
        super().__init__(search_query, **kwargs)
        self._domain = "https://pubs.acs.org"
        self._search_path = "/action/doSearch?"
        self._term_param = "AllField="
        self._max_page_size = "pageSize=100"
        self._page_param = "startPage="
        self._order_param = "sortBy="
        self._open_param = "openAccess=18&accessType=openAccess"
        self._journal_param = "SeriesKey="
        self._date_range_param = "Earliest="
        self._pub_type = ""

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

    def get_page_info(self, page:Page):
        total_results = int(page.locator("span.result__count").inner_text())
        total_results = min(total_results, 2020)

        page_counter = page.locator(".pagination")
        page_counter_list = [page_number.text.strip() for page_number in page_counter.locator("li").all_inner_texts()]

        current_page = int(page_counter_list[0])
        total_pages = total_results // 20
        return current_page, total_pages, total_results

    def get_articles_from_search_url(self, url:str):
        """Generates a list of articles from a single search term"""
        max_scraped = self.search_query["maximum_scraped"]
        self.logger.info(f"GET request: {url}")

        def get_articles_from_playwright(page:Page, url:str, **kwargs):
            article_paths = set()
            page.goto(url)

            start_page, stop_page, total_articles = self.get_page_info(page)

            for page_number in range(start_page, stop_page + 1):
                for locator in page.locator("a[href]").all():
                    url = locator.get_attribute['href']
                    url = url.split('?page=search')[0]

                    if url.split("/")[-1] in self.articles_visited:
                        # It is an article but we are not interested
                        continue

                    # self.logger.debug("Candidate Article: PASS")
                    if url.startswith('/doi/full/') or url.startswith('/en/content/articlehtml/'):
                        article_paths.add(url)

                    if len(article_paths) >= max_scraped:
                        return article_paths

                # Get next page at end of loop since page 1 is obtained from the search_url
                page.goto(self.turn_page(url, page_number + 1))
            return article_paths
        return self.temporary_browser(get_articles_from_playwright, url=url)

    def get_article_figures(self, url):
        """
        Get all figures from an article 
        Args:
            url: A url to a journal article
        Returns:
            A dict of figure_jsons from an article
        """
        def get_article_figures_from_playwright(page:Page, **kwargs):
            # options.add_argument("--disable-dev-shm-usage") #overcome limited resource problems
            # options.binary_location = "/gpfs/fs1/home/avriza/chrome/opt/google/chrome/google-chrome"
            # driver = webdriver.Chrome(service=Service('/gpfs/fs1/home/avriza/chromedriver'), options=options)
            #
            # stealth(driver,
            #       languages=["en-US", "en"],
            #       vendor="Google Inc.",
            #       platform="Win32",
            #       webgl_vendor="Intel Inc.",
            #       renderer="Intel Iris OpenGL Engine",
            #       fix_hairline=True,
            #       )
            page.goto(url)
            is_open, _license = self.get_license(page)

            html_directory = self.results_directory / "html"
            html_directory.mkdir(exist_ok=True)

            with open(html_directory / (url.split("/")[-1]+'.html'), "w", encoding='utf-8') as file:
                file.write(page.locator("html").inner_html())

            figure_list = page.locator("figure") # self.get_figure_list(url) #
            captions = []

            # TODO: Is this block needed since the captions variable is immediately overwritten after this
            for figure_locator in figure_list.all():
                figcaption = figure_locator.locator('figcaption')
                if figcaption.count() > 0:
                    captions.append(figcaption.nth(0).inner_text().strip())

            # Print the captions
            for caption in captions:
                print(caption)

            article_json = {}

            # for figure in soup.find_all('figure'):
            for figures, figure in enumerate(figure_list.all(), start=1):
                print(f"Figure: {figure}")

                captions = figure.locator("figcaption").all()
                # acs captions are duplicated, one version with no captions
                if len(captions) == 0:
                    continue

                print(f"Captions: {captions}")
                figure_caption = ""
                for caption in captions:
                    if caption is not None:
                        figure_caption += caption.inner_text()

                print(f"Figure caption: {figure_caption}")

                # initialize the figure's json
                article_name = url.split("/")[-1]
                # TODO: Is this supposed to be the figure's caption or the article's title, because the soup object would only contain the <figure>...</figure> space.
                figure_json = {"title": "", # soup.find('title').get_text(),
                               "article_url": url,
                               "article_name": article_name,
                               "full_caption": figure_caption,
                               "caption_delimiter": ""}

                # get figure url and name
                if 'rsc' in url.split("."):
                    # for image_tag in figure.find_all("a", href=True):
                    for image_tag in [a for a in figure.locator("a[href]").all() if self.extra_key in str(a)]:
                        image_url = image_tag["href"]
                else:
                    image_tag = figure.locator("img")
                    image_url = image_tag.locator("src").first.inner_text()

                image_url = self.prepend + image_url.replace('_hi-res','')
                if ":" not in image_url:
                    image_url = "https:" + image_url

                figure_name = f"{article_name}_fig{figures}.jpg"  # " +  image_url.split('.')[-1]
                # print('fig_name',figure_name)
                # print('im_url',image_url)
                # save image info
                figure_json |= {"figure_name": figure_name,
                                "image_url": image_url,
                                "license": _license,
                                "open": is_open
                                }

                # save figure as image
                # self.save_figure(figure_name, image_url)
                figures_directory = self.results_directory / "figures"
                print('figures_directory', figures_directory)

                out_file = figures_directory / figure_name
                print('out_file', out_file)

                print('image_url', image_url)
                page.goto(image_url)
                page.screenshot(path=out_file)

                figure_path = Path(self.search_query["name"]) / "figures" / figure_name
                apply_mask(figure_path)

                figure_json |= {
                   "figure_path": str(figure_path),
                   "master_images": [],
                   "unassigned": {
                        'master_images': [],
                        'dependent_images': [],
                        'inset_images': [],
                        'subfigure_labels': [],
                        'scale_bar_labels':[],
                        'scale_bar_lines': [],
                        'captions': []
                    }
                }

                # add all results
                article_json[figure_name] = figure_json
                # increment index
                # Open a file with write binary mode, and write to it
                figures_directory = self.results_directory / "figures"
                figure_path = figures_directory / figure_name
            return article_json

        return self.temporary_browser(get_article_figures_from_playwright)

    def get_additional_url_arguments(self, page:Page):
        # rsc allows unlimited results, so no need for additional args # TODO: Check if ACS has unlimited results
        return super().get_additional_url_arguments(page)

    def get_license(self, soup):
        if isinstance(soup, BeautifulSoup):
            open_access = soup.find("div", {"class": "article_header-open-access"})
            if open_access:
                match open_access.text.lower():
                    case "acs authorchoice" | "acs editors' choice":
                        return (True, open_access.text)
        elif isinstance(soup, Page):
            open_access = soup.locator("div.article_header-open-access")
            if open_access.count() > 0:
                match open_access.inner_text().lower():
                    case "acs authorchoice" | "acs editors' choice":
                        return (True, open_access.text)
        return (False, "unknown")

    def is_link_to_open_article(self, tag):
        # ACS allows filtering for search. Therefore, if self.open is True, all results will be open.
        return super().is_link_to_open_article(tag)

    def turn_page(self, url, pg_num):
        return f"{url.split('&startPage=')[0]}&startPage={pg_num}&pageSize=20"


class Nature(JournalFamily):
    def __init__(self, results_directory, **kwargs):
        super().__init__(results_directory, **kwargs)
        self._domain = "https://www.nature.com"
        self._search_path = "/search?"
        self._page_param = "page="
        self._max_page_size = ""  # not available for nature
        self._term_param = "q="
        self._order_param = "order="
        self._open_param = ""
        self._date_range_param = "date_range="
        self._journal_param = "journal="
        self._pub_type = ""
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

    def get_page_info(self, page:Page):
        page_re = compile(r"page\n(\d+)")

        def page_regex(locator:Locator) -> int:
            if locator.count() == 0:
                raise ValueError("Could not find page numbers.")

            match = page_re.search(locator.inner_text())
            if match is None:
                raise ValueError("Could not extract page numbers.")

            return int(match.group(1))

        total_results = page.locator("span[data-test=results-data]")
        if total_results.count() == 0:
            if page.locator("h1[data-test='no-results']").count() == 1:
                return 0, 0, 0
            raise ValueError("No articles were found, try to modify the search criteria")

        match = search(r"Showing (\d+)–(\d+) of\s*(\d+) results", total_results.inner_text())
        if match is None:
            raise ValueError("Cannot extract the number of results from the Nature article.")
        total_results = int(match.group(3))

        pages = page.locator("li.c-pagination__item")
        if pages.count() == 0:
            if not total_results:
                with open("/opt/project/error.html", 'w') as f:
                    f.write(page.locator("html").inner_html())
                raise ValueError("Could not find page information.")
            total_pages, current_page = 1, 1
        else:
            total_pages = page.locator("a.c-pagination__link")
            total_pages = page_regex(total_pages.nth(total_pages.count() - 2))

            current_page = page_regex(page.locator(".c-pagination__link.c-pagination__link--active"))

        return current_page, total_pages, total_results

    def get_additional_url_arguments(self, page:Page):
        current_year = datetime.now().year
        earliest_year = 1845
        non_exhaustive_years = 25
        # If the search is exhaustive, search all 161 nature journals, for all years since 1845, in relevance, oldest, and youngest order.
        if self.order == "exhaustive":
            page.goto("https://www.nature.com/search/advanced")
            journal_tags = page.locator("li[data-action='filter-remove-btn']")

            journal_codes = {tag.inner_text.strip() for tag in journal_tags.all()}
            years = [f"{year}-{year}" for year in range(current_year, earliest_year, -1)]
            orderings = set(self.order_values.values())
        # If the search is not exhaustive, search the most relevant materials journals, for the past 25 years, in self.order order.
        else:
            journal_codes = self._materials_journals
            years = [f"{year}-{year}" for year in range(current_year - non_exhaustive_years, current_year)]
            orderings = [self.order_values[self.order]]
        years = [""] + years
        # author =
        return years, journal_codes, orderings

    def get_license(self, page:Page) -> tuple[bool, str]:
        data_layer_string = page.locator("script[data-test='dataLayer']").inner_text()

        data_layer_json = (
            "{" + data_layer_string.split("[{", 1)[1].split("}];", 1)[0] + "}"
        )
        parsed = loads(data_layer_json)
        # try to get whether the journal is open
        try:
            _copyright = parsed["content"]["attributes"]["copyright"]
        except KeyError:
            return False, "unknown"

        if _copyright is None:
            return False, "unknown"

        is_open = _copyright.get("open", False)

        # try to get the license
        try:
            _license = _copyright["legacy"]["webtrendsLicenceType"]
        except KeyError:
            _license = "unknown"
        return is_open, _license

    def is_link_to_open_article(self, locator:Locator) -> bool:
        locator.click(force=True)

        url = locator.page.url
        if not url.startswith(self.domain):
            print(f"The link led to a website outside of {self.domain}, so there is no way to know if it is open access or not: {url}.")
            return False

        return self.get_license(locator.page)[0]


class RSC(JournalFamilyDynamic):
    def __init__(self, search_query:dict, **kwargs):
        super().__init__(search_query, **kwargs)
        self._domain = "https://pubs.rsc.org"
        # term_param = "AllField="
        self._relevant = "Relevance"
        self._recent = "Latest%20to%20oldest"
        self._path = "/en/results?searchtext="
        self._join = "\"%20\""
        self._pre_sb = "\"&SortBy="
        self._open_pre_sb = "\"&SortBy="
        self._post_sb = "&PageSize=1&tab=all&fcategory=all&filter=all&Article%20Access=Open+Access"
        self._article_path = ('/en/content/articlehtml/', '')
        self._prepend = "https://pubs.rsc.org"
        self._extra_key = "/image/article"
        self._search_path = "/en/results?"
        self._page_param = ""  # pagination through javascript
        self._max_page_size = "PageSize=1000"
        self._term_param = "searchtext="
        self._order_param = "SortBy="
        self._open_param = "ArticleAccess=Open+Access"
        self._date_range_param = "DateRange="
        self._journal_param = "Journal="
        self._pub_type = ""
        # order options
        self._order_values = {
            "relevant": "Relevance",
            "old": "Oldest to latest",
            "recent": "Latest to oldest",
        }
        self._articles_path = "/doi/"

    def get_page_info(self, page):
        info = page.locator("div.fixpadv--l.pos--left.pagination-summary").first
        match = search(r"(\d+) results - Showing page (\d+) of (\d+)", info.inner_text())
        return int(match.group(2)), int(match.group(3)), int(match.group(1))

    def get_articles_from_search_url(self, search_url: str) -> set:
        """Generates a list of articles from a single search term"""
        def get_articles_from_playwright(page:Page, **kwargs):
            max_scraped = self.search_query["maximum_scraped"]
            # self.logger.info("GET request: {}".format(search_url))
            page.goto(search_url)

            wait_time = float(randint(0, 50))
            sleep(wait_time / float(10))
            start_page, stop_page, total_articles = self.get_page_info(page)

            # print('search url', search_url)
            article_paths = set()

            for page_number in range(start_page, stop_page + 1):
                # print(soup.find_all("a", href=True))
                for tag in page.locator("a[href]").all():
                    url = tag.get_attribute("href").split('?page=search')[0]
                    if url.split("/")[-1] in self.articles_visited:
                        # It is an article but we are not interested
                        continue
                    # self.logger.debug("Candidate Article: PASS")

                    if url.startswith('/doi/full/') or url.startswith('/en/content/articlehtml/'):
                        article_paths.add(url)

                    if len(article_paths) >= max_scraped:
                        return article_paths

                # Get next page at end of loop since page 1 is obtained from search_url
                # search_url = self.turn_page(search_url, page_number + 1)
                # try:
                page.locator(".paging__btn.paging__btn--next").first.click(force=True)
            return article_paths
        return self.temporary_browser(get_articles_from_playwright)

    def turn_page(self, url, pg_size):
        return f"{url.split('1&tab=all')[0]}{pg_size}&tab=all&fcategory=all&filter=all&Article%20Access=Open+Access"

    def get_figure_list(self, url:str):
        def get_figure_list_from_playwright(page:Page, **kwargs):
            page.goto(url)
            return [BeautifulSoup(fig.inner_html(), "html.parser") for fig in page.locator("figure.img-tbl__image").all()]

        return self.temporary_browser(get_figure_list_from_playwright)

    def find_captions(self, figure:BeautifulSoup):
        return figure.find_all("figcaption")

    def save_figure(self, figure_name, image_url):
        out_file = self.results_directory / "figures" / figure_name
        urlretrieve(image_url, out_file)

    def get_additional_url_arguments(self, page):
        # rsc allows unlimited results, so no need for additional args
        return super().get_additional_url_arguments(page)

    def get_figure_subtrees(self, soup):
        figure_subtrees = soup.find_all("div", "image_table")
        return figure_subtrees

    def get_figure_url(self, figure_subtree):
        return self.prepend + figure_subtree.find("a", href=True)["href"]

    def get_article_figures(self, url: str) -> dict:
        """
        Get all figures from an article 
        Args:
            url: A url to a journal article
        Returns:
            A dict of figure_jsons from an article
        """
        def get_article_figures_from_playwright(page:Page, **kwargs) -> tuple[bool, str, str]:
            page.goto(url)
            is_open, _license = self.get_license(soup)

            html_directory = self.results_directory / "html"
            html_directory.mkdir(exist_ok=True)

            with open(html_directory / (url.split("/")[-1]+'.html'), "w", encoding='utf-8') as file:
                file.write(page.locator("html").inner_html())
            title = page.locator("title").inner_text().strip()
            return is_open, _license, title

        is_open, _license, title = self.temporary_browser(get_article_figures_from_playwright)
        figure_list:list[BeautifulSoup] = self.get_figure_list(url)
        article_json = {}

        # for figure in soup.find_all('figure'):
        for figures, figure in enumerate(figure_list, start=1):
            captions = self.find_captions(figure)

            # acs captions are duplicated, one version with no captions
            if len(captions) == 0:
                continue

            # initialize the figure's json
            article_name = url.split("/")[-1]
            figure_json = {"title": title,
                           "article_url": url,
                           "article_name": article_name,
                           "caption_delimiter": "", # Allocate entry for caption delimiter
                           # get figure caption
                           "full_caption": "".join(map(lambda caption: caption.get_text(), captions)),
                           "license": _license,
                           "open": is_open
                           }

            try:
                image_url = figure.find('a')['href']
            except:
                img_tags = figure.find('img')['data-original']
                image_url = self.prepend + img_tags

            if ":" not in image_url:
                image_url = self.prepend + image_url

            figure_name = f"{article_name}_fig{figures.jpg}"  # " +  image_url.split('.')[-1]
            print(f"{figure_name=}")
            print(f"{image_url=}")
            # save image info
            figure_json |= {"figure_name": figure_name,
                            "image_url": image_url}

            # save figure as image
            self.save_figure(figure_name, image_url)
            figure_path = Path(self.search_query["name"]) / "figures" / figure_name

            figure_json |= {"figure_path": str(figure_path),
                            "master_images": [],
                            "unassigned": {
                                'master_images': [],
                                'dependent_images': [],
                                'inset_images': [],
                                'subfigure_labels': [],
                                'scale_bar_labels': [],
                                'scale_bar_lines': [],
                                'captions': []
                            }
                            }
            # add all results
            article_json[figure_name] = figure_json
            # increment index
        return article_json


class Wiley(JournalFamily):
    domain = "https://onlinelibrary.wiley.com"
    search_path = "/action/doSearch?"
    page_param = "startPage="
    max_page_size = "pageSize=20"
    term_param = "AllField="
    order_param = "sortBy="
    open_param = "ConceptID=15941"
    journal_param = "SeriesKey="
    date_range_param = "AfterYear="
    pub_type = "PubType=journal"  # Type of publication hosted on Wiley
    # order options
    order_values = {"relevant": "relevancy", "recent": "Earliest", "old": ""}
    # join is for terms in search query
    join = '"+"'
    max_query_results = 2000
    articles_path = "/doi/"
    prepend = "https://onlinelibrary.wiley.com"
    extra_key = " "
    articles_path_length = 3

    def get_page_info(self, soup):
        totalResults = soup.find("span", {"class": "result__count"}).text
        totalResults = int(totalResults.replace(",", ""))

        totalPages = ceil(float(totalResults / 20)) - 1
        page = 0
        return page, totalPages, totalResults

    def get_additional_url_arguments(self, soup):
        current_year = datetime.now().year
        journal_list = soup.find(id="Published in").parent.next_sibling
        journal_link_tags = journal_list.find_all("a", href=True)
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

    def turn_page(self, url, pg_num):
        return f"{url.split('&startPage=')[0]}&startPage={pg_num}&pageSize=20"

    def get_license(self, soup):
        open_access = soup.find("div", {"class": {"doi-access"}})
        if open_access and "Open Access" in open_access.text:
            return (True, open_access.text)
        return (False, "unknown")

    def is_link_to_open_article(self, tag):
        """Wiley allows filtering for search. Therefore, if self.open is True, all results will be open."""
        return super().is_link_to_open_article(tag)

    def find_captions(self, figure):
        return figure.find_all("span", class_="graphic_title")

    def save_figure(self, figure_name, image_url):
        figures_directory = self.results_directory / "figures"
        out_file = figures_directory / figure_name
        urlretrieve(image_url, out_file)

    def get_additional_url_arguments(self, page):
        # rsc allows unlimited results, so no need for additional args # TODO: Check if Wiley has unlimited results
        return super().get_additional_url_arguments(page)

    def get_figure_subtrees(self, soup):
        figure_subtrees = soup.find_all("div", "image_table")
        return figure_subtrees

    def get_figure_url(self, figure_subtree):
        return self.prepend + figure_subtree.find("a", href=True)["href"]


journals:dict[str, Type[JournalFamily]] = {
    "acs": ACS,
    "nature": Nature,
    "rsc": RSC,
    "wiley": Wiley,
}
