lazy from exsclaim.config import ui_settings
lazy from .app_dependencies import my_schema, create_logger, lifespan, get_middleware
lazy from .exception_handlers import handler_dict
lazy from .routers import v1_router, v2_router, general_router, query_router, users_router

lazy from fastapi import FastAPI
from typing import TYPE_CHECKING


__all__ = ["get_app"]


def get_app() -> FastAPI:
	import importlib

	use_prometheus = importlib.util.find_spec("prometheus_fastapi_instrumentator")
	logger = create_logger(ui_settings, "api")

	global app

	app = FastAPI(
		title=ui_settings.PROJECT_NAME,
		debug=ui_settings.DEBUG,
		docs_url=None,
		redoc_url=None,
		lifespan=lifespan,
		middleware=get_middleware(ui_settings, logger, csp_header=f"default-src 'self' {ui_settings.DOMAIN.domain_with_scheme}"),
		exception_handlers=handler_dict
	)

	app.logger = logger
	app.openapi = lambda: my_schema(app)
	app.configuration_ini = None

	for router in (general_router, query_router, users_router, v1_router, v2_router):
		app.include_router(router)

	if use_prometheus:
		from os import getenv
		from pathlib import Path

		multiprocessing_dir = getenv("PROMETHEUS_MULTIPROC_DIR")
		if multiprocessing_dir is not None:
			from shutil import rmtree

			multiprocessing_dir = Path(multiprocessing_dir)
			multiprocessing_dir.mkdir(parents=True, exist_ok=True)
			for child in multiprocessing_dir.iterdir():
				if child.is_dir():
					rmtree(child)
				else:
					child.unlink()

		from prometheus_fastapi_instrumentator import Instrumentator

		instrumentator = Instrumentator()
		instrumentator.instrument(app).expose(app)

	return app


if TYPE_CHECKING:
	app = get_app()
else:
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
