lazy from exsclaim.api.app_dependencies import my_schema, create_logger, lifespan, get_middleware
lazy from exsclaim.config import ui_settings

lazy from .routers import router
lazy from .components.query import get_llms

lazy import dash
lazy import dash_bootstrap_components as dbc

lazy from fastapi import FastAPI
lazy from pathlib import Path
from typing import TYPE_CHECKING


__all__ = ["get_app"]


global logger


def error_handler(exception: Exception) -> None:
	print(f"ERROR: {exception}")
	logger.exception("An error occurred in Dash", exc_info=exception)


def fix_badge_issue(app: FastAPI):
	"""Fixes the issue with img.shields.io reporting the site is down when it isn't."""
	from fastapi.routing import APIRoute
	routes = filter(lambda route: isinstance(route, APIRoute) and route.path == "/", app.router.routes)
	route = next(routes, None)
	if route is None:
		return

	route.methods.add("HEAD")


def get_app() -> FastAPI:
	global logger
	logger = create_logger(ui_settings, "dashboard")
	title = "EXSCLAIM Dashboard"
	plotly_script = "https://cdn.plot.ly/plotly-4.3.0.min.js"

	csp_header = f"default-src 'self' {ui_settings.DOMAIN.domain_with_scheme}; style-src-elem 'unsafe-inline' 'self' https://cdn.jsdelivr.net/ https://use.fontawesome.com/ https://fonts.googleapis.com; script-src-elem 'unsafe-inline' {plotly_script} 'self'; font-src https://fonts.gstatic.com/ https://use.fontawesome.com/; connect-src *.{ui_settings.DOMAIN.domain} {ui_settings.DOMAIN.domain} https://cdn.jsdelivr.net/; img-src 'unsafe-inline' 'self' {ui_settings.DOMAIN.domain_with_scheme} https://media.springernature.com/ data:;"
	server = FastAPI(
		title=title,
		debug=ui_settings.DEBUG,
		docs_url=None,
		redoc_url=None,
		lifespan=lifespan,
		middleware=get_middleware(ui_settings, logger, csp_header=csp_header),
		terms_of_service="/terms-of-service"
	)
	server.logger = logger
	server.openapi = lambda: my_schema(server)
	server.configuration_ini = None

	server.include_router(router)

	meta_tags = [
		{"property": "og:url", "content": ui_settings.DOMAIN.components.geturl()},
	]

	logo_path = Path(__file__).parent / "assets" / "logo.png"
	if logo_path.is_file():
		from contextlib import suppress
		from PIL import Image

		with suppress(FileNotFoundError):
			width, height = Image.open(logo_path).size
			meta_tags.extend([
				{"property": "og:image", "content": f"{ui_settings.DASHBOARD_URL}/assets/logo.png"},
				{"property": "og:image:width", "content": str(width)},
				{"property": "og:image:height", "content": str(height)},
			])

	app = dash.Dash(
		title,
		title=title,
		on_error=error_handler,
		suppress_callback_exceptions=not ui_settings.DEBUG,
		compress=False,
		external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
		use_pages=True,
		external_scripts=[plotly_script],
		meta_tags=meta_tags,
		health_endpoint="/healthcheck",
		server=server,
		show_undo_redo=True,
	)

	import callbacks # Imports the callbacks after the app is created

	if ui_settings.DEBUG:
		app.enable_dev_tools(
			debug=True,
			dev_tools_ui=True,
			dev_tools_props_check=True,
			# dev_tools_prune_errors=False,
			# dev_tools_hot_reload=False,
			# dev_tools_serve_dev_bundles=False
		)
		app.backend.register_prune_error_handler(None, False)

	available_llms, show_api_key, required_api_key = get_llms()

	fastapi_url = ui_settings.FAST_API_URL.domain_with_scheme
	public_fastapi_url = ui_settings.PUBLIC_API_URL.domain_with_scheme

	app.layout = dash.html.Div([
		dash.dcc.Interval(
			id="check-credentials",
			interval=2_500 # Check credentials after 2.5 seconds. The callback disables it if the user isn't logged in.
		),
		dash.dcc.Store(
			id="storage",
			storage_type="local",
			data=dict(
				theme="light",
				last_seen_banner=None
			)
		),
		dash.dcc.Store(
			id="exsclaim-store",
			storage_type="memory",
			data=dict(
				fast_api_url=fastapi_url,
				available_llms=available_llms,
				show_api_key=show_api_key,
				required_api_key=required_api_key,
				public_fastapi_url=public_fastapi_url
			)),
		dash.dcc.Location(id="url", refresh=False),
		dash.page_container
	])

	fix_badge_issue(server)

	return server


def main():
	app = get_app()
	app.run(debug=ui_settings.DEBUG, port=ui_settings.DASHBOARD_PORT, host="0.0.0.0")


if TYPE_CHECKING:
	app = get_app()
else:
	app = None


# if __name__ == "__main__":
# 	main()
