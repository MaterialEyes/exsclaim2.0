from pydantic import Field
from typing import Annotated, Union, Optional

from .v0 import OutputV0
from .v1 import OutputV1, migrate_v0_to_v1

__all__ = ["Output", "CurrentStructure", "VERSION_REGISTRY", "model_validate", "migrate"]


Output = Annotated[
	Union[OutputV0, OutputV1],
	Field(discriminator="version")
]

CurrentStructure = OutputV1

VERSION_REGISTRY: dict[Optional[int], type[Output]] = {
	None: OutputV0,
	1: OutputV1,
}


def model_validate(json: dict) -> Output:
	version = json.get("version", None)
	if version not in VERSION_REGISTRY:
		raise ValueError(f"Invalid results version: {version}.")
	return VERSION_REGISTRY[version].model_validate(json)


def migrate(json: dict | Output) -> CurrentStructure:
	if isinstance(json, dict):
		json = model_validate(json)

	if isinstance(json, OutputV0):
		json = migrate_v0_to_v1(json)

	return json


# MigrationList: dict[type[Output], Callable[[Output], Output]] = {
# 	OutputV0: migrate_v0_to_v1
# }


# def migrate(json: Output) -> CurrentStructure:
# 	if isinstance(json, CurrentStructure):
# 		return json
#
# 	migrations = iter(MigrationList.items())
# 	while (migration := next(migrations, None)) is not None:
# 		if isinstance(json, migration[0]):
# 			json = migration[1](json)
# 			break
# 	else:
# 		raise ValueError(f"Could not find next migration method for type: {type(json)}!")
#
# 	for _, migration in migrations:
# 		json = migration(json)
#
# 	return json
