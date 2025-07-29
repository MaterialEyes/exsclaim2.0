__all__ = ["ExsclaimToolException", "JournalScrapeError", "PDFScrapeException", "PipelineInterruptionException"]


class ExsclaimToolException(Exception):
	...

class JournalScrapeError(ExsclaimToolException):
	def __init__(self, message:str, status:int = None, headers=None):
		self.message = message
		self.status = status
		self.headers = headers or {}

	@property
	def status(self) -> int | None:
		return self._status

	@status.setter
	def status(self, status:int | None):
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


class PipelineInterruptionException(BaseException):
	...
