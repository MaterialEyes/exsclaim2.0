from datetime import datetime as dt
from multiprocessing import cpu_count
from os import getenv
from pathlib import Path
from pydantic import Field, computed_field, field_validator, EmailStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from re import compile
from typing import Optional, Self

__all__ = ["ExsclaimSettings", "settings", "UISettings", "ui_settings", "get_variables", "orcid_settings", "ORCIDSettings"]


BOOL_REGEX = compile("^0?$")


class EmailSettings(BaseSettings):
	SERVER: str = Field(description="The server that is hosting the email account.")
	PORT: int = Field(default=465)
	ACCOUNT: EmailStr = Field(description="The email that is used to send notifications.")
	PASSWORD: Optional[str] = Field(default=None, description="The password for the email account.")
	PASSWORD_FILE: Optional[Path] = Field(default=None,
										  description="The file containing the password for the email account.")

	@model_validator(mode="after")
	def get_password(self) -> Self:
		if self.PASSWORD is None and self.PASSWORD_FILE is None:
			raise ValueError("A password must be given for the email.")

		if self.PASSWORD_FILE is not None:
			with open(self.PASSWORD_FILE, "r") as f:
				self.PASSWORD = self.PASSWORD_FILE.read()

		self.PASSWORD = self.PASSWORD.strip()
		return self


class ExsclaimSettings(BaseSettings):
	"""Gets access to the environment variables used throughout the project."""
	model_config = SettingsConfigDict(
		env_prefix="EXSCLAIM_",
		env_nested_delimiter="__",
		secrets_dir=("/run/secrets/", "/var/run")
	)

	ALLOW_PDF_PATHS: bool = Field(
		default=False,
		description="",
		examples=[],
	)

	CHECKPOINTS_PATH: Path = Field(
		default="/exsclaim/checkpoints",
		description="The directory where the checkpoint files for the FigureSeparator should be stored.",
		examples=["~/.exsclaim/checkpoints", "/exsclaim/checkpoints"],
	)

	DEBUG: bool = Field(
		default=False,
		description="If the service should run in DEBUG mode, which would allow for hot-reloading of the code and more detailed crash errors. Having the value unset or set as '0' turns off debug mode.",
		examples=["0", "1", ""],
	)

	DISPLAY_TQDM: bool = Field(
		default=False,
		description="If tqdm progress bars should be displayed during the pipeline.",
		examples=["0", "1", ""],
	)

	EMAIL: Optional[EmailSettings] = Field(default=None)

	ALLOW_EMAILS_WITHOUT_ACCOUNT: bool = Field(
		default=True,
		description="If the Email's model validator should raise an error if emails are provided without the pipeline being able to send emails."
	)

	LOGS_PATH: Path = Field(
		default="/exsclaim/logs",
		description="The directory where the log files should be stored.",
		examples=["~/.exsclaim/logs", "/var/logs/exsclaim", "/exsclaim/logs"],
	)

	OLLAMA_HOST: Optional[str] = Field(
		default=None,
		description="The directory where the checkpoint files for the FigureSeparator should be stored.",
		examples=["http://localhost:11434", "http://ollama:11434"],
	)

	RESULTS_PATH: Path = Field(
		default=Path.home().resolve() / ".exsclaim",
		description="The directory where the results from the pipeline should be stored.",
		examples=["~/.exsclaim/results", "/exsclaim/results"],
	)

	UNCLASSIFIED_SUBFIGURES_PATH: Optional[Path] = Field(
		default=None,
		description="The directory where subfigures that could not have been classified should be stored (in case future models should be trained on it).",
		examples=["~/.exsclaim/training/unclassified", "/exsclaim/training/unclassified"],
	)

	UNDETECTED_SUBFIGURES_PATH: Optional[Path] = Field(
		default=None,
		description="The directory where images that had no detected subfigures should be stored (in case future models should be trained on it).",
		examples=["~/.exsclaim/training/undetected", "/exsclaim/training/undetected"],
	)

	UNSCRAPED_HTML_PATH: Optional[Path] = Field(
		default=None,
		description="The directory where the HTML of articles that incurred an error should be stored (in case of debugging possible bugs in the code).",
		examples=["~/.exsclaim/training/unscraped", "/exsclaim/training/unscraped"],
	)

	@field_validator("OLLAMA_HOST")
	@classmethod
	def domain_has_no_trailing_slash(cls, url: Optional[str]) -> Optional[str]:
		if url is None:
			return url
		return url.rstrip("/")

	@field_validator("ALLOW_PDF_PATHS", "DEBUG", "DISPLAY_TQDM", mode="before")
	@classmethod
	def validate_boolean(cls, value) -> bool:
		if isinstance(value, bool):
			return value

		if value is None:
			return False

		if isinstance(value, str):
			return BOOL_REGEX.match(value) is None

		raise ValueError(f"Unknown boolean-coercion type: {type(value).__name__} with value {value}.")

	@field_validator("CHECKPOINTS_PATH", "LOGS_PATH", "RESULTS_PATH", "UNDETECTED_SUBFIGURES_PATH", "UNCLASSIFIED_SUBFIGURES_PATH",
					 "UNSCRAPED_HTML_PATH", mode="after")
	@classmethod
	def validate_paths(cls, path: Optional[Path]) -> Optional[Path]:
		if path is None:
			return None

		path = path.resolve()

		if not path.is_dir():
			path.mkdir(parents=True, exist_ok=True)

		return path


