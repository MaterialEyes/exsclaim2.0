from abc import ABC, abstractmethod
from logging import getLogger
from requests import post, ConnectionError
from typing import Type


__all__ = ["Notifications", "NTFY", "Email", "notifiers", "CouldNotNotifyException"]


class CouldNotNotifyException(BaseException):
	pass


class Notifications(ABC):
	"""An interface designed to notify the user in various ways."""
	def __init__(self, **kwargs):
		self.logger = kwargs.get("logger", getLogger(self.__class__.__name__))

	@abstractmethod
	def notify(self, data: dict | str, name:str, exception: Exception = None):
		...

	@classmethod
	@abstractmethod
	def from_json(cls, json:dict):
		...


class NTFY(Notifications):
	def __init__(self, url:str, access_token:str=None, **kwargs):
		super().__init__(**kwargs)
		self._ntfy_url = url
		self._access_token = access_token
		self._priority = kwargs.get("priority", "3")

	@classmethod
	def from_json(cls, json: dict):
		url = json.get("url", None)
		if url is None:
			raise ValueError("The URL must be provided for NTFY notifications.")
		access_token = json.get("access_token", None)
		priority = json.get("priority", "3")
		return cls(url, access_token, priority=priority)

	def notify(self, data: dict | str, name:str, exception: Exception = None):
		if isinstance(data, dict):
			from json import dumps
			data = dumps(data)

		if exception is not None:
			from traceback import format_exception
			data += ' '.join(format_exception(exception))

		headers = {
			"Markdown": "yes",
			"Title": f"EXSCLAIM: `{name}` Notification",
			"Priority": self._priority,
		}

		if self._access_token is not None:
			headers["Authorization"] = f"Bearer {self._access_token}"

		try:
			post(self._ntfy_url, data, headers=headers)
		except ConnectionError as e:
			raise CouldNotNotifyException(str(e))

	@property
	def url(self) -> str:
		return self._ntfy_url


class Email(Notifications):
	def __init__(self, recipients:tuple[str], **kwargs):
		super().__init__(**kwargs)
		self._recipients = recipients

	@classmethod
	def from_json(cls, json:dict):
		if isinstance(json, str):
			recipients = (json,)
		else:
			recipients = json.get("recipients", tuple())
		return cls(recipients)

	def notify(self, data: dict | str, name:str, exception: Exception = None):
		self.logger.error(f"Setup notifications through email.")


notifiers:dict[str, Type[Notifications]] = {
	"ntfy": NTFY,
	"email": Email
}
