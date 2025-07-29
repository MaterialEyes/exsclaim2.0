from ..caption import LLM, ChatMessage, ResponseBase

from logging import exception, error
from os import getenv
from openai import AsyncOpenAI, OpenAIError, NOT_GIVEN
from openai.types.responses import ResponseOutputMessage, ResponseFunctionToolCall, ParsedResponseOutputMessage
from openai.types.shared.chat_model import ChatModel as OpenAILLMs
from pydantic import BaseModel, ValidationError
from typing import get_args, Iterable, Any, Type

__all__ = ["OpenAI", "OpenAILLMs"]


class OpenAI(LLM):
	def __init__(self, model:OpenAILLMs, api_key:str = None, **kwargs):
		super().__init__(model, api_key, **kwargs)
		self.model = model
		api_key = api_key or getenv("OPENAI_API_KEY", None)
		self.client = AsyncOpenAI(api_key=api_key)

	@staticmethod
	def available_models():
		return tuple(
			(model, True, model.replace("gpt", "GPT")) for model in get_args(OpenAILLMs)
		)

	def format_messages(self, messages: Iterable[ChatMessage]) -> list[dict[str, Any]]:
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
	def create_tool_from_model(response_format:Type[BaseModel]) -> dict:
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

	async def get_response(self, prompt: list[ChatMessage], response_format:Type[ResponseBase] = str) -> ResponseBase:
		await super().get_response(prompt, response_format)

		input_ = self.format_messages(prompt)
		temperatures = tuple(filter(lambda temperature: temperature is not None, map(lambda message: message.temperature, prompt)))
		if len(temperatures) != 0:
			temperature = sum(temperatures) / len(temperatures)
		else:
			temperature = NOT_GIVEN

		try:
			completion = await self.client.responses.parse(model=self.model, input=input_, temperature=temperature,
															text_format=response_format if response_format != str else NOT_GIVEN)

			response = completion.output[0]
		except OpenAIError as e:
			exception("An error occurred in OpenAI.")
			raise e

		if response_format == str:
			return response.content[0].text
		elif isinstance(response, ParsedResponseOutputMessage):
			return response.content[0].parsed
		elif isinstance(response, ResponseFunctionToolCall):
			output = response.arguments
		elif isinstance(response, ResponseOutputMessage):
			output = response.text
			error(f"Response type: ResponseOutputMessage. {output=}")
		else:
			raise TypeError(f"An unknown response type was received from OpenAI. Received type: {response.__class__.__name__}.")

		try:
			return response_format.model_validate_json(output)
		except ValidationError as e:
			exception(f"Error validating to type: {response_format}.")
			raise e
