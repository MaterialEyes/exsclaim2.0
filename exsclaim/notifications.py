from .config import ui_settings

from abc import ABC, abstractmethod
from datetime import datetime as dt, timezone as tz
from enum import Enum
from pydantic import BaseModel, model_validator, field_validator, EmailStr, ConfigDict
from typing import Annotated, Collection, Optional, Type, Self
from uuid import UUID

import fastapi
import httpx
import logging
import re

__all__ = ["Notification", "Notifications", "NTFY", "Email", "Webhook", "CouldNotNotifyException"]


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
	async def notify(self, notification: Notification):
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

	@abstractmethod
	@model_validator(mode="after")
	async def is_valid_notifier(self) -> Self:
		...

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
	access_token: Annotated[str, Path(
		title=f"The access token fastapi.that may be needed to send the NTFY notification as stated in {create_link('https://docs.ntfy.sh/publish/#access-tokens')}")] = None
	priority: Annotated[int, fastapi.Path(
		title=f"The priority of the message as stated in {create_link('https://docs.ntfy.sh/publish/#message-priority')}.",
		ge=1, le=5)] = 3

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

	async def notify(self, notification: Notification):
		from json import dumps

		headers = {
			"Markdown": "yes",
			"Title": f"EXSCLAIM: `{notification.name}` Notification",
			"Priority": self._priority,
		}

		if (ui_link := self._get_results_link(notification.run_id)) is not None:
			headers["Actions"] = f"view, Open Results, {ui_link}"

		if self._access_token is not None:
			headers["Authorization"] = f"Bearer {self._access_token}"

		async with httpx.AsyncClient() as client:
			try:
				await client.post(self._ntfy_url, data=notification.model_dump(), headers=headers)
			except httpx.ConnectError as e:
				raise CouldNotNotifyException from e


class Email(Notifications):
	recipients: list[EmailStr]

	async def notify(self, notification: Notification):
		self.logger.warning("Email notifications have not been setup.")

	async def is_valid_notifier(self) -> Self:
		return self # Only checking that the emails' syntax is correct, which they are because of the EmailStr


class WebhookType(Enum):
	Slack = "Slack"
	Discord = "Discord"
	Default = "Default"


class Webhook(Notifications):
	"""
	When setting up a webhook, there are two types of events that will be sent.
	The first is the `test` event sent before the pipeline runs.
	The webhook needs to respond with status 202 Accepted for the pipeline to accept that the webhook is properly configured.
	The second event is the `message` event, which is the pipeline sending if the pipeline finished successfully or crashed.
	The pipeline must respond with a 200 or 300 level status code that is **not** 202, or else the pipeline will think that the message didn't go through.
	"""
	url: Annotated[str, fastapi.Path(title="The url that should be posted to.")]
	authorization: Annotated[Optional[str], fastapi.Path(title=f"The bearer token that should be sent with the webhook. This takes priority over a the Authorization header you may pass, so leave it empty if you're handling headers through the headers value.")] = None
	headers: Annotated[dict[str, str], fastapi.Path(default_factory=dict, title=f"The headers that should be sent with the webhook.")]
	type: Annotated[WebhookType, fastapi.Path(title="The application type of the webhook.")] = WebhookType.Default

	async def _send_post(self, notification: Notification) -> httpx.Response:
		headers = self.headers.copy()
		if self.authorization is not None:
			headers["Authorization"] = self.authorization

		headers["Content-Type"] = "application/json"

		async with httpx.AsyncClient() as client:
			try:
				return await client.post(self.url, data=notification.model_dump(), headers=headers)
			except httpx.HTTPError as e:
				raise CouldNotNotifyException from e

	async def _send_slack_webhook(self, notification: Notification) -> httpx.Response:
		headers = {"Content-Type": "application/json"}
		timestamp = f"<!date^{int(notification.time.timestamp())}^ {{date_short_pretty}} at {{time_secs}}|{notification.time.isoformat()}>"

		if notification.exception is not None:
			logs_link = self._get_logs_link(notification.run_id)
			if logs_link is None:
				data = {"text": f"Results for {notification.name} failed to compile due to {type(notification.exception).__name__} at {timestamp}."}
			else:
				data = {
					"text": f"Results for *{notification.name}* failed.",
					"blocks": [
						{
							"type": "section",
							"text": {
								"type": "mrkdwn",
								"text": f"Results for <{logs_link}|{notification.name}> failed at {timestamp}. "
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
								"text": f"Results for <{ui_link}|{notification.name}> finished {timestamp} and can be"
										f" viewed at <{ui_link}|{ui_link}>."
							}
						},
					]
				}
			else:
				data = {"text": f"Results for *{notification.name}* finished compiling {timestamp}."}

		async with httpx.AsyncClient() as client:
			return await client.post(self.url, headers=headers, json=data)

	async def _send_discord_webhook(self, notification: Notification) -> httpx.Response:
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
		data["avatar_url"] = "https://raw.githubusercontent.com/MaterialEyes/exsclaim2.0/b22ed4009c63ddd58d8415c5882ab58febde691c/dashboard/public/favicon.ico"

		async with httpx.AsyncClient() as client:
			return await client.post(self.url, headers=headers, json=data)

	async def send_post(self, notification: Notification) -> httpx.Response:
		match self.type:
			case WebhookType.Slack:
				return await self._send_slack_webhook(notification)
			case WebhookType.Discord:
				return await self._send_discord_webhook(notification)
			case _:
				return await self._send_post(notification)

	async def notify(self, notification: Notification):
		response = await self.send_post(notification)
		try:
			response.raise_for_status()
		except httpx.HTTPError as e:
			raise CouldNotNotifyException(f"[{response.status_code}] The status code that the webhook responded with "
										  f"did not match what was expected: {response.text}.") from e
		return response

	def _test_discord_webhook(self):
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

	def is_valid_notifier(self) -> Self:
		url = self.url

		if re.match(r"https://hooks.slack.com/services/T(\w{8,})/B(\w{8,})/(\w{24})", url):
			self.type = WebhookType.Slack
		elif url.startswith(r"https://discord.com/api/webhooks/"):
			self.type = WebhookType.Discord

		match self.type:
			case WebhookType.Discord:
				self._test_discord_webhook()
			case _:
				...

		return self
