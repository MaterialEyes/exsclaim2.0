__all__ = ["SubfigureBoundary", "SubfigureInfo", "ScalebarInfo"]


from typing import Any, NamedTuple


class SubfigureBoundary(NamedTuple):
	x1: int
	y1: int
	x2: int
	y2: int
	confidence: str


class SubfigureInfo(NamedTuple):
	label: int
	x1: float
	y1: float
	width: float
	height: float


class ScalebarInfo(NamedTuple):
	x1: Any
	y1: Any
	x2: Any
	y2: Any
	confidence: Any
	label: Any
