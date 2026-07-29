from abc import ABC, abstractmethod
from aiohttp import ClientSession, ClientConnectionError
from typing import Collection, Optional, Type
from uuid import UUID

import httpx
import logging

__all__ = ["Notifications", "NTFY", "Email", "CouldNotNotifyException"]


class CouldNotNotifyException(BaseException):
	pass


class Notifications(ABC):
	"""An interface designed to notify the user in various ways."""
	def __init__(self, **kwargs):
		self.logger = kwargs.get("logger", logging.getLogger("exsclaim.api"))

	@staticmethod
	@abstractmethod
	def json_name() -> str:
		...

	@abstractmethod
	async def notify(self, data: dict | str, name: str, id: Optional[UUID] = None, exception: Exception = None):
		...

	@classmethod
	@abstractmethod
	def from_json(cls, json: dict) -> "Notifications":
		...

	@staticmethod
	def notifiers() -> dict[str, Type["Notifications"]]:
		def get_subclasses(cls) -> set:
			subclasses = set()
			for subclass in cls.__subclasses__():
				subclasses.add(subclass)
				subclasses.update(get_subclasses(subclass))
			return subclasses

		return {notifier.json_name(): notifier for notifier in get_subclasses(Notifications)}


class NTFY(Notifications):
	def __init__(self, url: str, access_token: str = None, **kwargs):
		super().__init__(**kwargs)
		self._ntfy_url = url
		self._access_token = access_token
		self._priority = kwargs.get("priority", "3")

	@staticmethod
	def json_name() -> str:
		return "ntfy"

	@classmethod
	def from_json(cls, json: dict):
		url = json.get("url", None)
		if url is None:
			raise ValueError("The URL must be provided for NTFY notifications.")
		access_token = json.get("access_token", None)
		priority = json.get("priority", "3")
		return cls(url, access_token, priority=priority)

	async def notify(self, data: dict | str, name: str, id: Optional[UUID] = None, exception: Exception = None):
		from .config import ui_settings

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

		if id is not None and ui_settings.DASHBOARD_URL is not None:
			headers["Actions"] = f"view, Open Results, {ui_settings.DASHBOARD_URL}/results/{id}"

		if self._access_token is not None:
			headers["Authorization"] = f"Bearer {self._access_token}"

		async with ClientSession() as session:
			try:
				await session.post(self._ntfy_url, data=data, headers=headers)
			except ClientConnectionError as e:
				raise CouldNotNotifyException from e

	@property
	def url(self) -> str:
		return self._ntfy_url


class Email(Notifications):
	def __init__(self, recipients: tuple[str], **kwargs):
		super().__init__(**kwargs)
		self._recipients = recipients

	@staticmethod
	def json_name() -> str:
		return "email"

	@classmethod
	def from_json(cls, json:dict):
		if isinstance(json, str):
			recipients = (json,)
		else:
			recipients = json.get("recipients", tuple())
		return cls(recipients)

	async def notify(self, data: dict | str, name: str, id: Optional[UUID] = None, exception: Exception = None):
		self.logger.error(f"Setup notifications through email.")


class Webhook(Notifications):
	def __init__(self, url: str, authorization: Optional[str] = None, **kwargs):
		super().__init__(**kwargs)
		self._post_url = url
		self._authorization = authorization

	@staticmethod
	def json_name() -> str:
		return "webhook"

	@classmethod
	def from_json(cls, json: dict):
		url = json.get("url", None)
		if url is None:
			raise ValueError("The URL must be provided for Webhook notifications.")
		authorization = json.get("authorization", None)
		return cls(url, authorization)

	async def notify(self, data: dict | str, name: str, id: Optional[UUID] = None, exception: Exception = None):
		from .config import ui_settings

		data = data.copy()
		if exception is not None:
			from traceback import format_exception
			data["exception"] = ' '.join(format_exception(exception))
		else:
			data["exception"] = None

		headers = dict()
		if self._authorization is not None:
			headers["Authorization"] = self._authorization

		async with httpx.AsyncClient() as session:
			try:
				await session.post(self._post_url, data=data, headers=headers)
			except httpx.HTTPError as e:
				raise CouldNotNotifyException from e
