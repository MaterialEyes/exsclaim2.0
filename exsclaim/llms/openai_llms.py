from ..caption import LLM, ChatMessage, ResponseBase, LLMOptions, LLMUsage

from logging import exception, error
from os import getenv
from openai import AsyncOpenAI, OpenAIError, NOT_GIVEN, BadRequestError
from openai.types.responses import ResponseOutputMessage, ResponseFunctionToolCall, ParsedResponseOutputMessage
from openai.types.shared.chat_model import ChatModel as OPEN_AI_LLMs
from pydantic import BaseModel, ValidationError
from typing import get_args, Any, Type, Optional, Collection

__all__ = ["OpenAI", "OPEN_AI_LLMs"]


class OpenAI(LLM):
	def __init__(self, model: OPEN_AI_LLMs, api_key: str, timeout=NOT_GIVEN, **kwargs):
		super().__init__(model, api_key, **kwargs)
		api_key = api_key or getenv("OPENAI_API_KEY", None)
		self.client = AsyncOpenAI(api_key=api_key)

	@staticmethod
	def available_models():
		return tuple(
			LLMOptions(model, True, True, model.replace("gpt", "GPT")) for model in get_args(OPEN_AI_LLMs)
		)

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

	@staticmethod
	def create_tool_from_model(response_format: Type[BaseModel]) -> dict:
		def clean(schema):
			if isinstance(schema, dict):
				return {
					k: clean(v)
					for k, v, in schema.items()
					if k in {"type", "properties", "items", "required", "enum", "format", "additionalProperties"}
				}
			elif isinstance(schema, list):
				return list(map(clean, schema))
			return schema

		parameters = response_format.model_json_schema()
		parameters["additionalProperties"] = False

		return dict(
			# type="function",
			name=response_format.__name__[:64],
			description=f"Get the {response_format.__name__}.",
			strict=True,
			parameters=parameters,
		)

	async def get_response(self, prompt: list[ChatMessage], response_format: Type[ResponseBase] = str) -> tuple[ResponseBase, LLMUsage]:
		await super().get_response(prompt, response_format)

		input_ = self.format_messages(prompt)
		temperatures = tuple(filter(lambda temperature: temperature is not None, map(lambda message: message.temperature, prompt)))
		if len(temperatures) != 0:
			temperature = sum(temperatures) / len(temperatures)
		else:
			temperature = NOT_GIVEN

		try:
			response = await self.client.responses.parse(model=self.model, input=input_, temperature=temperature,
															text_format=response_format if response_format != str else NOT_GIVEN)
			output = response.output_parsed
			usage = LLMUsage(response.usage.input_tokens, response.usage.output_tokens)
			return output, usage
		except BadRequestError as e:
			from json import dumps
			exception(f"Could not parse the response from the LLM when inputs where inputs are:\n{dumps(input_, indent='\t')}", exc_info=e)
			raise e
		except OpenAIError as e:
			exception("An error occurred in OpenAI.", exc_info=e)
			raise e

		try:
			return response_format.model_validate_json(output)
		except ValidationError as e:
			exception(f"Error validating to type: {response_format}.")
			raise ValidationError(f"Could not parse the response from the LLM: `{output}`") from e
