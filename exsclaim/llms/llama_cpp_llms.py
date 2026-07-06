from openai import AsyncOpenAI

from ..caption import LLM
from .openai_llms import OpenAI, NOT_GIVEN
from ..config import settings

from httpx import Client, AsyncClient, ReadTimeout, Timeout
from os import getenv
from orjson import loads
from pathlib import Path
from re import compile
from typing import Literal, Optional, Callable

import ssl

__all__ = ["LlamaCPP"]


SEE_REGEX = compile("data: (.+)\\s?")


def _get_context() -> Optional[ssl.SSLContext]:
	cert_path = getenv("LLAMA_ARG_SSL_CERT_FILE")
	if cert_path is None:
		return None

	if not Path(cert_path).is_file():
		raise FileNotFoundError(f"Llama.cpp certificate file not found at {cert_path}.")

	return ssl.create_default_context(cafile=cert_path)


class LlamaCPP(OpenAI):
	def __init__(self, model: str, api_key: str = "not-needed", **kwargs):
		from os import getenv
		base_url = kwargs.setdefault("base_url", f"{settings.LLAMA_CPP_HOST}").rstrip('/')
		timeout = getenv("LLAMA_ARG_TIMEOUT", NOT_GIVEN)
		if timeout != NOT_GIVEN:
			timeout = int(timeout)

		self._ctx = _get_context()
		http_client = AsyncClient(base_url=base_url, timeout=timeout, verify=self._ctx)

		api_key = api_key or "not-needed"
		LLM.__init__(self, model, api_key, **kwargs)
		self.client = AsyncOpenAI(api_key=api_key, base_url=f"{base_url}/v1", timeout=timeout, http_client=http_client)
		self.id = self.convert_alias_to_id()

	@staticmethod
	def available_models(silent_fail: bool = True):
		with Client(base_url=settings.LLAMA_CPP_HOST, verify=_get_context()) as client:
			response = client.get("/v1/models")
			if silent_fail and not response.is_success:
				return ()
			response.raise_for_status()
			models = response.json()["data"]
		return tuple(
			(model["id"], False, model["aliases"][0] if len(model["aliases"]) > 0 else model["id"]) for model in models
		)

	def convert_alias_to_id(self) -> str:
		with Client(base_url=settings.LLAMA_CPP_HOST, verify=self._ctx) as client:
			response = client.get("/v1/models")
			response.raise_for_status()
			models = response.json()["data"]

		for model in models:
			if self.model == model["id"]:
				return model["id"]

			if self.model in set(model["aliases"]):
				return model["id"]

		raise ValueError(f"Could not find ID for alias {self.model}.")

	async def listen_to_events(self, logger, endpoint: Literal["load", "unload"], message_filter: Callable[[dict], bool],
							   timeout: int | float = 120) -> bool:
		"""

		:param logging.Logger logger:
		:param endpoint:
		:param message_filter: A filter that checks if the given server side event is what is needed to stop blocking.
		:return: True if the model has been confirmed as fully loaded, False if the request was succesfully sent but the load status is unknown
		:rtype:
		"""
		timeout = Timeout(5, read=timeout)
		try:
			async with AsyncClient(base_url=settings.LLAMA_CPP_HOST, verify=self._ctx) as client:
				async with client.stream("GET", "/models/sse") as response:
					async with AsyncClient(base_url=settings.LLAMA_CPP_HOST, verify=self._ctx) as client2:
						response2 = await client2.post(f"/models/{endpoint}", json={"model": self.model}, headers={"Content-Type": "application/json"})
						response2.raise_for_status()

					if response.status_code != 200:
						logger.warning(f"Could not wait for Llama's server side events to say when model {self.model} was ready: {response.text}")
						return False

					async for chunk in response.aiter_lines():
						match = SEE_REGEX.search(chunk)
						if not match:
							continue

						data = loads(match.group(1))
						if data["model"] == self.id and data["event"] == "status_change" and message_filter(data):
							return True
		except ReadTimeout as e:
			logger.info(f"Did not receive any new server side events in the last {timeout:,} seconds.", exc_info=e)
			return False

	async def load(self, logger: "logging.Logger"):
		def message_filter(data: dict) -> bool:
			return  data["data"]["status"] == "loaded" or (data["data"]["status"] == "loading" and data["data"]["progress"]["value"] == 1.0)
		return await self.listen_to_events(logger, "load", message_filter)

	async def unload(self, logger: "logging.Logger"):
		def message_filter(data: dict) -> bool:
			return data["data"]["status"] == "unloaded"
		return await self.listen_to_events(logger, "unload", message_filter)

	@staticmethod
	def request_concurrency() -> Optional[int]:
		concurrency = getenv("LLAMA_CPP_SEMAPHORE")
		if concurrency is None:
			return None
		return int(concurrency)
