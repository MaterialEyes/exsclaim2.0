from os import getenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(secrets_dir=("/run/secrets/", "/var/run"))

	PROJECT_NAME: str = "FastAPI"
	DEBUG: bool = getenv("EXSCLAIM_DEBUG") is not None

	# db_password: str = None
	#
	# @property
	# def db_url(self) -> str:
	# 	if self.db_password is None:
	# 		with open("/run/secrets/db_password", 'r') as f:
	# 			self.db_password = f.read().strip()
	# 	return f"postgresql+asyncpg://exsclaim:{self.db_password}@db:5432/exsclaim"
