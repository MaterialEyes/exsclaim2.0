from dataclasses import dataclass
from typing import Annotated, Collection, Literal, overload

import fastapi
import itertools
import re

__all__ = ["Accept", "AcceptDirective", "AcceptHeader", "BAD_CONTENT_TYPE_EXCEPTION"]


ACCEPT_REGEX = re.compile(r"^(?P<media_type>[^;]+)/(?P<sub_type>[^;]+)(?:;q=(?P<weight>[0-9.]+))?$")


BAD_CONTENT_TYPE_EXCEPTION = fastapi.HTTPException(
	status_code=fastapi.status.HTTP_406_NOT_ACCEPTABLE,
	detail="No acceptable content type found."
)


@dataclass
class AcceptDirective:
	type: str
	sub_type: str
	weight: float = 1.0

	@property
	def media_type(self) -> str:
		return f"{self.type}/{self.sub_type}"

	@classmethod
	def from_string(cls, value) -> "AcceptDirective":
		match = ACCEPT_REGEX.search(value)
		if match is None:
			raise ValueError(f"Could not convert {value!r} in an AcceptDirective.")

		media_type = match.group("media_type")
		sub_type = match.group("sub_type")

		if media_type == "*" and sub_type != "*":
			raise ValueError(f"Type should not be all (*) while subtype is specific {sub_type}.")

		return AcceptDirective(
			type=media_type,
			sub_type=sub_type,
			weight=float(match.group("weight") or 1.0),
		)

	def __repr__(self) -> str:
		representation = f"{self.media_type};q={self.weight}"
		return representation

	def __hash__(self):
		return hash(self.media_type)

	def __eq__(self, value: object, /) -> bool:
		if isinstance(value, AcceptDirective):
			return self.media_type == value.media_type and self.weight == value.weight

		if not isinstance(value, str):
			return False

		if self.media_type == "*/*":
			return True

		return self.media_type == value

	def __contains__(self, item):
		if isinstance(item, str):
			item = AcceptDirective.from_string(item)

		if not isinstance(item, AcceptDirective):
			return False

		if not (self.type == item.type or self.type == "*"):
			return False

		return self.sub_type == item.sub_type or self.sub_type == "*"


class Accept:
	def __init__(self, header: str):
		self._raw_header = header
		options = header.split(',')
		directives: list[AcceptDirective] = [None] * len(options)

		for i, option in enumerate(options):
			try:
				directives[i] = AcceptDirective.from_string(option)
			except ValueError:
				continue

		self._directives = frozenset(directive for directive in directives if directive is not None)
		self._sorted_directives = tuple(sorted(self._directives, key=lambda directive: directive.weight, reverse=True))

	def __contains__(self, item: str | AcceptDirective):
		if not isinstance(item, str | AcceptDirective):
			return False

		if "*/*" in self._directives:
			return True

		return item in self._directives

	def __iter__(self):
		return iter(self._sorted_directives)

	def __len__(self):
		return len(self._sorted_directives)

	@property
	def directives(self) -> tuple[AcceptDirective, ...]:
		return self._sorted_directives

	def get_directive(self, directive: str) -> AcceptDirective:
		if directive not in self:
			raise ValueError(f"Directive '{directive}' not found")

		return self._directives[directive]

	def get_highest_directives(self) -> tuple[float, list[str]]:
		highest_weight = self._sorted_directives[0].weight
		matching_directives = [directive.media_type for directive in self._sorted_directives if directive.weight == highest_weight]

		return highest_weight, matching_directives

	@overload
	def get_best_option(self, potential_options: Collection[str | AcceptDirective], return_none: Literal[False] = False) -> tuple[str, AcceptDirective, float]:
		...

	@overload
	def get_best_option(self, potential_options: Collection[str | AcceptDirective], return_none: Literal[True] = True) -> tuple[str, AcceptDirective, float] | None:
		...

	def get_best_option(self, potential_options: Collection[str | AcceptDirective], return_none: bool = False):
		"""
		Given a collection of options, finds the best option based on the weights given in the Accept header, and returns that option.
		:param typing.Collection[str | AcceptDirective] potential_options: The content types the server can return.
		:param bool return_none: Whether to return None if no option is found (True) or to raise a fastapi.HTTPException (False).
		:return: The best option given, the directive that matched it, and the weight of the directive.
		"""
		options = [None] * (len(potential_options) * len(self._sorted_directives))
		for i, (directive, option) in enumerate(itertools.product(self._sorted_directives, potential_options)):
			if option not in directive:
				continue
			options[i] = (directive.weight, directive, option)

		ordered_options = sorted(
			filter(lambda option: option is not None, options),
			key=lambda option: option[0],
			reverse=True
		)

		if len(ordered_options) == 0:
			if return_none:
				return None
			raise BAD_CONTENT_TYPE_EXCEPTION

		best_option = ordered_options[0]
		return best_option[2], best_option[1], best_option[0]


def get_accepted_types(accept: str = fastapi.Header(...)) -> Accept:
	if not accept:
		return Accept("*/*")
	return Accept(accept)


AcceptHeader = Annotated[Accept, fastapi.Depends(get_accepted_types)]
