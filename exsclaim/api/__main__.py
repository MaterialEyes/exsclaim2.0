import exsclaim
import logging

from .middleware import *
from .routers import v1_router, general_router, query_router, users_router

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
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
			# "url": "https://materialeyes.org/help",
			"email": "developer@materialeyes.org"
		},
		"license": {
			"name": "MIT License",
			"identifier": "MIT",
			"url": "https://opensource.org/license/mit"
		},
	}

	app.openapi_schema = openapi_schema
	return app.openapi_schema


def create_logger(settings):
	printer_handler = logging.StreamHandler()
	printer_handler.setFormatter(exsclaim.PrinterFormatter())
	file_handler = TimedRotatingFileHandler(settings.LOGS_PATH / "exsclaim-api.log", backupCount=2,
											interval=1, when="D")
	file_handler.setFormatter(exsclaim.ExsclaimFormatter())

	logging.basicConfig(level=logging.INFO,
						handlers=(printer_handler, file_handler),
						force=True)
	return logging.getLogger(__name__)


def flush_logger(app: FastAPI):
	for handler in app.logger.handlers:
		handler.flush()


@asynccontextmanager
async def lifespan(app: FastAPI):
	# Runs before the application starts
	for _dir in ("results", "logs"):
		path = Path("/exsclaim") / _dir
		path.mkdir(exist_ok=True, parents=True)

	app.sitemap = None

	yield # Runs the application

	# Runs after the application has finished
	flush_logger(app)


def get_middleware(settings, logger) -> tuple[Middleware, ...]:
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
			allow_methods=["GET", "POST", "OPTIONS"],
			allow_headers=["*"],
		),
		Middleware(RequestLoggerMiddleware, logger=logger),
		Middleware(PreflightCacheMiddleware),
		Middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts),
		Middleware(GZipMiddleware, minimum_size=1_000),
		Middleware(SQLAlchemyMiddleware, logger=logger),
		Middleware(UserMiddleware),
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

	app.include_router(general_router, prefix="")
	app.include_router(query_router, prefix="")
	app.include_router(users_router, prefix="/user")
	app.include_router(v1_router, prefix="/results/v1")
	return app


app = None

if __name__ == "__main__":
	from asyncio import run
	from hypercorn.asyncio import serve
	from hypercorn.config import Config
	app = get_app()

	config = Config.from_pyfile(Path(__file__).parent / "config.py")

	run(serve(app, config))
