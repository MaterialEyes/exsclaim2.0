from ..caption import LLM, ChatMessage, ResponseBase
from logging import warning, exception, info
from ollama import AsyncClient, ChatResponse, ResponseError
from pydantic import ValidationError
from re import compile
from typing import Any, Type, Iterable

__all__ = ["Ollama"]


class Ollama(LLM):
	__slots__ = ("model", "client")

	def __init__(self, model, api_key:str = None, **kwargs):
		super().__init__(model, api_key, **kwargs)
		self.model = model
		self.client = AsyncClient()

	@staticmethod
	def available_models(silent_fail:bool = True):
		try:
			from ollama import list as model_list
			models = model_list()["models"]
		except ConnectionError as e:
			if silent_fail:
				warning(f"Could not connect to Ollama. This may cause issues down the line if Ollama-based LLMs are required.")
				return tuple()
			raise e
		except ResponseError as e:
			if silent_fail:
				warning(f"Could not connect to Ollama. This may cause issues down the line if Ollama-based LLMs are required.")
				return tuple()
			raise e

		tag_regex = compile(r"^([\w.-]+):.+$")	# Removes the tag from the model name
		space_regex = compile(r"([a-z])(\d)]")	# Adds a space when necessary

		models = tuple({tag_regex.search(model.model).group(1) for model in models})
		labels = (space_regex.sub(r"\1 \2", model) for model in models)

		return tuple((model, False, label.title()) for model, label in zip(models, labels))

	async def load(self):
		await self.client.generate(model=self.model)
		info(f"Loaded {self.model}.")

	async def unload(self):
		await self.client.generate(model=self.model, keep_alive=0)
		info(f"Unloaded {self.model}.")

	def format_messages(self, messages: Iterable[ChatMessage]) -> list[dict[str, Any]]:
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

	async def get_response(self, prompt:list[ChatMessage], response_format:Type[ResponseBase] = str) -> ResponseBase:
		await super().get_response(prompt, response_format)

		_format = response_format.model_json_schema() if response_format != str else None
		messages = self.format_messages(prompt)

		response:ChatResponse = await self.client.chat(model=self.model, messages=messages, format=_format)

		output_string = response.message.content

		if response_format == str:
			return output_string

		try:
			return response_format.model_validate_json(output_string)
		except ValidationError as e:
			exception(f"Error validating to type: {response_format}.")
			raise e
