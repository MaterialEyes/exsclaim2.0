try:
	from .exsclaim_ui_components import App
	from ..caption import LLM
	from ..journal import JournalFamily
	from ..utilities import PrinterFormatter, ExsclaimFormatter
except ImportError:
	from exsclaim.dashboard.exsclaim_ui_components import App
	from exsclaim import LLM, JournalFamily, PrinterFormatter, ExsclaimFormatter

import dash_bootstrap_components as dbc
import logging

from dash import Dash, html
from os import getenv

__all__ = ["app", "server"]


printer_handler = logging.StreamHandler()
printer_handler.setFormatter(PrinterFormatter())
file_handler = logging.FileHandler("/exsclaim/logs/exsclaim-dashboard.log", "a")
file_handler.setFormatter(ExsclaimFormatter())

logging.basicConfig(level=logging.DEBUG,
					handlers=(printer_handler, file_handler),
					force=True)

logger = logging.getLogger(__name__)


def error_handler(exception:Exception) -> None:
	print(f"ERROR: {exception}")
	logger.exception(str(exception))


title = "EXSCLAIM Dashboard"
app = Dash(title, title=title, on_error=error_handler,
		   external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
server = app.server

available_llms = [dict(model_name=model_name, needs_api_key=needs_api_key,
					   display_name=label if label is not None else model_name.title())
				  for model_name, (cls, needs_api_key, label) in LLM]
journal_families = [name for name, cls in JournalFamily]

app.layout = html.Div(
	[
		App(
			fast_api_url=getenv("FAST_API_URL", "http://localhost:8000").rstrip('/'),
			available_llms=available_llms,
			journalFamilies=journal_families
		),
	],
)


def main():
	debug = getenv("EXSCLAIM_DEBUG") is not None
	app.run(debug=debug, port=getenv("DASHBOARD_PORT", 3000), host="0.0.0.0")


if __name__ == "__main__":
	main()
