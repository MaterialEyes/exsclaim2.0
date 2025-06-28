from ..caption import LLM
from logging import warning
from ollama import AsyncClient, list as model_list, ChatResponse, ResponseError
from re import compile

__all__ = ["Ollama"]


class Ollama(LLM):
	def __init__(self, model, api_key:str = None, **kwargs):
		super().__init__(model, api_key, **kwargs)
		self.model = model
		self.client = AsyncClient()

	@staticmethod
	def available_models(silent_fail:bool = True):
		try:
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

		tag_regex = compile(r"^([\w.]+):.+$")	# Removes the tag from the model name
		space_regex = compile(r"([a-z])(\d)]")	# Adds a space when necessary

		models = tuple({tag_regex.search(model.model).group(1) for model in models})
		labels = (space_regex.sub(r"\1 \2", model) for model in models)

		return tuple((model, False, label) for model, label in zip(models, labels))

	async def get_response(self, prompt:list[dict[str, str]], _format:LLM.ResponseType = None) -> str:
		response:ChatResponse = await self.client.chat(model=self.model, messages=prompt,
													   format="json")

		output_string = response.message.content

		# Replace single quotes with double quotes to make the string valid JSON
		output_string = output_string.replace("\\", "\\\\").replace("'", "\"")

		if _format is not None and _format != self.ResponseType.JSON:
			...

		return self.remove_control_characters(output_string)

