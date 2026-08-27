from .config import ui_settings

from abc import ABC, abstractmethod
from datetime import datetime as dt, timezone as tz, timedelta as td, tzinfo
from email.message import EmailMessage
from pydantic import BaseModel, model_validator, field_validator, EmailStr, ConfigDict, RootModel, GetCoreSchemaHandler, \
	field_serializer, WithJsonSchema, Field
from smtplib import SMTP, SMTP_SSL
from typing import Annotated, Generator, Optional, Type, Self
from uuid import UUID

import asyncio
import httpx2
import logging
import re
import ssl
import zoneinfo

__all__ = ["Notification", "SuccessNotification", "InterruptionNotification", "ErrorNotification", "Notifications",
		   "NTFY", "Email", "Webhook", "CouldNotNotifyException", "QueryNotifications"]


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
	time: dt = Field(default_factory=lambda: dt.now(tz=tz.utc),
					 description=f"The headers that should be sent with the webhook.")


class SuccessNotification(Notification):
	...


class InterruptionNotification(Notification):
	exception: str | asyncio.CancelledError | KeyboardInterrupt


class ErrorNotification(Notification):
	exception: str | BaseException


TZInfo = Annotated[
	tzinfo,
	WithJsonSchema({
		"oneOf": [
			{"type": "string", "examples": ["UTC", "America/Chicago"]},
			{"type": "number", "examples": [0, -5, 5]}
		]
	})
]


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

	@staticmethod
	def _get_results_link(results_id: Optional[UUID]) -> Optional[str]:
		if ui_settings.DASHBOARD_URL is None or results_id is None:
			return None

		return f"{ui_settings.DASHBOARD_URL}/results/{results_id}"

	@staticmethod
	def _get_logs_link(results_id: Optional[UUID]) -> Optional[str]:
		if ui_settings.PUBLIC_API_URL is None or results_id is None:
			return None

		return f"{ui_settings.PUBLIC_API_URL}/results/{results_id}/logs"


class NTFY(Notifications):
	"""A base model representing the necessary info to send an NTFY notification."""
	model_config = ConfigDict(arbitrary_types_allowed=True)

	url: str = Field(
		description=f"The url to the NTFY server, with the topic included (e.g. {create_link('https://ntfy.sh/exsclaim')})")

	access_token: Optional[str] = Field(
		default=None,
		description=f"The access token fastapi.that may be needed to send the NTFY notification as stated in {create_link('https://docs.ntfy.sh/publish/#access-tokens')}"
	)

	priority: int = Field(
		title=f"The priority of the message as stated in {create_link('https://docs.ntfy.sh/publish/#message-priority')}.",
		default=3,
		ge=1,
		le=5
	)

	timezone: TZInfo = Field(
		default=zoneinfo.ZoneInfo("localtime"),
		title="A timezone used to send the relative time to NTFY since NTFY's client cannot parse it directly.",
	)

	@field_validator("timezone", mode="before")
	@classmethod
	def get_timezone(cls, value: Optional[str | float | int]) -> TZInfo:
		if value is None:
			return tz.utc

		elif isinstance(value, float | int):
			return tz(td(hours=value))

		elif value not in zoneinfo.available_timezones():
			raise ValueError(f"No time zone found with key {value}.")

		return zoneinfo.ZoneInfo(value)

	@field_validator("url", "access_token", mode="after")
	@classmethod
	def strip_whitespace(cls, value: Optional[str]) -> Optional[str]:
		if value is None:
			return value
		return value.strip()

	@model_validator(mode="after")
	def is_valid_notifier(self) -> Self:
		"""Checks if the given NTFY server is valid."""
		try:
			with httpx2.Client() as client:
				response: httpx2.Response = client.get(self.url)
				if response.is_success or response.is_redirect:
					return self
				raise ValueError(response.text)
		except httpx2.InvalidURL as e:
			raise ValueError(str(e)) from e

	@field_serializer("timezone")
	def serialize_timezone(self, value: TZInfo) -> Optional[str | int | float]:
		if isinstance(value, zoneinfo.ZoneInfo):
			return value.key

		return dt.now(value).utcoffset().total_seconds() / 3600

	async def notify(self, notification: Notification, logger: logging.Logger):
		headers = {
			"Markdown": "yes",
			"Title": f"EXSCLAIM: `{notification.name}` Notification",
			"Priority": str(self.priority),
		}

		if (ui_link := self._get_results_link(notification.run_id)) is not None:
			headers["Actions"] = f"view, Open Results, {ui_link}"

		if self.access_token is not None:
			headers["Authorization"] = f"Bearer {self.access_token}"

		finished_at = notification.time.astimezone(self.timezone).strftime("%Y-%m-%dT%H:%M%z")

		if isinstance(notification, SuccessNotification):
			data = f"EXSCLAIM! query{f' `{notification.run_id}`' if notification.run_id is not None else ''} finished at: {finished_at}."
		elif isinstance(notification, InterruptionNotification):
			data = f"The pipeline was stopped at {finished_at} for{' the' if notification.run_id is None else ''} EXSCLAIM! query{f' `{notification.run_id}`' if notification.run_id is not None else ''}."
		elif isinstance(notification, ErrorNotification):
			from traceback import format_exception
			data = f"An error occurred at {finished_at} running{' the' if notification.run_id is None else ''} EXSCLAIM! query{f' `{notification.run_id}`' if notification.run_id is not None else ''}.\n"
			data += ' '.join(format_exception(notification.exception))

		async with httpx2.AsyncClient() as client:
			try:
				await client.post(self.url, data=data, headers=headers)
			except httpx2.ConnectError as e:
				raise CouldNotNotifyException from e


