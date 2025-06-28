# -*- coding: utf-8 -*-
import logging
from abc import ABC, abstractmethod, ABCMeta
from asyncio import sleep as asleep
from enum import StrEnum
from functools import wraps
from json import loads, JSONDecodeError, JSONEncoder
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.llms import HuggingFacePipeline
# from langchain_community.vectorstores import Chroma
from re import sub
from textwrap import dedent
from time import sleep
from typing import Literal, Iterable, Type, Optional


__all__ = ["COMPATIBLE_LLMS", "retry", "async_retry", "LLM", "CustomEncoder"]


COMPATIBLE_LLMS = Literal["gpt-3.5-turbo"]


def retry(*, max_tries=5, delay_seconds=2, logger:logging.Logger = logging.getLogger(__name__)):
	"""
	Retries a function if a failure occurs.
	:param int max_tries: The maximum number of tries the system should attempt before throwing an error.
	:param float delay_seconds: The number of seconds between tries.
	:param logging.Logger logger: The logger to use if an error occurs.
	:return: The returned value from the function.
	"""
	def retry_decorator(func):
		@wraps(func)
		def retry_wrapper(*args, **kwargs):
			tries = 0
			while tries < max_tries:
				try:
					return func(*args, **kwargs)
				except Exception as e:
					wait_time = delay_seconds * (2 ** tries)
					logger.exception(f"Error: {e}. Retrying in {wait_time} seconds...")
					tries += 1
					if tries == max_tries:
						logger.exception("Max retries reached. Skipping this caption.")
						return None
					# raise e
					sleep(wait_time)

		return retry_wrapper
	return retry_decorator


def async_retry(*, max_tries=5, delay_seconds=2, logger:logging.Logger = logging.getLogger(__name__)):
	"""
	Retries a function if a failure occurs.
	:param int max_tries: The maximum number of tries the system should attempt before throwing an error.
	:param float delay_seconds: The number of seconds between tries.
	:param logging.Logger logger: The logger to use if an error occurs.
	:return: The returned value from the function.
	"""
	def retry_decorator(func):
		@wraps(func)
		async def retry_wrapper(*args, **kwargs):
			tries = 0
			while tries < max_tries:
				try:
					return await func(*args, **kwargs)
				except Exception as e:
					wait_time = delay_seconds * (2 ** tries)
					logger.exception(f"Error: {e}. Retrying in {wait_time} seconds...")
					tries += 1
					if tries == max_tries:
						logger.exception("Max retries reached. Skipping this caption.")
						return None
					# raise e
					await asleep(wait_time)

		return retry_wrapper
	return retry_decorator


class LLMMeta(ABCMeta):
	models:dict[str, tuple[Type, bool, Optional[str]]] = dict()

	def __new__(meta_class, name, bases, dct):
		def wrap_function_with_retry(cls, attr):
			func = dct[attr]
			# The first set of parentheses passes the arguments to the decorator,
			# the second set takes in the function that needs to be wrapped
			wrapped = async_retry()(func)
			setattr(cls, attr, wrapped)

		cls = super().__new__(meta_class, name, bases, dct)

		if name == "LLM":
			return cls

		for model, needs_api_key, label in cls.available_models():
			LLMMeta.models[model] = (cls, needs_api_key, label)

		LLM._models = LLMMeta.models

		# wrap_function_with_retry(cls, "separate_captions")
		# wrap_function_with_retry(cls, "get_keywords")

		return cls

	def __call__(cls, *args, **kwargs):
		if cls != LLM:
			return super().__call__(*args, **kwargs)

		model_name = args[0]
		actual_cls, needs_api_key, _ = LLMMeta.models[model_name]
		return actual_cls.__call__(*args, **kwargs)

	def __iter__(cls):
		return iter(LLMMeta.models.items())


class LLM(ABC, metaclass=LLMMeta):
	class ResponseType(StrEnum):
		JSON = "json"
		LIST = "list"

	_models = dict()

	def __init__(self, model:str, api_key:str = None, *args, **kwargs):
		...

	@staticmethod
	def models() -> dict[str, tuple[type["LLM"], bool, str]]:
		"""Returns a dictionary containing each available LLM.
		Each key is the name of the LLM, and the value includes the class that will instantiate the model, if the model needs an API key/password,
		and an optional readable name."""
		return LLM._models

	@staticmethod
	@abstractmethod
	def available_models() -> Iterable[tuple[str, bool, str]]:
		"""Returns a list of tuples describing the available models.
		Each tuple should contain the name of the model and a boolean indicating if it requires an api_key/password (True) or not (False)."""
		...

	@abstractmethod
	async def get_response(self, prompt: list[dict[str, str]], _format:ResponseType = None) -> str:
		...

	async def separate_captions(self, caption: str, max_tries=5) -> dict:
		messages = [
			dict(role="system", content=dedent(f"""\
				Please separate the given full caption into the exact subcaptions. 
				It should be formatted as a syntactically valid Python 
				dictionary with the letter as the key of each subcaption. 
				The dictionary should be able to be loaded in using `json.loads`. 
				If there is no full caption then return an empty dictionary. 
				Do not hallucinate.""")),
			dict(role="user", content=caption)
		]

		tries = 0
		while True:
			output_string = await self.get_response(messages, _format=self.ResponseType.JSON)
			try:
				output_dict = loads(output_string)
				break
			except JSONDecodeError as e:
				logging.exception(f"Error: {e}. Prompting model to fix this issue.")
				if tries == max_tries:
					logging.exception("Max retries reached. Skipping this caption.")
					return dict()

				tries += 1
				messages.extend([
					dict(role="assistant", content=output_string),
					dict(role="user", content=str(e))
				])

		return output_dict

	async def get_keywords(self, caption: str) -> Optional[list[str]]:
		messages = [
			dict(role="system", content=dedent(f"""\
				You are an experienced material scientist. 
				Summarize the text in a less than three keywords separated by comma. 
				The keywords should be a broad and general description of the caption and can be related
				to the materials used, characterization techniques, or any other scientific related keyword. 
				The output should formatted as a JSON object with a key named `keywords` and the value being the array of strings.
				Do not hallucinate or create content that does not exist in the provided text:""")),
			dict(role="user", content=caption)
		]

		tries = 0
		while True:
			output_string = await self.get_response(messages, _format=self.ResponseType.JSON)
			try:
				keywords = loads(output_string)["keywords"]
				return keywords
			except JSONDecodeError as e:
				logging.exception(f"Error: {e}. Prompting model to fix this issue.")
				if tries == max_tries:
					logging.exception("Max retries reached. Skipping this caption.")
					return None

				tries += 1
				messages.extend([
					dict(role="assistant", content=output_string),
					dict(role="user", content=str(e))
				])

	@staticmethod
	def remove_control_characters(string:str) -> str:
		return sub(r"[\x00-\x1F\x7F-\x9F]", "", string)


class CustomEncoder(JSONEncoder):
	def default(self, obj):
		if isinstance(obj, str):
			return obj.encode('utf-8', 'ignore').decode('utf-8')
		return super().default(obj)