class ORCIDSettings(BaseSettings):
	model_config = SettingsConfigDict(env_prefix="ORCID_", secrets_dir=("/run/secrets/", "/var/run"))

	URL: Optional[str] = Field(
		default=getenv("ORCID_URL", "https://orcid.org").rstrip('/'),
		description="The URL that points to ORCID",
		examples=["https://orcid.org", "https://sandbox.orcid.org"],
	)

	@field_validator("URL")
	@classmethod
	def url_has_no_trailing_slash(cls, url: str) -> Optional[str]:
		if url is None:
			return url
		return url.rstrip("/")

	CLIENT_ID: Optional[str] = Field(
		default=None,
		description="",
	)

	CLIENT_SECRET: Optional[str] = Field(
		default=None,
		description="",
	)


class UISettings(ExsclaimSettings):
	"""Gets access to the environment variables necessary for running the UI (API and Dashboard)."""

	ALLOW_RELOAD: bool = Field(
		default=True,
		description="Whether or not to allow reloading the UI even if it's debugging.",
	)

	DASHBOARD_URL: Optional[str] = Field(
		default="http://localhost:3000",
		description="The full URL that a user would use to access the UI.",
		examples=["http://localhost:3000", "https://exsclaim.local", "https://exsclaim.materialeyes.org"],
	)

	DASHBOARD_PORT: int = Field(
		default=3000,
		description="The port that a user would use to access the Dashboard.",
		examples=[3000, 80, 8080],
	)

	DOMAIN: str = Field(
		default="localhost",
		description="The domain that a user would use to access the API and Dashboard through a proxy such as NGINX.",
		examples=["https://exsclaim.local", "https://exsclaim-dev.materialeyes.org", "http://localhost"],
	)

	FAST_API_URL: str = Field(
		default="http://localhost:8000",
		# default=getenv("EXSCLAIM_FAST_API_URL", "http://localhost:8000").rstrip('/'),
		description="The URL that a user inside the docker network would use to access the API i.e. from another service within Docker Compose.",
		examples=["http://localhost:8000", "http://python:8000"],
	)

	PUBLIC_API_URL: str = Field(
		default="http://localhost:8000",
		description="The URL that any user outside of the Docker network would use to access the API, i.e. from the computer hosting the Docker Compose services or an external computer.",
		examples=["https://api.exsclaim.local", "https://api.exsclaim-dev.materialeyes.org"],
	)

	PROJECT_NAME: str = "EXSCLAIM API"

	JWT_PUBLIC_KEY_FILE: Optional[Path] = Field(
		default=None,
		description="The file containing the JWT public key to use to authenticate with the API.",
	)

	JWT_PRIVATE_KEY_FILE: Optional[Path] = Field(
		default=None,
		description="The file containing the JWT private key to use to authenticate with the API.",
	)

	@field_validator("DOMAIN", "FAST_API_URL", "PUBLIC_API_URL", "DASHBOARD_URL")
	@classmethod
	def domain_has_no_trailing_slash(cls, url: str) -> str:
		return url.rstrip("/")

	@field_validator("JWT_PUBLIC_KEY_FILE", "JWT_PRIVATE_KEY_FILE")
	@classmethod
	def get_jwt_secrets(cls, file: Optional[Path]) -> Optional[Path]:
		if file is None:
			return file

		file = file.resolve()

		if not file.is_file():
			raise FileNotFoundError(f"File {file} does not exist.")

		return file

	@field_validator("ALLOW_RELOAD", mode="before")
	@classmethod
	def validate_boolean(cls, value) -> bool:
		return super().validate_boolean(value)


settings = ExsclaimSettings()
ui_settings = UISettings()
orcid_settings = ORCIDSettings()


def get_variables(port_env: str, default_port: str, log_subfolder: str) -> dict:
	log_dir = settings.LOGS_PATH / log_subfolder
	log_dir.mkdir(parents=True, exist_ok=True)
	date = dt.now().strftime("%Y-%m-%d")

	accesslog = log_dir / f"access-{date}.log"
	errorlog = log_dir / f"error-{date}.log"

	for log in (accesslog, errorlog):
		log.touch(exist_ok=True)

	reload = settings.DEBUG and ui_settings.ALLOW_RELOAD
	config = dict(
		bind=f"0.0.0.0:{getenv(port_env, default_port)}",
		workers=min(20, max(cpu_count() // 2, 1)), # Has at least 1 worker, at most 20 workers, or half of the cpus as workers if possible
		reload=reload,
		settings=settings,
		include_date_header=True,
		accesslog=str(accesslog),
		errorlog=str(errorlog),
	)

	if settings.DEBUG:
		config["workers"] = 1

	return config


def generate_env_file():
	raise NotImplementedError # TODO: Have a function that generates a sample .env file