class Email(Notifications, RootModel[list[EmailStr]]):
	@model_validator(mode="after")
	def is_valid_notifier(self) -> Self:
		if ui_settings.EMAIL is None and not ui_settings.ALLOW_EMAILS_WITHOUT_ACCOUNT:
			raise ValueError("Emails cannot be sent because this pipeline does not have the ability to send emails. Remove the emails before re-submitting your query.")

		return self

	async def notify(self, notification: Notification, logger: logging.Logger):
		emails = self.root
		if len(emails) == 0:
			return

		email_settings = ui_settings.EMAIL
		if email_settings is None:
			logger.warning("Email credentials were not provided by the pipeline's maintainer, so emails cannot be sent.")
			return

		messages: list[EmailMessage] = [EmailMessage() for _ in emails]
		for i, (email, msg) in enumerate(zip(emails, messages)):
			msg["Subject"] = f"EXSCLAIM Run {notification.name} ({notification.run_id})"
			msg["From"] = email_settings.ACCOUNT
			msg["To"] = email

			if isinstance(notification, SuccessNotification):
				link = self._get_results_link(notification.run_id)
				text = f"EXSCLAIM run {notification.name} completed at {notification.time}."

				if link is not None:
					html = f"EXSCLAIM run <a href={notification.name}>{link}</a> completed at {notification.time} and the results can be viewed at <a href={link}>{link}</a>."
				else:
					html = text
			elif isinstance(notification, InterruptionNotification):
				text = html = f"EXSCLAIM run stopped by user request."
			elif isinstance(notification, ErrorNotification):
				logs_link = self._get_logs_link(notification.run_id)
				text = f"EXSCLAIM run stopped due to an error at {notification.time}."
				html = f"EXSCLAIM run stopped due to an error at {notification.time} and the logs can be viewed at <a href={logs_link}>{logs_link}</a>."

			msg.set_content(text)
			msg.add_alternative(html, subtype="html")
			messages[i] = msg

		if email_settings.SERVER == "localhost":
			server = SMTP(email_settings.SERVER, email_settings.PORT)
		else:
			context = ssl.create_default_context()
			server = SMTP_SSL(email_settings.SERVER, email_settings.PORT, context=context)

		with server:
			server.login(email_settings.ACCOUNT, email_settings.PASSWORD)
			for msg in messages:
				server.send_message(msg)


