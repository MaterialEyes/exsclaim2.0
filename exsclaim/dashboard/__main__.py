from werkzeug.middleware.proxy_fix import ProxyFix

try:
	from ..config import ui_settings
	from ..utilities import PrinterFormatter, ExsclaimFormatter
except ImportError:
	from exsclaim import PrinterFormatter, ExsclaimFormatter, ui_settings

from .components.query import get_llms

import dash
import dash_bootstrap_components as dbc
import flask
import logging

from datetime import datetime as dt, timezone as tz
from dash import Dash, html, dcc
from textwrap import dedent
from pathlib import Path


__all__ = ["app", "server"]


logger, app = None, None
title = "EXSCLAIM Dashboard"
server = flask.Flask(title, static_folder="assets")
server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1, x_proto=1)


def create_logger(settings) -> logging.Logger:
	printer_handler = logging.StreamHandler()
	printer_handler.setFormatter(PrinterFormatter())
	printer_handler.setLevel(logging.INFO)

	file_handler = logging.FileHandler(settings.LOGS_PATH / "exsclaim-dashboard.log", "a")
	file_handler.setFormatter(ExsclaimFormatter())
	file_handler.setLevel(logging.DEBUG)

	handlers = (printer_handler, file_handler)
	logging.basicConfig(level=logging.INFO, force=True, handlers=[printer_handler])

	logger = logging.getLogger("exsclaim.dashboard")
	for handler in handlers:
		logger.addHandler(handler)
	return logger


def error_handler(exception: Exception) -> None:
	print(f"ERROR: {exception}")
	logger.exception("An error occurred in Dash", exc_info=exception)


def create_sitemap() -> str:
	host = ui_settings.DASHBOARD_URL
	last_mod = dt.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%z")

	def format_xml(page) -> Optional[str]:
		path = page["relative_path"].replace("/none", "/*")

		return dedent(f"""\
			<url>
				<loc>{host}{path}</loc>
				<lastmod>{last_mod}</lastmod>
			</url>
		""")

	routes = map(lambda page: format_xml(page), dash.page_registry.values())
	sitemap = f'<urlset xmlns="https://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="https://www.w3.org/1999/xhtml">\n{''.join(routes)}</urlset>'
	return sitemap


def get_app() -> Dash:
	global logger, app

	logger = create_logger(ui_settings)
	meta_tags = [
		{"property": "og:url", "content": ui_settings.DOMAIN},
	]

	logo_path = Path(__file__).parent / "assets" / "logo.png"
	if logo_path.is_file():
		import cv2
		image = cv2.imread(logo_path)
		if image is not None:
			height, width, _ = image.shape
			meta_tags.extend([
				{"property": "og:image", "content": f"{ui_settings.DASHBOARD_URL}/assets/logo.png"},
				{"property": "og:image:width", "content": str(width)},
				{"property": "og:image:height", "content": str(height)},
			])

	app = Dash(
		title,
		title=title,
		on_error=error_handler,
		suppress_callback_exceptions=not ui_settings.DEBUG,
		compress=False,
		external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
		use_pages=True,
		external_scripts=["https://cdn.plot.ly/plotly-3.5.1.min.js"],
		meta_tags=meta_tags,
		health_endpoint="/healthcheck",
		server=server,
		show_undo_redo=True,
	)

	available_llms, show_api_key, required_api_key = get_llms()

	fastapi_url = ui_settings.FAST_API_URL
	public_fastapi_url = ui_settings.PUBLIC_API_URL

	app.layout = html.Div([
		dcc.Interval(
			id="check-credentials",
			interval=300_000 # Check every 5 minutes
		),
		dcc.Store(
			id="storage",
			storage_type="local",
			data=dict(
				theme="light",
				last_seen_banner=None
			)
		),
		dcc.Store(
			id="exsclaim-store",
			storage_type="memory",
			data=dict(
				fast_api_url=fastapi_url,
				available_llms=available_llms,
				show_api_key=show_api_key,
				required_api_key=required_api_key,
				public_fastapi_url=public_fastapi_url
			)),
		dcc.Location(id="url", refresh=False),
		dash.page_container
	])
	server.sitemap = create_sitemap()
	return app


@server.route("/terms-of-service")
def terms_of_service():
	return flask.send_from_directory("assets", "terms_of_service.html")


@server.route("/privacy-policy")
def privacy_policy():
	return flask.send_from_directory("assets", "privacy_policy.html")


@server.route("/favicon.ico")
def favicon_ico():
	return flask.send_from_directory("assets", "favicon.ico")


@server.route("/favicon.png")
def favicon_png():
	return flask.send_from_directory("assets", "favicon.png")


@server.route("/logout")
def logout():
	return flask.redirect(f"{ui_settings.PUBLIC_API_URL}/user/logout")


@server.route("/robots.txt")
def robots():
	robots = dedent(f"""\
		User-Agent: *
		Content-signal: search=yes, ai-train=no, use=reference
		Allow: /
		
		User-Agent: Amazonbot
		Disallow: /
		
		User-agent: Applebot-Extended
		Disallow: /
		
		User-agent: Bytespider
		Disallow: /
		
		User-agent: CCBot
		Disallow: /
		
		User-Agent: ClaudeBot
		Disallow: /
		
		User-Agent: Google-Extended
		Disallow: /
		
		User-Agent: GPTBot
		Disallow: /
		
		Allow: /login
		
		Allow: /signup
		
		Allow: /terms-of-service
		
		Allow: /privacy-policy
		
		Disallow: /results/*
		
		Disallow: /train
		
		Disallow: /previous
		
		Disallow: /logout
		
		Sitemap: {ui_settings.DASHBOARD_URL}/sitemap.xml
	""")
	return flask.Response(robots, status=200, mimetype="text/plain")


@server.route("/sitemap.xml")
def sitemap():
	if hasattr(server, "sitemap"):
		sitemap = server.sitemap
	else:
		sitemap = create_sitemap()
		server.sitemap = sitemap
	return flask.Response(sitemap, status=200, mimetype="text/xml")


def main():
	app.run(debug=ui_settings.DEBUG, port=ui_settings.DASHBOARD_PORT, host="0.0.0.0")


app = get_app()


if __name__ == "__main__":
	main()
