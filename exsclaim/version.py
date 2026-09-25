from __future__ import annotations

import re

version = "2.5.2"
VERSION_REGEX = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(b(?P<beta>\d+))?")


def type_check(other):
	if not isinstance(other, Version):
		raise TypeError(f"exsclaim.Version can only be compared with exsclaim.Version, not {type(other).__name__}.")


class Version:
	def __init__(self, v: str | None = None):
		_version = v or version
		match = VERSION_REGEX.match(_version)
		if match is None:
			raise ValueError(f"Invalid version string: {v}")

		self._version = _version
		self._major = int(match.group("major"))
		self._minor = int(match.group("minor"))
		self._patch = int(match.group("patch"))
		self._beta = int(match.group("beta")) if match.group("beta") else None

	def __repr__(self) -> str:
		return self._version

	def __hash__(self) -> int:
		return hash(self._version)

	@property
	def is_beta(self) -> bool:
		return self._beta is not None

	@property
	def major(self) -> int:
		return self._major

	@property
	def minor(self) -> int:
		return self._minor

	@property
	def patch(self) -> int:
		return self._patch

	@property
	def beta(self) -> int | None:
		return self._beta

	def __lt__(self, other: Version) -> bool:
		type_check(other)
		if self.major > other.major:
			return False

		if self.minor > other.minor:
			return False

		if not self.is_beta and not other.is_beta:
			return self.patch < other.patch

		if self.is_beta and other.is_beta:
			if self.patch > other.patch:
				return False

			return self.beta < other.beta

		if self.is_beta and not other.is_beta:
			if self.patch == other.patch:
				return True
			return self.patch < other.patch

		if not self.is_beta and other.is_beta:
			if self.patch == other.patch:
				return False
			return self.patch < other.patch

		raise ValueError(f"This should never happen when comparing versions {self!r} and {other!r}.")

	def __eq__(self, value: object) -> bool:
		if not isinstance(value, Version):
			return False
		return self.major == value.major and self.minor == value.minor and self.patch == value.patch and self.beta == value.beta

	def __ne__(self, value: object) -> bool:
		return not self == value

	def __le__(self, other: Version) -> bool:
		return self == other or self < other

	def __ge__(self, other: Version) -> bool:
		return not self < other

	def __gt__(self, other: Version) -> bool:
		return not self <= other
