# from ..caption import LLM, ChatMessage, ResponseBase
from .openai_llms import OpenAI, OPEN_AI_LLMs, NOT_GIVEN
from ..config import settings

from httpx import Client, AsyncClient
from os import getenv

__all__ = ["LlamaCPP"]


class LlamaCPP(OpenAI):
	def __init__(self, model: OPEN_AI_LLMs, api_key: str = "not-needed", **kwargs):
		from os import getenv
		kwargs.setdefault("base_url", f"{settings.LLAMA_CPP_HOST}/v1")
		timeout = getenv("LLAMA_ARG_TIMEOUT", NOT_GIVEN)
		if timeout != NOT_GIVEN:
			timeout = int(timeout)
		kwargs.setdefault("timeout", timeout)
		api_key = api_key or "not-needed"
		super().__init__(model, api_key, **kwargs)

	@staticmethod
	def available_models(silent_fail: bool = True):
		with Client(base_url=settings.LLAMA_CPP_HOST) as client:
			response = client.get("/v1/models")
			if silent_fail and not response.is_success:
				return ()
			response.raise_for_status()
			models = response.json()["data"]
		return tuple(
			(model["id"], False, model["aliases"][0] if len(model["aliases"]) > 0 else model["id"]) for model in models
		)

	async def load(self):
		async with AsyncClient(base_url=settings.LLAMA_CPP_HOST) as client:
			await client.post("/models/load", json={"model": self.model}, headers={"Content-Type": "application/json"})

	async def unload(self):
		async with AsyncClient(base_url=settings.LLAMA_CPP_HOST) as client:
			await client.post("/models/unload", json={"model": self.model}, headers={"Content-Type": "application/json"})

	@staticmethod
	def request_concurrency() -> Optional[int]:
		concurrency = getenv("LLAMA_CPP_SEMAPHORE")
		if concurrency is None:
			return None
		return int(concurrency)
