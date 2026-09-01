# -*- coding: utf-8 -*-
from .exceptions import ExsclaimToolException

from abc import ABC, abstractmethod, ABCMeta
from asyncio import Semaphore
from base64 import b64encode
from dataclasses import dataclass
from io import BytesIO
from json import dumps
from logging import Logger
from PIL import Image
from pydantic import BaseModel, Field
from pydantic_core import ValidationError
from re import sub
from textwrap import dedent
from typing import Literal, Iterable, Type, Optional, Any, TypeVar, Self, Collection, NamedTuple
from uuid import UUID

import numpy as np


__all__ = ["ChatMessage", "LLMOptions", "LLMMeta", "LLMUsage", "LLM", "CaptionEntry", "Captions", "Keywords", "ResponseBase", "OptionalSemaphore"]


ResponseBase = TypeVar("ResponseBase", bound=str | BaseModel)


class CaptionEntry(BaseModel):
	label: str = Field(..., description="The caption label.")
	caption: str


class Captions(BaseModel):
	captions: list[CaptionEntry]


class Keywords(BaseModel):
	keywords: list[str]


class CaptionInfo(BaseModel):
	captions: list[CaptionEntry]
	keywords: list[str]


class ChatMessage:
	def __init__(self, content: str, role: Literal["user", "assistant", "system", "tool"] = "user",
				 temperature: Optional[float] = None, images: Optional[Collection[Any]] = None):
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


class LLMOptions(NamedTuple):
	id: str
	allows_api_key: bool
	requires_api_key: bool
	display_name: str


class LLMMeta(ABCMeta):
	models: dict[str, tuple[Type, bool, bool, Optional[str]]] = dict()
	unscanned_classes = []
	classes = set()

	def __new__(meta_class, name, bases, dct):
		cls = super().__new__(meta_class, name, bases, dct)

		if name != "LLM":
			LLMMeta.unscanned_classes.append(cls)
			LLMMeta.classes.add(cls)

		return cls

	def __call__(cls, *args, **kwargs):
		if cls != LLM:
			return super().__call__(*args, **kwargs)

		cls.append_llms()

		model_name = args[0]
		try:
			actual_cls, *_ = LLMMeta.models[model_name]
		except KeyError as e:
			raise ExsclaimToolException(f"{model_name} is not an available model.") from e
		return actual_cls.__call__(*args, **kwargs)

	def __iter__(cls):
		cls.append_llms()
		return iter(LLMMeta.models.items())

	def append_llms(cls):
		for scan_cls in LLMMeta.unscanned_classes:
			for model, allows_api_key, needs_api_key, label in scan_cls.available_models():
				LLMMeta.models[model] = (scan_cls, allows_api_key, needs_api_key, label)

		LLMMeta.unscanned_classes.clear()
		LLM._models = LLMMeta.models


@dataclass
class LLMUsage:
	input_tokens: Optional[int]
	output_tokens: Optional[int]


class OptionalSemaphore(Semaphore):
	def __init__(self, value: Optional[int] = None):
		self._is_valid_value = value is not None and value > 0
		if self._is_valid_value:
			super().__init__(value)

	async def __aenter__(self):
		if self._is_valid_value:
			await super().__aenter__()

	async def __aexit__(self, *args, **kwargs):
		if self._is_valid_value:
			await super().__aexit__(*args, **kwargs)


