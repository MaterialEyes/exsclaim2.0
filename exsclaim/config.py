from datetime import datetime as dt
from multiprocessing import cpu_count
from os import getenv
from pathlib import Path
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from re import match
from typing import Optional

__all__ = ["ExsclaimSettings", "settings", "UISettings", "ui_settings", "get_variables", "orcid_settings", "ORCIDSettings"]


class ExsclaimSettings(BaseSettings):
	"""Gets access to the environment variables used throughout the project."""
	model_config = SettingsConfigDict(env_prefix="EXSCLAIM_", secrets_dir=("/run/secrets/", "/var/run"))

	ALLOW_PDF_PATHS: bool = Field(
		default=not match("^0?$", getenv("EXSCLAIM_ALLOW_PDF_PATHS", "0").strip()),
		description="",
		examples=[],
	)

	CHECKPOINTS: str = Field(
		default="/exsclaim/checkpoints",
		description="The directory where the checkpoint files for the FigureSeparator should be stored.",
		examples=["~/.exsclaim/checkpoints", "/exsclaim/checkpoints"],
	)

	@computed_field
	@property
	def CHECKPOINTS_PATH(self) -> Path:
		"""The path object representing the directory value in self.CHECKPOINTS."""
		return Path(self.CHECKPOINTS).resolve()

	DEBUG: bool = Field(
		default=not match("^0?$", getenv("EXSCLAIM_DEBUG", "0").strip()),
		description="If the service should run in DEBUG mode, which would allow for hot-reloading of the code and more detailed crash errors. Having the value unset or set as '0' turns of debug mode.",
		examples=["0", "1", ""],
	)

	LOGS: str = Field(
		default="/exsclaim/logs",
		description="The directory where the log files should be stored.",
		examples=["~/.exsclaim/logs", "/var/logs/exsclaim", "/exsclaim/logs"],
		env="LOGS"
	)

	@computed_field
	@property
	def LOGS_PATH(self) -> Path:
		"""The pathlib.Path object representing the directory value in self.LOGS_PATH."""
		return Path(self.LOGS).resolve()

	RESULTS: str = Field(
		default="/exsclaim/results",
		description="The directory where the results from the pipeline should be stored.",
		examples=["~/.exsclaim/results", "/exsclaim/results"],
		env="RESULTS"
	)

	@computed_field
	@property
	def RESULTS_PATH(self) -> Path:
		"""The pathlib.Path object representing the directory value in self.RESULTS_PATH."""
		return Path(self.RESULTS).resolve() if self.RESULTS is not None else Path.home().resolve() / ".exsclaim"

	UNCLASSIFIED_SUBFIGURES: Optional[str] = Field(
		default=getenv("EXSCLAIM_UNCLASSIFIED_SUBFIGURES", None),
		description="The directory where subfigures that could not have been classified should be stored (in case future models should be trained on it).",
		examples=["~/.exsclaim/training/unclassified", "/exsclaim/training/unclassified"],
	)

	@computed_field
	@property
	def UNCLASSIFIED_SUBFIGURES_PATH(self) -> Optional[Path]:
		"""The pathlib.Path object representing the directory value in self.UNCLASSIFIED_SUBFIGURES_PATH."""
		return Path(self.UNCLASSIFIED_SUBFIGURES).resolve() if self.UNCLASSIFIED_SUBFIGURES is not None else None

	UNDETECTED_SUBFIGURES: Optional[str] = Field(
		default=None,
		description="The directory where images that had no detected subfigures should be stored (in case future models should be trained on it).",
		examples=["~/.exsclaim/training/undetected", "/exsclaim/training/undetected"],
		env="UNDETECTED_SUBFIGURES"
	)

	@computed_field
	@property
	def UNDETECTED_SUBFIGURES_PATH(self) -> Optional[Path]:
		"""The pathlib.Path object representing the directory value in self.UNDETECTED_SUBFIGURES_PATH."""
		return Path(self.UNDETECTED_SUBFIGURES).resolve() if self.UNDETECTED_SUBFIGURES is not None else None

	UNSCRAPED_HTML: Optional[str] = Field(
		default=None,
		description="The directory where the HTML of articles that incurred an error should be stored (in case of debugging possible bugs in the code).",
		examples=["~/.exsclaim/training/unscraped", "/exsclaim/training/unscraped"],
		env="UNSCRAPED_HTML"
	)

	@computed_field
	@property
	def UNSCRAPED_HTML_PATH(self) -> Optional[Path]:
		"""The pathlib.Path object representing the directory value in self.UNSCRAPED_HTML_PATH."""
		return Path(self.UNSCRAPED_HTML).resolve() if self.UNSCRAPED_HTML is not None else None


