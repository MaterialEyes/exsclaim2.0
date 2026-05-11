try:
	from ..config import ui_settings
	from ..caption import LLMMeta
	from ..journal import JournalFamily
	from ..utilities import PrinterFormatter, ExsclaimFormatter
	from .components import create_homepage_layout, create_resultpage_layout, create_login_page_layout, FormMode, create_previous_runs_layout
except ImportError:
	from exsclaim import LLMMeta, JournalFamily, PrinterFormatter, ExsclaimFormatter, ui_settings
	from components import create_homepage_layout, create_resultpage_layout, create_login_page_layout, FormMode, create_previous_runs_layout

import dash_bootstrap_components as dbc
import logging

from dash import Dash, html, Output, Input, dcc, callback
from re import search
from uuid import UUID


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


def get_llms() -> tuple[dict[str, dict[str, str | bool]], dict[str, bool]]:
	available_llms = dict()
	for cls in LLMMeta.classes:
		available_llms[cls.__name__] = [dict(
			model_name=model_name,
			needs_api_key=needs_api_key,
			display_name=label if label is not None else model_name.title()
		) for model_name, needs_api_key, label in cls.available_models()]

	show_api_key = {llm["model_name"]: llm["needs_api_key"] for models in available_llms.values() for llm in models}

	return available_llms, show_api_key


title = "EXSCLAIM Dashboard"
app = Dash(title, title=title, on_error=error_handler, suppress_callback_exceptions=True, compress=True,
		   external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
		   meta_tags=[
			   {"property": "og:type", "content": "website"},
			   {"property": "og:url", "content": ui_settings.DOMAIN},
			   {"property": "og:title", "content": "EXSCLAIM Dashboard"},
			   {"property": "og:description", "content": ""},
			   {"property": "og:image", "content": f"{ui_settings.DOMAIN}/banner"},
		   ])
server = app.server
available_llms, show_api_key = get_llms()

journal_families = [name for name, cls in JournalFamily]
fastapi_url = ui_settings.FAST_API_URL
public_fastapi_url = ui_settings.PUBLIC_API_URL

# Use the new Dash HomePage layout instead of React components
home_page = create_homepage_layout(journal_families, available_llms)
login_page = create_login_page_layout(FormMode.LOGIN)
signup_page = create_login_page_layout(FormMode.SIGNUP)
previous_runs_page = create_previous_runs_layout()

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
		storage_type="memory",
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
def page_router(pathname: str):
	pathname = pathname.rstrip("/")
	if pathname == "/" or pathname == "":
		return home_page
	elif pathname == "/healthcheck":
		return healthcheck
	elif pathname == "/login":
		return login_page
	elif pathname == "/logout":
		return dcc.Location(f"{public_fastapi_url}/user/logout", refresh=False)
	elif pathname == "/signup":
		return signup_page
	elif pathname == "/previous":
		return previous_runs_page
	elif (result_id := search(r"/results/([\da-z-]+)", pathname)) is not None:
		result_id = result_id.group(1)
		return create_resultpage_layout(UUID(result_id), fastapi_url, public_fastapi_url)
	return None # TODO: Raise 404


def main():
	app.run(debug=ui_settings.DEBUG, port=settings.DASHBOARD_PORT, host="0.0.0.0")


if __name__ == "__main__":
	main()
