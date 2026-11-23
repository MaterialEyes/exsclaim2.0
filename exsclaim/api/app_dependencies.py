lazy import exsclaim
lazy import logging
lazy import yaml

lazy from .middleware import RequestLoggerMiddleware, MetricsMiddleware, IPBlockerMiddleware, SecurityMiddleware

lazy from contextlib import asynccontextmanager
lazy from fastapi import FastAPI
lazy from fastapi.openapi.utils import get_openapi
lazy from logging.handlers import TimedRotatingFileHandler
lazy from starlette.middleware import Middleware
lazy from starlette.middleware.cors import CORSMiddleware
lazy from starlette.middleware.gzip import GZipMiddleware
lazy from starlette.middleware.trustedhost import TrustedHostMiddleware
from typing import Literal


__all__ = ["my_schema", "create_logger", "flush_logger", "lifespan", "get_middleware"]


def my_schema(app: FastAPI):
	if app.openapi_schema:
		return app.openapi_schema

	openapi_schema = get_openapi(
		title="EXSCLAIM API",
		version=exsclaim.__version__,
		openapi_version="3.2.0",
		routes=app.routes,
	)

	openapi_schema["info"] = {
		"title": "EXSCLAIM API",
		"version": exsclaim.__version__,
		"description": ("**EX**traction, **S**eparation, and **C**aption-based natural **L**anguage **A**nnotation of **IM**ages from scientific figures API.<br>"
					   "Check out our paper at <a href=\"https://arxiv.org/abs/2103.10631\">https://arxiv.org/abs/2103.10631</a>.<br>"
					   "Check out our GitHub at <a href=\"https://github.com/MaterialEyes/exsclaim2.0\">https://github.com/MaterialEyes/exsclaim2.0</a>."),
		# "termsOfService": "https://materialeyes.org/terms/",
		"contact": {
			"name": "Developers",
			"email": "developer@materialeyes.org"
		},
		"license": {
			"name": "MIT License",
			"identifier": "MIT",
			"url": "https://opensource.org/license/mit"
		},
	}

	app.openapi_schema = openapi_schema
	app.openapi_yaml_schema = yaml.dump(openapi_schema, default_flow_style=False)
	return app.openapi_schema


def create_logger(settings, module: Literal["api", "dashboard"]):
	printer_handler = logging.StreamHandler()
	printer_handler.setFormatter(exsclaim.PrinterFormatter(show_logger_name=True))
	printer_handler.setLevel(logging.INFO)

	logs_path = settings.LOGS_PATH / module
	logs_path.mkdir(parents=True, exist_ok=True)

	file_handler = TimedRotatingFileHandler(logs_path / f"exsclaim-{module}.log", backupCount=14,
											interval=1, when="D")
	file_handler.setFormatter(exsclaim.ExsclaimFormatter())
	file_handler.setLevel(logging.INFO)

	debug_file_handler = TimedRotatingFileHandler(logs_path / f"exsclaim-{module}-debug.log", backupCount=14,
											interval=1, when="D")
	debug_file_handler.setFormatter(exsclaim.ExsclaimFormatter())
	debug_file_handler.setLevel(logging.DEBUG)

	error_file_handler = TimedRotatingFileHandler(logs_path / f"exsclaim-{module}-errors.log", backupCount=14,
											interval=7, when="D")
	error_file_handler.setFormatter(exsclaim.ExsclaimFormatter())
	error_file_handler.setLevel(logging.ERROR)

	handlers = (file_handler, debug_file_handler, error_file_handler)
	logging.basicConfig(level=logging.INFO, force=True, handlers=[printer_handler])
	logger = logging.getLogger(f"exsclaim.{module}")
	for handler in handlers:
		logger.addHandler(handler)
	return logger


def flush_logger(app: FastAPI):
	for handler in app.logger.handlers:
		handler.flush()


@asynccontextmanager
async def lifespan(app: FastAPI):
	app.sitemap = None

	yield # Runs the application

	# Runs after the application has finished
	flush_logger(app)


def get_middleware(settings, logger: logging.Logger, csp_header: Optional[str] = None) -> tuple[Middleware, ...]:
	origins = [
		"https://exsclaim.materialeyes.org",
		"https://exsclaim-dev.materialeyes.org",
		settings.DASHBOARD_URL
	]

	allowed_hosts = [
		"exsclaim.materialeyes.org",
		"*.exsclaim.materialeyes.org",
		"exsclaim-dev.materialeyes.org",
		"*.exsclaim-dev.materialeyes.org",
		"localhost",
		"127.0.0.1",
	]

	# Check if running on localhost, if so, add local domain names
	if (domain := settings.DOMAIN.domain):
		origins.extend([domain])

		# Removes the protocol for the allowed hosts
		domain = domain.split("//")[-1]
		allowed_hosts.extend((domain, f"*.{domain}"))

	return (
		# Logs all requests
		Middleware(RequestLoggerMiddleware, logger=logger),

		# Only compresses the generated response
		Middleware(GZipMiddleware, minimum_size=1_000),

		# Checks if the request should be blocked before hitting its endpoint
		Middleware(
			CORSMiddleware,
			allow_origins=origins,
			allow_credentials=True,
			allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
			allow_headers=["*"], # X-Request-Id
			expose_headers=["X-EXSCLAIM-Access-Minutes", "X-EXSCLAIM-Refresh-Days"]
		),
		Middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts),
		Middleware(IPBlockerMiddleware, logger=logger),
		Middleware(SecurityMiddleware, csp_header=csp_header),

		Middleware(MetricsMiddleware),
	)
