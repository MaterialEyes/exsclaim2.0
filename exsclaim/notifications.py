from .config import ui_settings

from abc import ABC, abstractmethod
from datetime import datetime as dt, timezone as tz
from pydantic import BaseModel, model_validator, field_validator, EmailStr, ConfigDict, RootModel, model_serializer, \
	GetCoreSchemaHandler
from pydantic_core import CoreSchema
from typing import Annotated, Collection, Generator, Optional, Type, Self
from uuid import UUID

import fastapi
import httpx
import logging
import re

__all__ = ["Notification", "Notifications", "NTFY", "Email", "Webhook", "CouldNotNotifyException", "QueryNotifications"]


def create_link(link: str) -> str:
	# return f"<a href={link}>{link}</a>"
	# return f"[{link}]({link})"
	return link


class CouldNotNotifyException(BaseException):
	pass


class Notification(BaseModel):
	model_config = ConfigDict(arbitrary_types_allowed=True)
	message: str | dict[str, str]
	run_id: Optional[UUID] = None
	name: str
	time: dt = dt.now(tz.utc)
	exception: Optional[str | BaseException] = None


class Notifications(BaseModel, ABC):
	"""An interface designed to notify the user in various ways."""
	@classmethod
	def json_name(cls) -> str:
		return cls.__name__.lower()

	@abstractmethod
	async def notify(self, notification: Notification, logger: logging.Logger):
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

	def _get_results_link(self, results_id: Optional[UUID]) -> Optional[str]:
		if ui_settings.DASHBOARD_URL is None or results_id is None:
			return None

		return f"{ui_settings.DASHBOARD_URL}/results/{results_id}"

	def _get_logs_link(self, results_id: Optional[UUID]) -> Optional[str]:
		if ui_settings.PUBLIC_API_URL is None or results_id is None:
			return None

		return f"{ui_settings.PUBLIC_API_URL}/results/{results_id}/logs"


class NTFY(Notifications):
	"""A base model representing the necessary info to send an NTFY notification."""
	url: Annotated[str, fastapi.Path(
		title=f"The url to the NTFY server, with the topic included (e.g. {create_link('https://ntfy.sh/exsclaim')})")]

	access_token: Annotated[Optional[str], Path(
		title=f"The access token fastapi.that may be needed to send the NTFY notification as stated in {create_link('https://docs.ntfy.sh/publish/#access-tokens')}")] = None

	@field_validator("url", "access_token", mode="after")
	@classmethod
	def strip_whitespace(cls, value: Optional[str]) -> Optional[str]:
		if value is None:
			return value
		return value.strip()

	priority: Annotated[int, fastapi.Path(
		title=f"The priority of the message as stated in {create_link('https://docs.ntfy.sh/publish/#message-priority')}.",
		ge=1, le=5)] = 3

	@model_validator(mode="after")
	def is_valid_notifier(self) -> Self:
		"""Checks if the given NTFY server is valid."""
		try:
			with httpx.Client() as client:
				response: httpx.Response = client.get(self.url)
				if response.is_success or response.is_redirect:
					return self
				raise ValueError(response.text)
		except httpx.InvalidURL as e:
			raise ValueError(str(e)) from e

	async def notify(self, notification: Notification, logger: logging.Logger):
		from json import dumps

		headers = {
			"Markdown": "yes",
			"Title": f"EXSCLAIM: `{notification.name}` Notification",
			"Priority": str(self.priority),
		}

		if (ui_link := self._get_results_link(notification.run_id)) is not None:
			headers["Actions"] = f"view, Open Results, {ui_link}"

		if self.access_token is not None:
			headers["Authorization"] = f"Bearer {self.access_token}"

		if notification.exception is None:
			data = f"EXSCLAIM! query{f' `{notification.run_id}`' if notification.run_id is not None else ''} finished at: {notification.time:%Y-%m-%dT%H:%M%z}."
		elif isinstance(notification.exception, (asyncio.CancelledError, KeyboardInterrupt)):
			data = f"The pipeline was stopped at {notification.time:%Y-%m-%dT%H:%M%z} for{' the' if notification.run_id is None else ''} EXSCLAIM! query{f' `{notification.run_id}`' if notification.run_id is not None else ''}."
		else:
			from traceback import format_exception
			data = f"An error occurred at {notification.time:%Y-%m-%dT%H:%M%z} running{' the' if notification.run_id is None else ''} EXSCLAIM! query{f' `{notification.run_id}`' if notification.run_id is not None else ''}."
			data += ' '.join(format_exception(exception))

		async with httpx.AsyncClient() as client:
			try:
				await client.post(self.url, data=data, headers=headers)
			except httpx.ConnectError as e:
				raise CouldNotNotifyException from e


