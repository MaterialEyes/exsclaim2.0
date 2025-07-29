try:
	from ..caption import LLM
	from ..journal import JournalFamily
	from ..utilities import PrinterFormatter, ExsclaimFormatter
	from .components import create_homepage_layout, create_resultpage_layout
except ImportError:
	from exsclaim import LLM, JournalFamily, PrinterFormatter, ExsclaimFormatter
	from components import create_homepage_layout, create_resultpage_layout

import dash_bootstrap_components as dbc
import logging

from dash import Dash, html, Output, Input, dcc, callback
from os import getenv
from re import search
from uuid import UUID


__all__ = ["app", "server"]


printer_handler = logging.StreamHandler()
printer_handler.setFormatter(PrinterFormatter())
file_handler = logging.FileHandler("/exsclaim/logs/exsclaim-dashboard.log", "a")
file_handler.setFormatter(ExsclaimFormatter())

logging.basicConfig(level=logging.DEBUG,
					handlers=(printer_handler, file_handler),
					force=True)

logger = logging.getLogger(__name__)
DEBUG = getenv("EXSCLAIM_DEBUG") is not None


def error_handler(exception:Exception) -> None:
	print(f"ERROR: {exception}")
	logger.exception(str(exception))


title = "EXSCLAIM Dashboard"
app = Dash(title, title=title, on_error=error_handler,
		   external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
server = app.server

available_llms = [dict(
					model_name=model_name,
					needs_api_key=needs_api_key,
					display_name=label if label is not None else model_name.title()
				  ) for model_name, (cls, needs_api_key, label) in LLM]
show_api_key = {llm["model_name"]: llm["needs_api_key"] for llm in available_llms}

journal_families = [name for name, cls in JournalFamily]
fastapi_url = getenv("FAST_API_URL", "http://localhost:8000").rstrip('/')
public_fastapi_url = getenv("PUBLIC_FAST_API_URL", fastapi_url).rstrip('/')

# Use the new Dash HomePage layout instead of React components
home_page = create_homepage_layout(title, journal_families, available_llms)

healthcheck = html.Div([
	html.P("EXSCLAIM Dashboard is operating normally.")
])


app.layout = html.Div([
	dcc.Store(
		id="theme",
		storage_type="local",
		data=dict(theme="light")),
	dcc.Store(
		id="exsclaim-store",
		storage_type="session",
		data=dict(
			fast_api_url=fastapi_url,
			available_llms=available_llms,
			show_api_key=show_api_key,
			public_fastapi_url=public_fastapi_url
		)),
	dcc.Location(id="url", refresh=False),
	html.Div(id="page-content"),
])


@callback(
	Output("page-content", "children"),
	Input("url", "pathname")
)
def page_router(pathname:str):
	if pathname == "/" or pathname == "":
		return home_page
	elif pathname == "/healthcheck":
		return healthcheck
	elif (result_id := search(r"/results/([\da-z-]+)", pathname)) is not None:
		result_id = result_id.group(1)
		return create_resultpage_layout(UUID(result_id), fastapi_url)
	return None # TODO: Raise 404


def main():
	app.run(debug=DEBUG, port=getenv("DASHBOARD_PORT", 3000), host="0.0.0.0")


if __name__ == "__main__":
	main()
