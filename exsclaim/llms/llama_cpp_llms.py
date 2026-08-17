from ..caption import LLM, LLMOptions
from .openai_llms import OpenAI

from openai import AsyncOpenAI, NotGiven, NOT_GIVEN
from os import getenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Literal, Optional, Callable, Coroutine

import httpx2
import logging
import re
import ssl

__all__ = ["LlamaCPP", "LlamaCPPSettings"]

SSE_REGEX = re.compile("data: (.+)\\s?")
BOOL_REGEX = re.compile("^0?$")


def _get_context() -> ssl.SSLContext | bool:
	cert_path = settings.SSL_CERT_FILE
	if cert_path is None:
		return True

	return ssl.create_default_context(cafile=cert_path)


class LlamaCPPSettings(BaseSettings):
	model_config = SettingsConfigDict(env_prefix="LLAMA_ARG_", secrets_dir=("/run/secrets/", "/var/run"))

	HOST: Optional[str] = Field(
		default=None,
		description="The directory where the checkpoint files for the FigureSeparator should be stored.",
		examples=["http://localhost:8080", "http://llama-cpp:8080"],
	)

	@field_validator("HOST")
	@classmethod
	def domain_has_no_trailing_slash(cls, url: Optional[str]) -> Optional[str]:
		if url is None:
			return url
		return url.rstrip("/")

	SSL_CERT_FILE: Optional[Path] = Field(
		default=None,
		description="The path to the certificate that httpx2 can use to verify its authenticity.",
	)

	SEND_RUN_ID_HEADER: bool = Field(
		default=False,
		description="Whether or not to send the run id in a header to the Llama.cpp server.",
	)

	@field_validator("SEND_RUN_ID_HEADER", mode="before")
	@classmethod
	def boolean(cls, value) -> bool:
		if isinstance(value, bool):
			return value

		if value is None:
			return False

		if isinstance(value, str):
			return BOOL_REGEX.match(value) is None

		raise ValueError(f"Unknown boolean-coercion type: {type(value).__name__} with value {value}.")

	@field_validator("SSL_CERT_FILE")
	@classmethod
	def cert_file_exists_if_given(cls, cert_path: Optional[Path]) -> Optional[Path]:
		if cert_path is None:
			return cert_path

		cert_path = Path(cert_path)
		if not cert_path.is_file():
			raise FileNotFoundError(f"Llama.cpp certificate file not found at {cert_path}.")

		return cert_path

	TIMEOUT: int | NotGiven = Field(
		default=6000,
		# default=NOT_GIVEN,
	)

	@field_validator("TIMEOUT")
	@classmethod
	def timeout(cls, timeout: Optional[int | str]) -> int | NOT_GIVEN:
		if timeout is None:
			return NOT_GIVEN

		return int(timeout)


settings = LlamaCPPSettings()