class Email(Notifications, RootModel[list[EmailStr]]):
	async def notify(self, notification: Notification, logger: logging.Logger):
		emails = self.root
		logger.warning("Email notifications have not been setup.")


class Webhook(Notifications):
	"""
	When setting up a webhook, there are two types of events that will be sent.
	The first is the `test` event sent before the pipeline runs.
	The webhook needs to respond with status 202 Accepted for the pipeline to accept that the webhook is properly configured.
	The second event is the `message` event, which is the pipeline sending if the pipeline finished successfully or crashed.
	The pipeline must respond with a 200 or 300 level status code that is **not** 202, or else the pipeline will think that the message didn't go through.
	"""
	url: Annotated[str, fastapi.Path(title="The url that should be posted to.")]

	authorization: Annotated[Optional[str], fastapi.Path(
		title=f"The bearer token that should be sent with the webhook. This takes priority over a the Authorization header you may pass, so leave it empty if you're handling headers through the headers value.")] = None

	headers: Annotated[dict[str, str], fastapi.Path(default_factory=dict, title=f"The headers that should be sent with the webhook.")]

	@staticmethod
	def get_url_pattern() -> re.Pattern[str]:
		return re.compile("^.*$")

	@model_validator(mode="wrap")
	@classmethod
	def _resolve_adaptive_object(cls, data: dict, handler: GetCoreSchemaHandler, /) -> Webhook:
		if Notifications not in cls.__bases__:
			return handler(data)

		url = data["url"]
		for subclass in cls.__subclasses__():
			if subclass.get_url_pattern().match(url):
				return subclass.model_validate(data)

		return cls.model_validate(data)

	async def notify(self, notification: Notification, logger: logging.Logger) -> httpx.Response:
		headers = self.headers.copy()
		if self.authorization is not None:
			headers["Authorization"] = self.authorization

		headers["Content-Type"] = "application/json"

		async with httpx.AsyncClient() as client:
			try:
				response = await client.post(self.url, data=notification.model_dump(), headers=headers)
				response.raise_for_status()
			except httpx.HTTPError as e:
				raise CouldNotNotifyException from e


class Slack(Webhook):
	"""
	When setting up a webhook, there are two types of events that will be sent.
	The first is the `test` event sent before the pipeline runs.
	The webhook needs to respond with status 202 Accepted for the pipeline to accept that the webhook is properly configured.
	The second event is the `message` event, which is the pipeline sending if the pipeline finished successfully or crashed.
	The pipeline must respond with a 200 or 300 level status code that is **not** 202, or else the pipeline will think that the message didn't go through.
	"""
	@staticmethod
	def get_url_pattern() -> re.Pattern[str]:
		return re.compile(r"https://hooks.slack.com/services/T(\w{8,})/B(\w{8,})/(\w{24})")

	async def notify(self, notification: Notification, logger: logging.Logger) -> httpx.Response:
		headers = {"Content-Type": "application/json"}
		timestamp = f"<!date^{int(notification.time.timestamp())}^ {{date_short_pretty}} at {{time_secs}}|{notification.time.isoformat()}>"

		if notification.exception is not None:
			logs_link = self._get_logs_link(notification.run_id)
			if logs_link is None:
				data = {"text": f"Results for {notification.name} failed to compile due to {type(notification.exception).__name__} at{timestamp}."}
			else:
				data = {
					"text": f"Results for *{notification.name}* failed.",
					"blocks": [
						{
							"type": "section",
							"text": {
								"type": "mrkdwn",
								"text": f"Results for <{logs_link}|{notification.name}> failed at{timestamp}. "
										f"Logs are available at <{logs_link}|{logs_link}>."
							}
						},
					]
				}
		else:
			ui_link = self._get_results_link(notification.run_id)
			if ui_link is not None:
				data = {
					"text": f"Results for {notification.name} available at {ui_link}.",
					"blocks": [
						{
							"type": "section",
							"text": {
								"type": "mrkdwn",
								"text": f"Results for <{ui_link}|{notification.name}> finished{timestamp} and can be"
										f" viewed at <{ui_link}|{ui_link}>."
							}
						},
					]
				}
			else:
				data = {"text": f"Results for *{notification.name}* finished compiling{timestamp}."}

		async with httpx.AsyncClient() as client:
			try:
				response = await client.post(self.url, headers=headers, json=data)
				response.raise_for_status()
			except httpx.HTTPError as e:
				raise CouldNotNotifyException(f"[{response.status_code}] The status code that the webhook responded with "
			                              f"did not match what was expected: {response.text}.") from e
		return response


