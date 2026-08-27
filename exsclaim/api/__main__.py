import exsclaim
import logging
import yaml

from .middleware import *
from .routers import v1_router, general_router, query_router, users_router

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from logging.handlers import TimedRotatingFileHandler
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware


__all__ = ["get_app"]


def my_schema():
	if app.openapi_schema:
		return app.openapi_schema

	openapi_schema = get_openapi(
		title="EXSCLAIM API",
		version=exsclaim.__version__,
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


def create_logger(settings):
	printer_handler = logging.StreamHandler()
	printer_handler.setFormatter(exsclaim.PrinterFormatter())
	printer_handler.setLevel(logging.INFO)

	file_handler = TimedRotatingFileHandler(settings.LOGS_PATH / "exsclaim-api.log", backupCount=14,
											interval=1, when="D")
	file_handler.setFormatter(exsclaim.ExsclaimFormatter())
	file_handler.setLevel(logging.INFO)

	debug_file_handler = TimedRotatingFileHandler(settings.LOGS_PATH / "exsclaim-api-debug.log", backupCount=14,
											interval=1, when="D")
	debug_file_handler.setFormatter(exsclaim.ExsclaimFormatter())
	debug_file_handler.setLevel(logging.DEBUG)

	handlers = (file_handler, debug_file_handler)
	logging.basicConfig(level=logging.INFO, force=True, handlers=[printer_handler])
	logger = logging.getLogger("exsclaim.api")
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


def get_middleware(settings, logger: logging.Logger) -> tuple[Middleware, ...]:
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
	if (domain := settings.DOMAIN):
		origins.extend([domain])

		# Removes the protocol for the allowed hosts
		domain = domain.split("//")[-1]
		allowed_hosts.extend((domain, f"*.{domain}"))

	return (
		Middleware(
			CORSMiddleware,
			allow_origins=origins,
			allow_credentials=True,
			allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
			allow_headers=["*"],
			expose_headers=["X-EXSCLAIM-Access-Minutes", "X-EXSCLAIM-Refresh-Days"]
		),
		Middleware(RequestLoggerMiddleware, logger=logger),
		Middleware(PreflightCacheMiddleware),
		Middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts),
		Middleware(GZipMiddleware, minimum_size=1_000),
	)


def get_app() -> FastAPI:
	settings = exsclaim.ui_settings
	logger = create_logger(settings)

	global app

	app = FastAPI(
		title=settings.PROJECT_NAME,
		debug=settings.DEBUG,
		docs_url=None,
		redoc_url=None,
		lifespan=lifespan,
		middleware=get_middleware(settings, logger),
	)

	app.logger = logger
	app.openapi = my_schema
	app.configuration_ini = None

	for router in (general_router, query_router, users_router, v1_router):
		app.include_router(router)

	return app


app = None

# if __name__ == "__main__":
# 	from asyncio import run
# 	from hypercorn.asyncio import serve
# 	from hypercorn.config import Config
# 	app = get_app()
#
# 	config = Config.from_pyfile(Path(__file__).parent / "config.py")
#
# 	run(serve(app, config))
