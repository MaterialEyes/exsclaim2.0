try:
	from ..config import ui_settings
	from ..caption import LLMMeta
	from ..journal import JournalFamily
	from ..utilities import PrinterFormatter, ExsclaimFormatter
except ImportError:
	from exsclaim import LLMMeta, JournalFamily, PrinterFormatter, ExsclaimFormatter, ui_settings

from .components.query import get_llms

import dash
import dash_bootstrap_components as dbc
import logging

from dash import Dash, html, dcc
from flask import Flask, send_from_directory, redirect


__all__ = ["app", "server"]


printer_handler = logging.StreamHandler()
printer_handler.setFormatter(PrinterFormatter())
file_handler = logging.FileHandler(ui_settings.LOGS_PATH / "exsclaim-dashboard.log", "a")
file_handler.setFormatter(ExsclaimFormatter())

logging.basicConfig(level=logging.DEBUG,
					handlers=(printer_handler, file_handler),
					force=True)

logger = logging.getLogger(__name__)


def error_handler(exception: Exception) -> None:
	print(f"ERROR: {exception}")
	logger.exception(str(exception), exc_info=exception)


title = "EXSCLAIM Dashboard"
server = Flask(title, static_folder="assets")
app = Dash(title, title=title, on_error=error_handler, suppress_callback_exceptions=not ui_settings.DEBUG, compress=True,
		   external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME], use_pages=True,
		   external_scripts=["https://cdn.plot.ly/plotly-3.5.1.min.js"],
		   meta_tags=[
			   {"property": "og:type", "content": "website"},
			   {"property": "og:url", "content": ui_settings.DOMAIN},
			   {"property": "og:title", "content": "EXSCLAIM Dashboard"},
			   {"property": "og:description", "content": ""},
			   {"property": "og:image", "content": f"{ui_settings.DOMAIN}/banner"},
		   ],
		   health_endpoint="/healthcheck", server=server)
available_llms, show_api_key = get_llms()

fastapi_url = ui_settings.FAST_API_URL
public_fastapi_url = ui_settings.PUBLIC_API_URL


@server.route("/terms-of-service")
def terms_of_service():
	return send_from_directory("assets", "terms_of_service.html")


@server.route("/privacy-policy")
def privacy_policy():
	return send_from_directory("assets", "privacy_policy.html")


@server.route("/favicon.ico")
def favicon():
	return send_from_directory("assets", "favicon.ico")


@server.route("/logout")
def logout():
	return redirect(f"{public_fastapi_url}/user/logout")


app.layout = html.Div([
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
			public_fastapi_url=public_fastapi_url
		)),
	dcc.Location(id="url", refresh=False),
	# html.Div([
	# 	dcc.Link(page["name"], href=page["relative_path"]) for page in dash.page_registry.values()
	# ]),
	dash.page_container
])


def main():
	app.run(debug=ui_settings.DEBUG, port=ui_settings.DASHBOARD_PORT, host="0.0.0.0")


if __name__ == "__main__":
	main()
