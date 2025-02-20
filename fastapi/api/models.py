from exsclaim import COMPATIBLE_LLMS, COMPATIBLE_JOURNALS
from fastapi import Path as FastPath
from pydantic import BaseModel
from typing import Annotated, Literal
from typing_extensions import Doc


__all__ = ["BaseModel", "NTFY", "Query", "Article", "Figure", "Subfigure"]


def create_link(link:str) -> str:
	# return f"<a href={link}>{link}</a>"
	# return f"[{link}]({link})"
	return link


class NTFY(BaseModel):
	"""A base model representing the necessary info to send an NTFY notification."""
	link: Annotated[str, FastPath(title=f"The link to the NTFY server, with the topic included (e.g. {create_link('https://ntfy.sh/exsclaim')})")]
	access_token: Annotated[str, FastPath(title=f"The access token that may be needed to send the NTFY notification as stated in {create_link('https://docs.ntfy.sh/publish/#access-tokens')}")] = None
	priority: Annotated[int, FastPath(title=f"The priority of the message as stated in {create_link('https://docs.ntfy.sh/publish/#message-priority')}.", ge=1, le=5)] = 3

	def to_json(self):
		return {
			"url": self.link,
			"access_token": self.access_token,
			"priority": str(self.priority),
		}


class Query(BaseModel):
	name: Annotated[str, FastPath(title="The name of the folder for this run.")]
	journal_family: Annotated[COMPATIBLE_JOURNALS, FastPath(title="The Journal Family that EXSCLAIM should look through.")] = "Nature"
	maximum_scraped: Annotated[int, FastPath(title="The maximum number of articles that EXSCLAIM should scrape. Maximum does not specify how many articles will be scraped before the process ends, only what the upper limit is.", ge=1)] = 5
	sortby: Annotated[Literal["relevant", "recent"], FastPath(title="How the search feature should sort the articles, by the relevancy or the recent publish date.")] = "relevant"
	term: Annotated[str, FastPath(title="The term or phrase that you want searched.")]
	synonyms: Annotated[list[str], FastPath(title="Any synonyms that you're term might be related to.")] = []
	save_format: Annotated[list[Literal["subfigures", "visualization", "boxes", "postgres", "csv", "mongo"]],
	FastPath(title="How the results should be saved.")] = ["boxes"]
	open_access: Annotated[bool, FastPath(title="Determines if EXSCLAIM only uses open-access articles (True).")] = False
	llm: Annotated[COMPATIBLE_LLMS, FastPath(title="The Large Language Model (LLM) that is used to separate captions and generate keywords for articles and figures.")] = "gpt-3.5-turbo"
	model_key: Annotated[str, FastPath(title="The API key that might be needed depending on the specified llm.")] = ""
	emails: Annotated[list[str], FastPath(title="The email address that will receive a notification when EXSCLAIM has finished running.")] = []
	ntfy: Annotated[list[NTFY], FastPath(title="A list of NTFY links that will receive a notification when EXSCLAIM has finished running.")] = []


class Article(BaseModel):
	id: Annotated[str, FastPath(title="The id of the article. Typically, its the url path without the domain name.")]
	title: Annotated[str, FastPath(title="The title of the article.")]
	url: Annotated[str, FastPath(title="The url to reach the article.")]
	license: Annotated[str | None, FastPath(title="The article's license type.")] = None
	open: Annotated[bool, FastPath(title="If the article is open access.")] = False
	authors: Annotated[str | None, FastPath(title="The authors of the article.")] = None
	abstract: Annotated[str | None, FastPath(title="The abstract for the article.")] = None


class Figure(BaseModel):
	# TODO: Check if these descriptions are accurate
	id: Annotated[str, FastPath(title="The id of the figure. Typically, its the id of the article that the figure came from followed by the images number within the article.")]
	caption: Annotated[str | None, FastPath(title="The caption of the figure.")] = None
	caption_delimiter: str | None = None
	url: Annotated[str, FastPath(title="The url to reach the raw figure.")]
	figure_path: Annotated[str, FastPath(title="The path to the ")]
	article_id: Annotated[str, FastPath(title="The id of the article that the figure came from.")]


class Subfigure(BaseModel):
	id: str
	classification_code: Literal["MC", "DF", "GR", "PH", "IL", "UN", "PT"]
	height: float | None = None
	width: float | None = None
	nm_height: float | None = None
	nm_width: float | None = None
	x1: int
	y1: int
	x2: int
	y2: int
	caption: str | None = None
	keywords: list[str]
	figure_id: str
