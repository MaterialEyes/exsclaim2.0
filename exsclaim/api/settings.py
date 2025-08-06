from os import getenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(secrets_dir=("/run/secrets/", "/var/run"))

	PROJECT_NAME: str = "FastAPI"
	DEBUG: bool = getenv("EXSCLAIM_DEBUG", "0").strip() != "0"