class LLM(ABC, metaclass=LLMMeta):
	_models = dict()
	_classes = set()

	def __init__(self, model: str, api_key: str = None, *args, **kwargs):
		self.model = model

	@staticmethod
	def models() -> dict[str, tuple[type["LLM"], bool, bool, str]]:
		"""Returns a dictionary containing each available LLM.
		Each key is the name of the LLM, and the value includes the class that will instantiate the model, if the model needs an API key/password,
		and an optional readable name."""
		return LLM._models

	@staticmethod
	@abstractmethod
	def available_models() -> Iterable[LLMOptions]:
		"""Returns a list of tuples describing the available models.
		Each tuple should contain the name of the model and a boolean indicating if it requires an api_key/password (True) or not (False)."""
		...

	@staticmethod
	@abstractmethod
	def check_validity(model: str, api_key: Optional[str]): ...

	@staticmethod
	@abstractmethod
	def request_concurrency() -> Optional[int]:
		"""
		Returns: the number of requests that can be sent at once. -1 if there is no limit.
		"""
		...

	@abstractmethod
	def format_messages(self, messages: Collection[ChatMessage]) -> list[Any]:
		...

	async def __aenter__(self) -> Self:
		await self.load()
		return self

	async def __aexit__(self, *args, **kwargs):
		await self.unload()

	async def load(self, logger: Optional[Logger] = None, num_captions: Optional[int] = None) -> bool:
		"""Does any needed preparation to load the model."""
		return True

	async def unload(self, logger: Optional[Logger] = None):
		"""Does any needed preparation to unload the model."""
		...

	@abstractmethod
	async def get_response(self, prompt: list[ChatMessage], response_format: Type[ResponseBase] = str) -> tuple[ResponseBase, LLMUsage]:
		if response_format != str and not issubclass(response_format, BaseModel):
			raise TypeError("response_format should be str or a subclass of BaseModel.")

	async def parse_captions(self, caption: str) -> tuple[dict[str, str], list[str], LLMUsage]:
		messages = [
			ChatMessage(role="system", content=(
				"You are an experienced material scientist. " 
				"Please parse the given caption with the response only containing a valid JSON object that can be plugging into Pydantic's BaseModel.model_validation_json. " 
				"Do not add any markdown wrappers or code blocks, only the raw JSON object. " 
				"The `keywords` key should hold a list of three to five (3-5) broad and general description of the caption and can be related to the materials used, characterization techniques, or any other scientific related keyword. " 
				"The `captions` key should be a list of objects, where each object holds the letter sublabel in the `label` key and the parsed subcaption in the `caption` key. " 
				"Please include any HTML tags from the full caption in the separated caption values. " 
				"Remove as little content as possible when splitting the subcaptions, and having duplicated content across labels is okay. " 
				"If there is no full caption then return an object with `keywords` and `captions` being empty lists. " 
				"Do not hallucinate or create content that does not exist in the provided text."
			)),
			ChatMessage(role="user", content=caption)
		]

		while True:
			try:
				info, usage = await self.get_response(messages, response_format=CaptionInfo)
				break
			except ValidationError as error:
				messages.append(ChatMessage(role="user", content=f"Your previous response could not be parsed: {dumps(error.errors())}"))

		captions = {entry.label: entry.caption for entry in info.captions}
		return captions, info.keywords[:5], usage # TODO: Make sure the keywords are unique

	# TODO: Add deprecations to these methods
	async def separate_captions(self, caption: str) -> dict[str, str]:
		messages = [
			ChatMessage(role="system", content=dedent(f"""\
				Please separate the given full caption into the exact subcaptions. 
				Duplicating content across keys is okay. 
				If there is no full caption then return a list with an empty dictionary. 
				Do not hallucinate or create content that does not exist in the provided text.""")),
			ChatMessage(role="user", content=caption)
		]

		captions = await self.get_response(messages, response_format=Captions)
		captions = {entry.label: entry.caption for entry in captions.captions}
		return captions

	async def get_keywords(self, caption: str) -> tuple[str, ...]:
		messages = [
			ChatMessage(role="system", content=dedent(f"""\
				You are an experienced material scientist. 
				Summarize the text in a less than three keywords separated by comma. 
				Do not hallucinate or create content that does not exist in the provided text:""")),
			ChatMessage(role="user", content=caption)
		]

		keywords = await self.get_response(messages, response_format=Keywords)
		return tuple(keywords.keywords)

	@staticmethod
	def get_info_from_search_query(search_query: dict[str, Any]) -> tuple[str, Optional[str]]:
		llm = search_query.get("llm", None)
		if llm is None:
			raise ValueError("llm key must be provided to search_query.")
		model_key = search_query.get("model_key", None)
		return llm, model_key

	@classmethod
	def from_search_query(cls, search_query: dict, run_id: Optional[UUID] = None):
		llm, model_key = cls.get_info_from_search_query(search_query)
		return cls(llm, model_key, run_id=run_id)

	@classmethod
	def validate_search_query(cls, search_query: dict):
		llm, model_key = cls.get_info_from_search_query(search_query)
		cls.check_validity(llm, model_key)

	@staticmethod
	def remove_control_characters(string: str) -> str:
		return sub(r"[\x00-\x1F\x7F-\x9F]", "", string)
