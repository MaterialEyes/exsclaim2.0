from ..caption import LLM

from os import getenv
from openai import AsyncOpenAI
from openai.types.shared.chat_model import ChatModel as OpenAILLMs
from typing import get_args

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

	async def get_response(self, prompt:str, _format:LLM.ResponseType = None) -> str:
		# https://platform.openai.com/docs/guides/structured-outputs?api-mode=responses#supported-schemas
		match _format:
			case LLM.ResponseType.LIST:
				output_structure = "Array"
			case LLM.ResponseType.JSON:
				output_structure = "Object"
			case _:
				output_structure = "String"

		completion = await self.client.chat.completions.create(
			model=self.model,
			messages=[{"role": "assistant", "content": prompt}],
			temperature=0,
			response_format=output_structure
		)

		output_string = completion.choices[0].message.content.strip()

		# Replace single quotes with double quotes to make the string valid JSON
		output_string = output_string.replace("\\", "\\\\").replace("'", "\"")
		return self.remove_control_characters(output_string)
