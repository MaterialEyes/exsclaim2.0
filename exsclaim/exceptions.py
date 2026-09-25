from typing import Collection, Optional

__all__ = ["ExsclaimError", "ExsclaimToolException", "JournalScrapeError", "PDFScrapeException", "PipelineInterruptionException",
		   "PipelineConfigError"]


class ExsclaimError(Exception):
	...


class ExsclaimToolException(ExsclaimError):
	...


class PipelineConfigError(ExsclaimError):
	"""An error thrown when the search query has information that would crash the run."""
	def __init__(self, message: str, keys: Optional[Collection[str]]):
		super().__init__()
		self.message = message
		self.keys = keys

	@property
	def string_keys(self) -> str:
		if self.keys is None:
			return "None"
		return f"[{', '.join(self.keys)}]"


class JournalScrapeError(ExsclaimToolException):
	def __init__(self, message: str, status: int = None, headers=None, url: str = None, html=None):
		self.message = message
		self.status = status
		self.headers = headers or dict()
		self.html = html
		self.url = url

	@property
	def status(self) -> int | None:
		return self._status

	@status.setter
	def status(self, status: int | None):
		if status is None:
			self._status = None
			return

		if not isinstance(status, int):
			raise TypeError("HTTP Status code must be an integer.")
		if not (100 <= status <= 599):
			raise ValueError("HTTP Status code must be between 100 and 599.")
		self._status = status

	def __repr__(self):
		return f"{self.__class__.__name__}(status={self.status!r}, message={self.message!r}, headers={self.headers!r})"

	def __str__(self):
		return repr(self)


class PDFScrapeException(ExsclaimToolException):
	...


class PipelineInterruptionException(ExsclaimError):
	...