class LlamaCPP(OpenAI):
	def __init__(self, model: str, api_key: str = "not-needed", **kwargs):
		base_url = kwargs.setdefault("base_url", "").rstrip('/') or settings.HOST
		if base_url is None:
			raise ValueError("base_url cannot be None.")
		timeout = settings.TIMEOUT

		self._ctx = _get_context()
		headers = dict()

		if settings.SEND_RUN_ID_HEADER and (run_id := kwargs.get("run_id")) is not None:
			headers["X-EXSCLAIM-RUN-ID"] = str(run_id)

		if api_key is not None:
			headers["Authorization"] = f"Bearer {api_key}"

		self.event_hooks: dict[str, list[Coroutine[None, None, Callable[[httpx2.Request | httpx2.Response], None]]]] = \
			kwargs.get("event_hooks", dict())
		self.http_client = httpx2.AsyncClient(base_url=base_url, timeout=timeout, verify=self._ctx, headers=headers,
											 event_hooks=self.event_hooks)

		api_key = api_key or "not-needed"
		LLM.__init__(self, model, api_key, **kwargs)
		self.id = self.convert_alias_to_id()
		self.client = AsyncOpenAI(api_key=api_key, base_url=f"{base_url}/v1", timeout=timeout, http_client=self.http_client)

	def __repr__(self):
		if self.model == self.alias:
			return f"LlamaCPP({self.alias})"

		return f"LlamaCPP({self.model} [{self.alias}])"

	@staticmethod
	def check_validity(model: str, api_key: Optional[str]):
		...

	@staticmethod
	def available_models(silent_fail: bool = False):
		if settings.HOST is None:
			if silent_fail:
				logging.error("Could not connect to Llama.cpp. This may cause issues down the line if Llama.cpp LLMs are required.")
				return ()
			raise ValueError("Cannot get available models from Llama.cpp since the value in `LLAMA_ARG_HOST` is None.")

		with httpx2.Client(base_url=settings.HOST, verify=_get_context(), timeout=120) as client:
			try:
				response = client.get("/v1/models")
			except httpx2.ConnectError as e:
				if silent_fail:
					logging.error(f"Could not connect to Llama.cpp. This may cause issues down the line if Llama.cpp LLMs are required.", exc_info=e)
					return ()
				raise httpx2.ConnectError(f"Could not connect to Llama.cpp server to retrieve the models: {e}") from e

			if silent_fail and not response.is_success:
				logging.error(f"Could not connect to Llama.cpp. This may cause issues down the line if Llama.cpp LLMs are required.")
				return ()

			response.raise_for_status()
			models = response.json()["data"]
		return tuple(
			LLMOptions(model["id"], True, False, model["aliases"][0] if len(model["aliases"]) > 0 else model["id"]) for model in models
		)

	def convert_alias_to_id(self) -> str:
		with httpx2.Client(base_url=self.http_client.base_url, verify=self._ctx, headers=self.http_client.headers) as client:
			response = client.get("/v1/models")
			response.raise_for_status()
			models = response.json()["data"]

		for model in models:
			if self.model == model["id"]:
				return model["id"]

			if self.model in set(model["aliases"]):
				return model["id"]

		raise ValueError(f"Could not find ID for input {self.model}.")

	async def listen_to_events(self, endpoint: Literal["load", "unload"], message_filter: Callable[[dict], bool], logger=None,
							   timeout: int | float = 120, additional_headers: Optional[dict] = None) -> bool:
		"""

		:param logging.Logger | None logger:
		:param endpoint:
		:param message_filter: A filter that checks if the given server side event is what is needed to stop blocking.
		:return: True if the model has been confirmed as fully loaded, False if the request was successfully sent but the load status is unknown
		:rtype:
		"""
		timeout = httpx2.Timeout(5, read=timeout)
		headers = {"Content-Type": "application/json"}
		if additional_headers is not None:
			headers.update(additional_headers)

		if hasattr(self, "__last_sse_id"):
			last_sse_id = self.__last_sse_id
		else:
			self.__last_sse_id = last_sse_id = None

			sse_headers = self.http_client.headers.copy()
			if last_sse_id is not None:
				sse_headers["Last-Event-ID"] = last_sse_id

		try:
			async with httpx2.AsyncClient(base_url=self.http_client.base_url, verify=self._ctx, event_hooks=self.event_hooks,
			                             headers=sse_headers, timeout=timeout) as client:
				async with client.sse("/models/sse") as source:
					endpoint_response = await self.http_client.post(f"/models/{endpoint}", json={"model": self.model},
																	headers=headers)
					if endpoint_response.status_code == 400:
						json = endpoint_response.json()
						if json["error"]["message"] == "model is already running":
							return True

					try:
						endpoint_response.raise_for_status()
					except httpx2.HTTPStatusError as e:
						raise httpx2.HTTPStatusError(f"[{endpoint_response.status_code}] Server failed to {endpoint} the model: {endpoint_response.json()}", request=e.request, response=e.response) from e

					if source.response.status_code != 200:
						if logger is not None:
							logger.warning(f"Could not wait for Llama's server side events to say when model {self.model} was ready: {source.text}")
						return False

					async for event in source:
						data = event.json()
						if event.id is not None:
							self.__last_sse_id = event.id

						match data["event"]:
							case "error":
								if data.get("message", "").startswith("No job has been posted for run"):
									continue
								if logger is not None:
									logger.info(f"An error occurred when trying to get server side events: {data['error']}")
								return False

							case "done":
								if logger is not None:
									logger.info(f"Server side events finished before matching event was sent.")
								return False

							case "status_change":
								try:
									if data["model"] in {self.id, self.model} and message_filter(data):
										return True
								except KeyError as e:
									if logger is not None:
										logger.warning(f"Could not get event from SSE: {data}", exc_info=e)

							case _:
								if logger is not None:
									logger.warning(f"Unknown event type \"{data["event"]}\" received from Llama's SSE with message: {data.get("message", "")}")
		except httpx2.ReadTimeout as e:
			if logger is not None:
				logger.info(f"Did not receive any new server side events in the last {timeout.read:,} seconds.", exc_info=e)
			return False
		except httpx2.TimeoutException as e:
			if logger is not None:
				logger.info(f"Could not connect to server side events to see when the LLM was fully loaded.", exc_info=e)
			return False

	async def load(self, logger=None, num_captions: Optional[int] = None) -> bool:
		def message_filter(data: dict) -> bool:
			return data["data"]["status"] == "loaded" or (data["data"]["status"] == "loading" and data["data"]["progress"]["value"] == 1.0)

		additional_headers = {"X-EXSCLAIM-Num-Captions": str(num_captions)} if num_captions is not None else dict()
		return await self.listen_to_events("load", message_filter, logger=logger, additional_headers=additional_headers)

	async def unload(self, logger=None):
		def message_filter(data: dict) -> bool:
			return data["data"]["status"] == "unloaded"
		return await self.listen_to_events("unload", message_filter, logger=logger)

	@staticmethod
	def request_concurrency() -> Optional[int]:
		concurrency = getenv("LLAMA_CPP_SEMAPHORE")
		if concurrency is None:
			return None
		return int(concurrency)