class Discord(Webhook):
	@staticmethod
	def get_url_pattern() -> re.Pattern[str]:
		return re.compile(r"https://discord.com/api/webhooks/(\d{17,19})/(\w+)")

	async def notify(self, notification: Notification, logger: logging.Logger) -> httpx.Response:
		headers = {"Content-Type": "application/json"}
		iso_timestamp = f"{notification.time:%Y-%m-%d %H:%M}"
		timestamp = int(notification.time.timestamp())
		timestamp = f"<t:{timestamp}:f>"

		if notification.exception is not None:
			logs_link = self._get_logs_link(notification.run_id)
			if logs_link is None:
				description = f"Results for **{notification.name}** failed to compile due to {type(notification.exception).__name__} at {timestamp}.",
			else:
				description = f"Results for [{notification.name}]({logs_link}) failed on {timestamp}. Logs are available at {logs_link}."

			data = {
				"content": None,
				"embeds": [{
					"title": f"{notification.name}: Pipeline Failed",
					"description": description,
					"url": logs_link,
					"color": 16711680,
					"timestamp": iso_timestamp
				}],
				"attachments": []
			}
		else:
			ui_link = self._get_results_link(notification.run_id)
			if ui_link is None:
				description = f"Results for **{notification.name}** finished compiling {timestamp}."
			else:
				description = f"Results for [{notification.name}]({ui_link}) finished {timestamp} and can be viewed at {ui_link}."

			data = {
				"content": None,
				"embeds": [{
					"title": f"{notification.name}: Pipeline Finished",
					"description": description,
					"url": ui_link,
					"color": 44543,
					"timestamp": iso_timestamp
				}],
				"attachments": []
			}

		data["username"] = "EXSCLAIM Pipeline"
		data["avatar_url"] = "https://raw.githubusercontent.com/MaterialEyes/exsclaim2.0/54317f169b0436eadde45bcc391c9beaf0a1135e/exsclaim/dashboard/assets/favicon.png"

		async with httpx.AsyncClient() as client:
			try:
				response = await client.post(self.url, headers=headers, json=data)
				response.raise_for_status()
			except httpx.HTTPError as e:
				raise CouldNotNotifyException(
					f"[{response.status_code}] The status code that the webhook responded with "
					f"did not match what was expected: {response.text}.") from e

	@model_validator(mode="after")
	def is_valid_notifier(self) -> Self:
		headers = {
			"Accept": "*/*",
			"Content-Type": "application/json",
		}

		with httpx.Client() as client:
			try:
				response = client.get(self.url, headers=headers)
				response.raise_for_status()
			except httpx.HTTPError as e:
				raise ValueError("Test ping for Discord did not work") from e

		return self


class QueryNotifications(BaseModel):
	ntfy: Annotated[list[NTFY], Path(title="A list of NTFY links that will receive a notification when EXSCLAIM has finished running.",
	                                 default_factory=list)]

	emails: Annotated[Email, Path(title="A list of email addresses that will receive a notification when EXSCLAIM has finished running.")]

	webhooks: Annotated[list[Webhook], Path(title="A list of webhooks that the system will POST to when EXSCLAIM has finished running.",
	                                        default_factory=list)]

	def __iter__(self) -> Generator[Notification, None, None]:
		for notifiers in (self.ntfy, self.webhooks):
			for notifier in notifiers:
				yield notifier

		yield self.emails
