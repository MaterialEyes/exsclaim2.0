version: str
__version__: str
full_version: str

git_revision: str
release: bool
short_version: str


class Version:
	__init__(str)

	__repr__: str
	__hash__: int

	__le__: bool
	__ge__: bool

	__lt__: bool
	__gt__: bool

	__eq__: bool
	__ne__: bool

	is_beta: bool