class Webhook(Notifications):
	"""
	When setting up a webhook, there are two types of events that will be sent.
	The first is the `test` event sent before the pipeline runs.
	The webhook needs to respond with status 202 Accepted for the pipeline to accept that the webhook is properly configured.
	The second event is the `message` event, which is the pipeline sending if the pipeline finished successfully or crashed.
	The pipeline must respond with a 200 or 300 level status code that is **not** 202, or else the pipeline will think that the message didn't go through.
	"""
	url: str = Field(description="The url that should be posted to.")

	authorization: Optional[str] = Field(default=None,
										 description=f"The bearer token that should be sent with the webhook. This takes priority over a the Authorization header you may pass, so leave it empty if you're handling headers through the headers value.")

	headers: dict[str, str] = Field(default_factory=dict, description=f"The headers that should be sent with the webhook.")

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

	async def notify(self, notification: Notification, logger: logging.Logger) -> httpx2.Response:
		headers = self.headers.copy()
		if self.authorization is not None:
			headers["Authorization"] = self.authorization

		headers["Content-Type"] = "application/json"

		async with httpx2.AsyncClient() as client:
			try:
				response = await client.post(self.url, data=notification.model_dump(), headers=headers)
				response.raise_for_status()
			except httpx2.HTTPError as e:
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

	async def notify(self, notification: Notification, logger: logging.Logger) -> httpx2.Response:
		headers = {"Content-Type": "application/json"}
		timestamp = f"<!date^{int(notification.time.timestamp())}^ {{date_short_pretty}} at {{time_secs}}|{notification.time.isoformat()}>"

		if isinstance(notification, InterruptionNotification):
			data = {"text": f"Results for {notification.name} were stopped by the user at{timestamp}."}
		elif isinstance(notification, ErrorNotification):
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
		elif isinstance(notification, SuccessNotification):
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

		async with httpx2.AsyncClient() as client:
			try:
				response = await client.post(self.url, headers=headers, json=data)
				response.raise_for_status()
			except httpx2.HTTPError as e:
				raise CouldNotNotifyException(f"[{response.status_code}] The status code that the webhook responded with "
			                              f"did not match what was expected: {response.text}.") from e
		return response


class Discord(Webhook):
	@staticmethod
	def get_url_pattern() -> re.Pattern[str]:
		return re.compile(r"https://discord.com/api/webhooks/(\d{17,19})/(\w+)")

	async def notify(self, notification: Notification, logger: logging.Logger) -> httpx2.Response:
		headers = {"Content-Type": "application/json"}
		iso_timestamp = f"{notification.time:%Y-%m-%d %H:%M}"
		timestamp = int(notification.time.timestamp())
		timestamp = f"<t:{timestamp}:f>"

		if isinstance(notification, InterruptionNotification):
			logs_link = self._get_logs_link(notification.run_id)
			description = f"Results for **{notification.name}** were stopped by the user at {timestamp}.",
			data = {
				"content": None,
				"embeds": [{
					"title": f"{notification.name}: Pipeline Stopped",
					"description": description,
					"url": logs_link,
					"color": 16711680,
					"timestamp": iso_timestamp
				}],
				"attachments": []
			}

		elif isinstance(notification, ErrorNotification):
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
		elif isinstance(notification, SuccessNotification):
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

		async with httpx2.AsyncClient() as client:
			try:
				response = await client.post(self.url, headers=headers, json=data)
				response.raise_for_status()
			except httpx2.HTTPError as e:
				raise CouldNotNotifyException(
					f"[{response.status_code}] The status code that the webhook responded with "
					f"did not match what was expected: {response.text}.") from e
		return response

	@model_validator(mode="after")
	def is_valid_notifier(self) -> Self:
		headers = {
			"Accept": "*/*",
			"Content-Type": "application/json",
		}

		with httpx2.Client() as client:
			try:
				response = client.get(self.url, headers=headers)
				response.raise_for_status()
			except httpx2.HTTPError as e:
				raise ValueError("Test ping for Discord did not work") from e

		return self


class QueryNotifications(BaseModel):
	ntfy: list[NTFY] = Field(description="A list of NTFY links that will receive a notification when EXSCLAIM has finished running.",
							 default_factory=list)

	emails: Email = Field(description="A list of email addresses that will receive a notification when EXSCLAIM has finished running.",
						  default_factory=lambda: Email.model_validate([]))

	webhooks: list[Webhook] = Field(description="A list of webhooks that the system will POST to when EXSCLAIM has finished running.",
									default_factory=list)

	def __iter__(self) -> Generator[Notification, None, None]:
		for notifiers in (self.ntfy, self.webhooks):
			for notifier in notifiers:
				yield notifier

		yield self.emails