class ORCIDSettings(BaseSettings):
	model_config = SettingsConfigDict(env_prefix="ORCID_", secrets_dir=("/run/secrets/", "/var/run"))

	URL: str = Field(
		default=getenv("ORCID_URL", "https://orcid.org").rstrip('/'),
		description="The URL that points to ORCID",
		examples=["https://orcid.org", "https://sandbox.orcid.org"],
	)

	CLIENT_ID: str = Field(
		description="",
	)

	CLIENT_SECRET: str = Field(
		description="",
	)


class UISettings(ExsclaimSettings):
	"""Gets access to the environment variables necessary for running the UI (API and Dashboard)."""

	DASHBOARD_URL: Optional[str] = Field(
		_dashboard_url.strip('/') if (_dashboard_url := getenv("EXSCLAIM_DASHBOARD_URL", None)) else None,
		description="The full URL that a user would use to access the UI.",
		examples=["http://localhost:3000", "https://exsclaim.local", "https://exsclaim.materialeyes.org"],
	)

	DASHBOARD_PORT: int = Field(
		default=3000,
		description="The port that a user would use to access the Dashboard.",
		examples=[3000, 80, 8080],
		env="DASHBOARD_PORT"
	)

	DOMAIN: str = Field(
		default=getenv("EXSCLAIM_DOMAIN", "").strip('/'),
		description="The domain that a user would use to access the API and Dashboard through a proxy such as NGINX.",
		examples=["https://exsclaim.local", "https://exsclaim-dev.materialeyes.org"],
	)

	FAST_API_URL: str = Field(
		default=getenv("EXSCLAIM_FAST_API_URL", "http://localhost:8000").rstrip('/'),
		description="The URL that a user inside the docker network would use to access the API i.e. from another service within Docker Compose.",
		examples=["http://localhost:8000", "http://python:8000"],
	)

	PUBLIC_API_URL: str = Field(
		default=getenv("EXSCLAIM_PUBLIC_FAST_API_URL", getenv("EXSCLAIM_FAST_API_URL", "http://localhost:8000")).rstrip('/'),
		description="The URL that any user outside of the Docker network would use to access the API, i.e. from the computer hosting the Docker Compose services or an external computer.",
		examples=["https://api.exsclaim.local", "https://api.exsclaim-dev.materialeyes.org"],
	)

	PROJECT_NAME: str = "EXSCLAIM API"


settings = ExsclaimSettings()
ui_settings = UISettings()
orcid_settings = ORCIDSettings()


def get_variables(port_env: str, default_port: str, log_subfolder: str) -> dict:
	log_dir = settings.LOGS_PATH / log_subfolder
	log_dir.mkdir(parents=True, exist_ok=True)
	time = dt.now().strftime("%Y-%m-%d")

	accesslog = log_dir / f"access-{time}.log"
	errorlog = log_dir / f"error-{time}.log"

	for log in (accesslog, errorlog):
		log.touch(mode=0o775, exist_ok=True)

	config = dict(
		bind=f"0.0.0.0:{getenv(port_env, default_port)}",
		workers=min(20, max(cpu_count() // 2, 1)), # Has at least 1 worker, at most 20 workers, or half of the cpus as workers if possible
		reload=settings.DEBUG,
		settings=settings,
		include_date_header=True,
		accesslog=str(accesslog),
		errorlog=str(errorlog),
	)

	return config


def generate_env_file():
	raise NotImplementedError # TODO: Have a function that generates a sample .env file
