from ..caption import LLM, ChatMessage, ResponseBase, LLMOptions, LLMUsage
from ..exceptions import PipelineConfigError

from logging import exception
from os import getenv
from openai.types.shared.chat_model import ChatModel
from pydantic import ValidationError
from typing import get_args, Any, Collection, Literal, Type, Optional

import openai

__all__ = ["OpenAI", "OPEN_AI_LLMs"]


def get_valid_openai_llms():
	models = get_args(ChatModel)
	mask = ["4o" in model for model in models]
	last_model = mask[::-1].index(True)
	valid_models = models[:-last_model]
	llm_literal = Literal[None]
	llm_literal.__args__ = tuple(valid_models)
	return valid_models, llm_literal


valid_models, OPEN_AI_LLMs = get_valid_openai_llms()


class OpenAI(LLM):
	def __init__(self, model: OPEN_AI_LLMs, api_key: str, **kwargs):
		super().__init__(model, api_key, **kwargs)
		api_key = api_key or getenv("OPENAI_API_KEY", None)
		self.client = openai.AsyncOpenAI(api_key=api_key)

	@staticmethod
	def available_models():
		return tuple(
			LLMOptions(model, True, True, model.replace("gpt", "GPT")) for model in valid_models
		)

	@staticmethod
	def check_validity(model: OPEN_AI_LLMS, api_key: str):
		try:
			client = openai.OpenAI(api_key=api_key)
			models = client.models.list().data
			model_ids = set(map(lambda model: model.id, models))
			if model not in model_ids:
				raise PipelineConfigError(f"The model {model} was not found given the API key.", keys=["llm", "model_key"])
		except openai.AuthenticationError as e:
			raise PipelineConfigError(f"An error occurred trying to check if this API key could work with the attempted model {model}.", keys=["llm"]) from e
		except openai.OpenAIError as e:
			raise PipelineConfigError("A general error stopped OpenAI from validating if this API key worked with the given model.", keys=["llm", "model_key"]) from e

	@staticmethod
	def request_concurrency() -> Optional[int]:
		return None

	def format_messages(self, messages: Collection[ChatMessage]) -> list[dict[str, Any]]:
		new_messages = [None] * len(messages)

		for i, message in enumerate(messages):
			formatted_message = dict(role=message.role)

			if message.images is not None:
				content = [dict(type="input_text", text=message.content)]
				content.extend(map(lambda image: dict(type="input_image", image_url=f"data:image/png;base64,{image}"),
								   message.images))
				formatted_message["content"] = content
			else:
				formatted_message["content"] = message.content

			new_messages[i] = formatted_message

		return new_messages

	async def get_response(self, prompt: list[ChatMessage], response_format: Type[ResponseBase] = str) -> tuple[ResponseBase, LLMUsage]:
		await super().get_response(prompt, response_format)

		input_ = self.format_messages(prompt)
		temperatures = tuple(filter(lambda temperature: temperature is not None, map(lambda message: message.temperature, prompt)))
		if len(temperatures) != 0:
			temperature = sum(temperatures) / len(temperatures)
		else:
			temperature = openai.NOT_GIVEN

		try:
			response = await self.client.responses.parse(model=self.model, input=input_, temperature=temperature,
															text_format=response_format if response_format != str else openai.NOT_GIVEN)
			output = response.output_parsed
			usage = LLMUsage(response.usage.input_tokens, response.usage.output_tokens)
			return output, usage
		except openai.BadRequestError as e:
			from json import dumps
			exception(f"Could not parse the response from the LLM when inputs where inputs are:\n{dumps(input_, indent='\t')}", exc_info=e)
			raise e
		except openai.OpenAIError as e:
			exception("An error occurred in OpenAI.", exc_info=e)
			raise e

		try:
			return response_format.model_validate_json(response.output)
		except ValidationError as e:
			exception(f"Error validating to type: {response_format}.")
			raise ValidationError(f"Could not parse the response from the LLM: `{output}`") from e
