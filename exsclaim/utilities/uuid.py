__all__ = ["gen_uuid7"]


def gen_uuid7() -> UUID:
	from sys import version_info
	if version_info >= (3, 14):
		from uuid import uuid7
		return uuid7()

	from uuid_utils import uuid7
	return UUID(str(uuid7()))
