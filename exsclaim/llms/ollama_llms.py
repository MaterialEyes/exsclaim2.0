from ..caption import LLM, LLMOptions, ChatMessage, ResponseBase, LLMUsage
from ..config import settings

from logging import warning, exception
from ollama import AsyncClient, Client, ChatResponse, ResponseError
from pydantic import ValidationError
from re import compile
from typing import Any, Type, Self, Collection, Optional

__all__ = ["Ollama"]


class Ollama(LLM):
	__slots__ = ("model", "client")

	def __init__(self, model, api_key: str = None, **kwargs):
		super().__init__(model, api_key, **kwargs)
		self.client = AsyncClient(host=settings.OLLAMA_HOST)

	@staticmethod
	def available_models(silent_fail: bool = True):
		try:
			client = Client(host=settings.OLLAMA_HOST)
			models = client.list().models
		except (ConnectionError, ResponseError) as e:
			if silent_fail:
				warning(f"Could not connect to Ollama. This may cause issues down the line if Ollama-based LLMs are required.", exc_info=e)
				return tuple()
			raise e

		tag_regex = compile(r"^([\w.-]+):.+$")	# Removes the tag from the model name
		space_regex = compile(r"([a-z])(\d)]")	# Adds a space when necessary

		models = tuple({tag_regex.search(model.model).group(1) for model in models})
		labels = (space_regex.sub(r"\1 \2", model) for model in models)

		return tuple(LLMOptions(model, False, False, label.title()) for model, label in zip(models, labels))

	@staticmethod
	def request_concurrency() -> Optional[int]:
		from os import getenv

		different_models = int(getenv("OLLAMA_MAX_LOADED_MODELS", '1'))
		num_parallel_requests = int(getenv("OLLAMA_NUM_PARALLEL", '1'))
		return different_models * num_parallel_requests

	async def load(self, logger: Optional[logging.Logger] = None, num_captions: Optional[int] = None) -> Self:
		await self.client.generate(model=self.model)
		if logger is not None:
			logger.info(f"Loaded {self.model}.")
		return self

	async def unload(self, logger: Optional[logging.Logger] = None):
		await self.client.generate(model=self.model, keep_alive=0)
		if logger is not None:
			logger.info(f"Unloaded {self.model}.")

	def format_messages(self, messages: Collection[ChatMessage]) -> list[dict[str, Any]]:
		new_messages = [None] * len(messages)

		for i, message in enumerate(messages):
			formatted_message = dict(
				content=message.content,
				role=message.role
			)

			if message.temperature is not None:
				formatted_message["options"] = dict(temperature=message.temperature)

			if message.images is not None:
				formatted_message["images"] = list(message.images)

			new_messages[i] = formatted_message

		return new_messages

	async def get_response(self, prompt: list[ChatMessage], response_format: Type[ResponseBase] = str):
		await super().get_response(prompt, response_format)

		_format = response_format.model_json_schema() if response_format != str else None
		messages = self.format_messages(prompt)

		response: ChatResponse = await self.client.chat(model=self.model, messages=messages, format=_format)

		output_string = response.message.content
		usage = LLMUsage(None, None)

		if response_format == str:
			return output_string, usage

		try:
			return response_format.model_validate_json(output_string), usage
		except ValidationError as e:
			exception(f"Error validating to type: {response_format}.", exc_info=e)
			raise e
