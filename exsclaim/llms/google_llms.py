from .caption import LLM, LLMOptions, ChatMessage, ResponseBase, LLMUsage
from ..exceptions import PipelineConfigError, LLMException

import logging

from google import genai
from google.genai._gaos import types
from typing import Optional, Type, Collection, Iterable

__all__ = ["Google"]


class Google(LLM):
	def __init__(self, model: str, api_key: str):
		super().__init__(model, api_key, **kwargs)
		self.client = genai.Client(api_key=api_key).aio

	@staticmethod
	def _api_key_needed_for_list() -> bool:
		return True

	async def load(self, logger: Optional[logging.Logger] = None, num_captions: Optional[int] = None):
		...

	async def unload(self, logger: Optional[logging.Logger] = None):
		await self.client.close()

	@staticmethod
	def available_models(api_key: Optional[str] = None, silent_fail: bool = False) -> Iterable[LLMOptions]:
		if api_key is None:
			raise LLMException("An API key is required to list Gemini's models.")

		client = genai.Client(api_key=api_key)
		models = client.models.list(config={"page_size": 100}).page
		models_list: list[LLMOptions] = [None] * len(models)

		for i, model in enumerate(models):
			if model.name is None:
				continue

			name = model.name.replace("models/", "")
			display_name = model.display_name or name
			models_list[i] = LLMOptions(name, True, True, display_name)

		return models_list

	@staticmethod
	def check_validity(model: str, api_key: str):
		try:
			client = genai.Client(api_key=api_key)
			client.models.get(model=model)
		except genai.errors.ClientError as e:
			match e.status:
				case "UNAUTHENTICATED":
					raise PipelineConfigError(e.message, keys=["model_key"]) from e
				case "NOT_FOUND":
					raise PipelineConfigError(e.message, keys=["llm", "model_key"]) from e
				case _:
					raise PipelineConfigError(e.message, keys=["llm"]) from e

	@staticmethod
	def request_concurrency() -> Optional[int]:
		return None

	def format_messages(self, messages: Collection[ChatMessage]) -> list[types.interactions.Content]:
		new_messages: list[types.interactions.Content] = [None]

		for i, message in enumerate(messages):
			if message.images is not None:
				formatted_message = types.interactions.ImageContent(
					data=message.images[0],
					type="image"
				)
			else:
				formatted_message = types.interactions.TextContent(text=message.content, type="text")

			new_messages[i] = formatted_message

		return new_messages

	async def get_response(self, prompt: list[ChatMessage], response_format: Type[ResponseBase] = str) -> tuple[ResponseBase, LLMUsage]:
		if response_format == str:
			interaction_format = types.interactions.ResponseFormatParam(
				mime_type="text/plain",
				type="text"
			)
		else:
			interaction_format = types.interactions.ResponseFormatParam(
				mime_type="application/json",
				schema_=response_format.model_json_schema(),
				type="text"
			)

		_input = self.format_messages(prompt)

		response = await self.client.interactions.create(
			model=self.model,
			input=prompt,
			response_format=interaction_format,
		)

		usage = LLMUsage(
			input_tokens=response.total_input_tokens,
			output_tokens=response.total_output_tokens
		)

		formatted_response = response.output_text
		if formatted_response is None:
			raise ValueError(f"Gemini response is None.")

		if response_format != str:
			formatted_response = response_format.model_validate_json(formatted_response)

		return formatted_response, usage
