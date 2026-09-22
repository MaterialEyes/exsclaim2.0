from .caption import LLM, ChatMessage, ResponseBase, LLMOptions, LLMUsage
from ..exceptions import PipelineConfigError

from logging import exception
from typing import Any, Collection, Type, Optional

import anthropic
import asyncio


class Anthropic(LLM):
	def __init__(self, model: str, api_key: str, max_tokens: Optional[int] = None, **kwargs):
		super().__init__(model, api_key, **kwargs)
		self.client = anthropic.AsyncAnthropic(api_key=api_key)
		self.max_tokens = max_tokens or 1_024

	@staticmethod
	def available_models(): # Unfortunately, Anthropic's API requires an API key to list models
		cached_models = (
			LLMOptions('claude-opus-5-5', True, True, 'Claude Opus 5.5'),
			LLMOptions('claude-fable-5-1', True, True, 'Claude Fable 5.1'),
			LLMOptions('claude-opus-5', True, True, 'Claude Opus 5'),
			LLMOptions('claude-sonnet-5', True, True, 'Claude Sonnet 5'),
			LLMOptions('claude-fable-5', True, True, 'Claude Fable 5'),
			LLMOptions('claude-opus-4-8', True, True, 'Claude Opus 4.8'),
			LLMOptions('claude-opus-4-7', True, True, 'Claude Opus 4.7'),
			LLMOptions('claude-sonnet-4-6', True, True, 'Claude Sonnet 4.6'),
			LLMOptions('claude-opus-4-6', True, True, 'Claude Opus 4.6'),
			LLMOptions('claude-opus-4-5-20251101', True, True, 'Claude Opus 4.5'),
			LLMOptions('claude-haiku-4-5-20251001', True, True, 'Claude Haiku 4.5'),
			LLMOptions('claude-sonnet-4-5-20250929', True, True, 'Claude Sonnet 4.5')
		)
		return cached_models

	@staticmethod
	def check_validity(model: str, api_key: str):
		try:
			client = anthropic.Anthropic(api_key=api_key)
			models = client.models.list().data
			model_ids = {model.id for model in models}
			if model not in model_ids:
				raise PipelineConfigError(f"The model {model} was not found given the API key.", keys=["llm", "model_key"])

			has_structured_outputs = {model.id: model.capabilities.structured_outputs.supported for model in models}
			if not has_structured_outputs[model]:
				raise PipelineConfigError(f"The model {model} does not allow structured outputs.", keys=["llm"])

		except anthropic.AuthenticationError as e:
			raise PipelineConfigError(f"An error occurred trying to check if this API key could work with the attempted model {model}.", keys=["llm"]) from e
		except anthropic.AnthropicError as e:
			raise PipelineConfigError("A general error stopped OpenAI from validating if this API key worked with the given model.", keys=["llm", "model_key"]) from e

	@staticmethod
	def request_concurrency() -> Optional[int]:
		return None

	def format_messages(self, messages: Collection[ChatMessage]) -> list[dict[str, Any]]:
		new_messages: list[anthropic.types.MessageParam] = [None] * len(messages)

		cache = anthropic.types.CacheControlEphemeralParam(type="ephemeral")
		for i, message in enumerate(messages):
			use_cache = cache if message.cache else None
			if message.images is not None:
				content = [anthropic.types.TextBlockParam(type="text", text=message.content, cache_control=use_cache)]
				content.extend([
					anthropic.types.ImageBlockParam(type="image", source=f"data:image/png;base64,{image}")
					for image in message.images
				])

				formatted_message = anthropic.types.MessageParam(content=content, role=message.role)
			else:
				formatted_message = anthropic.types.MessageParam(
					content=[anthropic.types.TextBlockParam(type="text", text=message.content, cache_control=use_cache)],
					role=message.role
				)

			new_messages[i] = formatted_message

		return new_messages

	async def get_response(self, prompt: list[ChatMessage], response_format: Type[ResponseBase] = str,
						   rate_limit_wait: int = 10) -> tuple[ResponseBase, LLMUsage]:
		await super().get_response(prompt, response_format)

		input_ = self.format_messages(prompt)
		first_message = input_[0]
		if first_message["role"] == "system":
			input_ = input_[1:]
			system = first_message["content"]
		else:
			system = anthropic.omit

		try:
			response = await self.client.messages.parse(
				model=self.model,
				messages=input_,
				max_tokens=self.max_tokens,
				system=system,
				output_format=response_format if response_format != str else anthropic.not_given
			)

			usage = LLMUsage(response.usage.input_tokens, response.usage.output_tokens)
			if (output := response.parsed_output) is None:
				output = response.content[0].text

			return output, usage
		except anthropic.RateLimitError:
			# Wait 10 seconds before retrying, and increase the wait time by 5 seconds each time the rate limit is hit
			await asyncio.sleep(rate_limit_wait)
			return await self.get_response(prompt, response_format, rate_limit_wait + 5)
		except anthropic.BadRequestError as e:
			from json import dumps
			exception(f"Could not parse the response from the LLM when inputs where inputs are:\n{dumps(input_, indent='\t')}", exc_info=e)
			raise e
		except anthropic.AnthropicError as e:
			exception("An error occurred in OpenAI.", exc_info=e)
			raise e
