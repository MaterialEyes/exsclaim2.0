from dash import Dash, html, Input, Output, callback, ctx, dcc
from flask import Flask
import sd_material_ui as mui
import dash_bootstrap_components as dbc
from os import getenv
try:
	import exsclaim_ui_components as ui
except ImportError:
	import exsclaim.dashboard.exsclaim_ui_components as ui

__all__ = ["app", "server"]


title = "EXSCLAIM Dashboard"
app = Dash(title, title=title,
		   external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
server = app.server


app.layout = html.Div(
	[
		ui.App(fast_api_url=getenv("FAST_API_URL", "http://fastapi")),
	],
)


if __name__ == "__main__":
	debug = getenv("DEBUG", "false").lower() == "true"
	app.run(debug=debug, port=getenv("PORT", 3000), host="0.0.0.0")
