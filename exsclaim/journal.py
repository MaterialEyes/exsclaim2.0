import itertools
import json
import logging
import os
import pathlib
import random
import shutil
import time
from abc import ABC, abstractmethod
from datetime import datetime
import bs4
import requests
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
from .utilities import paths


class JournalFamily(ABC):
    """Base class to represent journals and provide scraping methods
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
    There are two major types of JournalFamiles (in the future, these
    may make sense to be split into separate subclasses of JournalFamily):
    static and dynamic. Static journal families serve all results using
    static html. Nature is an example. These are simpler as GET requests
    alone will return all of the relevant data. Dynamic familes utilize
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
        """URL portion from end of top level domain to query parameters"""
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
        """URL paremter noting journal to search"""
        return self._journal_param

    @property
    def date_range_param(self) -> str:
        """URL parameter noting range of dates to search"""
        return self._date_range_param

    @property
    def pub_type(self) -> str:
        """URL paramter noting publication type (specific to Wiley)"""
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
        """The journal's url path to articles
        Articles are located at domain.name/articles_path/article
        """
        return self._articles_path

    @property
    def articles_path_length(self) -> int:
        """Number of / separated segments to articles path"""
        return self._articles_path_length

    def __init__(self, search_query: dict):
        """creates an instance of a journal family search using a query
        Args:
            search_query: a query json (python dictionary)
        Returns:
            An initialized instance of a search on a journal family
        """
        self.search_query = search_query
        self.open = search_query.get("open", False)
        self.order = search_query.get("order", "relevant")
        self.logger = logging.getLogger(__name__)
        # Set up file structure
        base_results_dir = paths.initialize_results_dir(
            self.search_query.get("results_dirs", None)
        )
        self.results_directory = base_results_dir / self.search_query["name"]
        figures_directory = self.results_directory / "figures"
        os.makedirs(figures_directory, exist_ok=True)

        # Check if any articles have already been scraped by checking
        # results_dir/_articles
        articles_visited = {}
        articles_file = self.results_directory / "_articles"
        if os.path.isfile(articles_file):
            with open(articles_file, "r") as f:
                contents = f.readlines()
            articles_visited = {a.strip() for a in contents}
        self.articles_visited = articles_visited

    # Helper Methods for retrieving relevant article URLS

    @abstractmethod
    def get_page_info(self, soup: BeautifulSoup) -> tuple:
        """Retrieve details on total results from search query
        Args:
            soup: a search results page
        Returns:
            (index origin, total page count in search, total results from search)
        """
        pass

    @abstractmethod
    def turn_page(self, url: str, page_number: int) -> BeautifulSoup:
        """Return page_number page of search results
        Args:
            url: the url to a search results page
            page_number: page number to search on
        Returns:
            soup of next page
        """
        new_url = url + "&" + self.page_param + str(page_number)
        return self.get_soup_from_request(new_url)

    @abstractmethod
    def get_additional_url_arguments(self, soup: BeautifulSoup) -> tuple:
        """Get lists of additional search url parameters
        Some JournalFamilies limit the number of articles returned
        by a single search. In order to retrieve articles beyond this,
        we create additional search queries filtering for non-overlapping
        sets, and execute them individually.
        Args:
            soup: initial search result for search term
        Returns:
            (years, journal_codes, orderings): where:
                years is a list of strings of desired date ranges
                journal_codes is a list of strings of desired journal codes
                orderings is a list of strings of desired results ordering
            Each of these should be in order of precedence.
        """
        pass

    # Helper Methods for retrieving figures from articles

    @abstractmethod
    def get_license(self, soup: BeautifulSoup) -> tuple:
        """Checks the article license and whether it is open access
        Args:
            soup: representation of page html
        Returns:
            is_open (a bool): True if article is open
            license (a string): Requried text of article license
        """
        return (False, "unknown")

    @abstractmethod
    def is_link_to_open_article(self, tag: BeautifulSoup) -> bool:
        """Checks if link is to an open access article
        Args:
            tag (bs4.tag): A tag containing an href attribute that
                links to an article
        Returns:
            True if the article is confirmed open_access
        """
        return False

    @abstractmethod
    def get_figure_subtrees(self, soup: BeautifulSoup) -> list:
        """Retrieves list of bs4 parse subtrees containing figure elements
        Args:
            soup: A beautifulsoup parse tree
        Returns:
            A list of all figures in the article as BeaustifulSoup objects
        """
        figure_list = [
            a for a in soup.find_all("figure") if str(a).find(self.extra_key) > -1
        ]
        return figure_list

    @abstractmethod
    def get_soup_from_request(self, url: str) -> BeautifulSoup:
        """Get a BeautifulSoup parse tree (lxml parser) from a url request
        Args:
            url: A requested url
        Returns:
            A BeautifulSoup parse tree.
        """
        headers = {
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": (
                "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:82.0)"
                " Gecko/20100101 Firefox/82.0"
            ),
        }
        wait_time = float(random.randint(0, 50))
        time.sleep(wait_time / float(10))
        with requests.Session() as session:
            r = session.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "lxml")
        return soup

    @abstractmethod
    def find_captions(self, figure_subtree: BeautifulSoup) -> bs4.element.ResultSet:
        """
        Returns all captions associated with a given figure
        Args:
            figure_subtree: an bs4 parse tree
        Returns:
            all captions for given figure
        """
        return figure_subtree.find_all("p")

    @abstractmethod
    def save_figure(self, figure_name: str, image_url: str):
        """
        Saves figure at img_url to local machine
        Args:
            figure_name: name of figure
            img_url: url to image
        """
        figures_directory = self.results_directory / "figures"
        response = requests.get(image_url, stream=True)
        figure_path = figures_directory / figure_name
        with open(figure_path, "wb") as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response

    @abstractmethod
    def get_figure_url(self, figure_subtree: BeautifulSoup) -> str:
        """Returns url of figure from figure's html subtree
        Args:
            figure_subtree (bs4): subtree containing an article figure
        Returns:
            url (str)
        """
        image_tag = figure_subtree.find("img")
        image_url = image_tag.get("src")
        return self.prepend + image_url

    def get_search_query_urls(self) -> list:
        """Create list of search query urls based on input query json
        Returns:
            A list of urls (as strings)
        """
        search_query = self.search_query
        # creates a list of search terms
        search_list = [
            [search_query["query"][key]["term"]]
            + search_query["query"][key].get("synonyms", [])
            for key in search_query["query"]
        ]
        search_product = list(itertools.product(*search_list))

        search_urls = []
        for term in search_product:
            url_parameters = "&".join(
                [self.term_param + self.join.join(term), self.max_page_size]
            )
            search_url = self.domain + self.search_path + self.pub_type + url_parameters
            if self.open:
                search_url += "&" + self.open_param + "&"
            soup = self.get_soup_from_request(search_url)
            years, journal_codes, orderings = self.get_additional_url_arguments(soup)
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
        return search_urls

    def get_articles_from_search_url(self, search_url: str) -> list:
        """Generates a list of articles from a single search term"""
        max_scraped = self.search_query["maximum_scraped"]
        self.logger.info("GET request: {}".format(search_url))
        soup = self.get_soup_from_request(search_url)
        start_page, stop_page, total_articles = self.get_page_info(soup)
        article_paths = set()
        for page_number in range(start_page, stop_page + 1):
            for tag in soup.find_all("a", href=True):
                url = tag.attrs["href"]
                self.logger.debug("Candidate Article: {}".format(url))
                if (
                    self.articles_path not in url
                    or url.count("/") != self.articles_path_length
                ):
                    # The url does not point to an article
                    continue
                if url.split("/")[-1] in self.articles_visited or (
                    self.open and not self.is_link_to_open_article(tag)
                ):
                    # It is an article but we are not interested
                    continue
                self.logger.debug("Candidate Article: PASS")
                article_paths.add(url)
                if len(article_paths) >= max_scraped:
                    return article_paths
            # Get next page at end of loop since page 1 is obtained from
            # search_url
            soup = self.turn_page(search_url, page_number + 1)

        return article_paths

    def get_article_extensions(self) -> list:
        """Retrieves a list of article url paths from a search query"""
        # This returns urls based on the combinations of desired search terms.
        search_query_urls = self.get_search_query_urls()
        article_paths = set()
        for search_url in search_query_urls:
            new_article_paths = self.get_articles_from_search_url(search_url)
            article_paths.update(new_article_paths)
            if len(article_paths) >= self.search_query["maximum_scraped"]:
                break
        return list(article_paths)

    def get_article_figures(self, url: str) -> dict:
        """Get all figures from an article
        Args:
            url: A url to a journal article
        Returns:
            A dict of figure_jsons from an article
        """
        soup = self.get_soup_from_request(url)
        is_open, license = self.get_license(soup)

        # Uncomment to save html
        html_directory = self.results_directory / "html"
        os.makedirs(html_directory, exist_ok=True)
        with open(
            html_directory / (url.split("/")[-1] + ".html"), "w", encoding="utf-8"
        ) as file:
            file.write(str(soup))

        figure_subtrees = self.get_figure_subtrees(soup)
        self.logger.info(len(figure_subtrees))
        figure_number = 1
        article_json = {}

        for figure_subtree in figure_subtrees:
            captions = self.find_captions(figure_subtree)

            # acs captions are duplicated, one version with no captions
            if len(captions) == 0:
                continue

            # get figure caption
            figure_caption = ""
            for caption in captions:
                figure_caption += caption.get_text()

            image_url = self.get_figure_url(figure_subtree)
            image_url = self.prepend + image_url #.replace('_hi-res','')
            if ":" not in image_url:
                image_url = "https:" + image_url
            article_name = url.split("/")[-1].split("?")[0]
            figure_name = article_name + "_fig" + str(figure_number) + ".jpg"
            figure_path = (
                pathlib.Path(self.search_query["name"]) / "figures" / figure_name
            )
            # initialize the figure's json
            figure_json = {
                "title": soup.find("title").get_text(),
                "article_url": url,
                "article_name": article_name,
                "image_url": image_url,
                "figure_name": figure_name,
                "license": license,
                "open": is_open,
                "full_caption": figure_caption,
                "caption_delimiter": "",
                "figure_path": str(figure_path),
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
            article_json[figure_name] = figure_json
            self.save_figure(figure_name, image_url)
            # increment index
            figure_number += 1
        return article_json


class Nature(JournalFamily):
    domain = "https://www.nature.com"
    search_path = "/search?"
    page_param = "page="
    max_page_size = ""  # not available for nature
    term_param = "q="
    order_param = "order="
    open_param = ""
    date_range_param = "date_range="
    journal_param = "journal="
    pub_type = ""
    author_param = "author="
    # order options
    order_values = {"relevant": "relevance", "old": "date_asc", "recent": "date_desc"}
    # codes for journals most relevant to materials science
    materials_journals = [
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
    ]

    join = "\"%20\"" #" "
    articles_path = "/articles/"
    articles_path_length = 2
    prepend = ""
    extra_key = " "
    max_query_results = 1000

    def find_captions(self, figure_subtree: BeautifulSoup):
        return super().find_captions(figure_subtree)

    def get_figure_subtrees(self, soup: BeautifulSoup) -> list:
        return super().get_figure_subtrees(soup)

    def get_figure_url(self, figure_subtree: BeautifulSoup) -> str:
        return super().get_figure_url(figure_subtree)

    def get_soup_from_request(self, url: str) -> BeautifulSoup:
        return super().get_soup_from_request(url)

    def save_figure(self, figure_name: str, image_url: str):
        return super().save_figure(figure_name, image_url)

    def turn_page(self, url: str, page_number: int) -> BeautifulSoup:
        return super().turn_page(url, page_number)

    def get_page_info(self, soup):
        def parse_page(page):
            # Fetches the page number given the string 'page #' (e.g. page 1) otherwise
            # returns None
            info = page.strip().split()
            if len(info) != 2 or info[0] != 'page':
                raise ValueError(f"Info {info} should be of the format 'page i'")
            
            return int(info[1])
        
        active_link = soup.find(class_='c-pagination__link c-pagination__link--active')

        try: 
            current_page = parse_page(active_link.text)  
            pages = soup.find_all(class_='c-pagination__item')
            total_pages = parse_page(pages[-2].text)  

        except:
            current_page, total_pages = 1, 1

        if soup.find(attrs={'data-test': 'results-data'}) == None:
            #pass
            raise ValueError(f"No articles were found, try to modily the search criteria")

        try:
            total_results = int(soup.find(attrs={'data-test': 'results-data'}).text.split()[-2])
            return current_page, total_pages, total_results
        except: 
            pass

    def get_additional_url_arguments(self, soup):
        current_year = datetime.now().year
        earliest_year = 1845
        non_exhaustive_years = 25
        # If the search is exhaustive, search all 161 nature journals,
        # for all years since 1845, in relevance, oldest, and youngest order.
        if self.order == "exhaustive":
            search_url = "https://www.nature.com/search/advanced"
            advanced_search = self.get_soup_from_request(search_url)
            journal_tags = advanced_search.find_all(name="journal[]")
            journal_codes = [tag.value for tag in journal_tags]
            years = [
                str(year) + "-" + str(year)
                for year in range(current_year, earliest_year, -1)
            ]
            orderings = list(self.order_values.values())
        # If the search is not exhaustive, search the most relevant materials
        # journals, for the past 25 years, in self.order order.
        else:
            journal_codes = self.materials_journals
            years = [
                str(year) + "-" + str(year)
                for year in range(current_year - non_exhaustive_years, current_year)
            ]
            orderings = [self.order_values[self.order]]
        years = [""] + years
        #author = 
        return years, journal_codes, orderings

    def get_license(self, soup):
        data_layer = soup.find(attrs={"data-test": "dataLayer"})
        data_layer_string = str(data_layer.string)
        data_layer_json = (
            "{" + data_layer_string.split("[{", 1)[1].split("}];", 1)[0] + "}"
        )
        parsed = json.loads(data_layer_json)
        # try to get whether the journal is open
        try:
            is_open = parsed["content"]["attributes"]["copyright"]["open"]
        except KeyError:
            is_open = False
        # try to get license
        try:
            license = parsed["content"]["attributes"]["copyright"]["legacy"][
                "webtrendsLicenceType"
            ]
        except KeyError:
            license = "unknown"
        return is_open, license

    def is_link_to_open_article(self, tag):
        current_tag = tag
        while current_tag.parent:
            if (
                current_tag.name == "li"
                and "app-article-list-row__item" in current_tag["class"]
            ):
                break
            current_tag = current_tag.parent
        candidates = current_tag.find_all("span", class_="u-color-open-access")
        for candidate in candidates:
            if candidate.text.startswith("Open"):
                return True
        return False
