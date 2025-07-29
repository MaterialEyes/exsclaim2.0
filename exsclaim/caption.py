# -*- coding: utf-8 -*-
import logging
import numpy as np

from abc import ABC, abstractmethod, ABCMeta
from asyncio import sleep as asleep
from base64 import b64encode
from functools import wraps
from io import BytesIO
from json import JSONEncoder
from PIL import Image
from pydantic import BaseModel
from re import sub
from textwrap import dedent
from time import sleep
from typing import Literal, Iterable, Type, Optional, Any, TypeVar


__all__ = ["retry", "async_retry", "ChatMessage", "LLM", "CustomEncoder", "Captions", "Keywords", "ResponseBase"]


ResponseBase = TypeVar("ResponseBase", bound=str | BaseModel)


class CaptionEntry(BaseModel):
	label: str
	caption: str


class Captions(BaseModel):
	captions: list[CaptionEntry]


class Keywords(BaseModel):
	keywords: list[str]


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


class ChatMessage:
	def __init__(self, content, role:Literal["user", "assistant", "system", "tool"] = "user", temperature:float = None,
				 images:Iterable[Any] = None):
		self.content = content
		self.role = role
		self.temperature = temperature
		self.images = images

	@property
	def images(self) -> Optional[tuple[str]]:
		"""Returns a list of Base64 encoded images that should be passed to the LLM."""
		return self._images

	@images.setter
	def images(self, images): # :Optional[Iterable[str | np.ndarray | BytesIO |  Image | bytes]]
		"""Sets the list of Base64 encoded images that should be passed to the LLM.
		For each value, if the type is string, the system will assume that it is already base 64 encoded.
		If it's a PIL.Image, np.ndarray, bytes, BytesIO, this will convert it to base 64 encoding.
		No other types are currently allowed.
		"""
		if images is None:
			self._images = None
			return

		new_images = [None] * len(images)

		for i, image in enumerate(images):
			if isinstance(image, str):
				new_images[i] = image
				continue

			# TODO: Check the cases for bytes, Image and np.ndarray
			elif isinstance(image, bytes):
				image = BytesIO(image)
			elif isinstance(image, Image.Image | Image):
				image = BytesIO(image.tobytes())
			elif isinstance(image, np.ndarray):
				image = BytesIO(image.tobytes())

			new_images[i] = b64encode(image.read()).decode("utf-8")

		self._images = tuple(new_images)

	def __repr__(self):
		return f"ChatMessage(role=\"{self.role}\", content=\"{self.content}\", temperature={self.temperature:,}, images={self.images})"

	def __str__(self):
		return repr(self)


class LLMMeta(ABCMeta):
	models:dict[str, tuple[Type, bool, Optional[str]]] = dict()
	unscanned_classes = []

	def __new__(meta_class, name, bases, dct):
		cls = super().__new__(meta_class, name, bases, dct)

		if name != "LLM":
			LLMMeta.unscanned_classes.append(cls)

		return cls

	def __call__(cls, *args, **kwargs):
		if cls != LLM:
			return super().__call__(*args, **kwargs)

		cls.append_llms()

		model_name = args[0]
		actual_cls, needs_api_key, _ = LLMMeta.models[model_name]
		return actual_cls.__call__(*args, **kwargs)

	def __iter__(cls):
		cls.append_llms()
		return iter(LLMMeta.models.items())

	def append_llms(cls):
		for scan_cls in LLMMeta.unscanned_classes:
			for model, needs_api_key, label in scan_cls.available_models():
				LLMMeta.models[model] = (scan_cls, needs_api_key, label)

		LLMMeta.unscanned_classes.clear()
		LLM._models = LLMMeta.models


class LLM(ABC, metaclass=LLMMeta):
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
	def format_messages(self, messages: Iterable[ChatMessage]) -> list[Any]:
		...

	async def load(self):
		"""Does any needed preparation to load the model."""
		...

	async def unload(self):
		"""Does any needed preparation to unload the model."""
		...

	@abstractmethod
	async def get_response(self, prompt: list[ChatMessage], response_format:Type[ResponseBase] = str) -> ResponseBase:
		if response_format != str and not issubclass(response_format, BaseModel):
			raise TypeError("response_format should be None or a subclass of BaseModel.")

	async def separate_captions(self, caption: str) -> dict[str, str]:
		messages = [
			ChatMessage(role="system", content=dedent(f"""\
				Please separate the given full caption into the exact subcaptions. 
				It should be formatted as a syntactically valid Python 
				dictionary with the letter as the key of each subcaption. 
				The dictionary should be able to be loaded in using `json.loads`. 
				If there is no full caption then return an empty dictionary. 
				Do not hallucinate.""")),
			ChatMessage(role="user", content=caption)
		]

		captions = await self.get_response(messages, response_format=Captions)
		captions = {entry.label: entry.caption for entry in captions.captions}
		return captions

	async def get_keywords(self, caption: str) -> tuple[str]:
		messages = [
			ChatMessage(role="system", content=dedent(f"""\
				You are an experienced material scientist. 
				Summarize the text in a less than three keywords separated by comma. 
				The keywords should be a broad and general description of the caption and can be related
				to the materials used, characterization techniques, or any other scientific related keyword. 
				The output should formatted as a JSON object with a key named `keywords` and the value being the array of strings.
				Do not hallucinate or create content that does not exist in the provided text:""")),
			ChatMessage(role="user", content=caption)
		]

		keywords = await self.get_response(messages, response_format=Keywords)
		return tuple(keywords.keywords)

	@classmethod
	def from_search_query(cls, search_query:dict):
		llm = search_query.get("llm", None)
		if llm is None:
			raise ValueError("llm key must be provided to search_query.")
		model_key = search_query.get("model_key", None)
		return LLM(llm, model_key)

	@staticmethod
	def remove_control_characters(string:str) -> str:
		return sub(r"[\x00-\x1F\x7F-\x9F]", "", string)


class CustomEncoder(JSONEncoder):
	def default(self, obj):
		if isinstance(obj, str):
			return obj.encode('utf-8', 'ignore').decode('utf-8')
		return super().default(obj)
