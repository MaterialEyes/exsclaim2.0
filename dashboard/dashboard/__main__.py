from dash import Dash, html, Input, Output, callback, dcc
import sd_material_ui as mui
import dash_bootstrap_components as dbc
# import dash_material_components as dmc
try:
	import exsclaim_ui_components as ui
except ImportError:
	from . import exsclaim_ui_components as ui

__all__ = ["app", "server"]


app = Dash("EXSCLAIM Dashboard", external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
server = app.server
_loadResults = False


app.layout = html.Div(
	[	# TODO: Read the favicon https://dash.plotly.com/external-resources
		ui.Header(EXSCLAIM_LOGO_SRC="/assets/ExsclaimLogo.png"),
		ui.Query(id="query") if _loadResults else ui.Layout(id="layout"),
		# html.Div(
		# 	"Div without n_clicks event listener",
		# 	id="click-div-2",
		# 	disable_n_clicks=False,
		# 	style={
		# 		"color": "red",
		# 		"font-weight": "bold",
		# 	},
		# ),
		# html.P(id="click-output-2", disable_n_clicks=False),
		ui.Footer(),
	],
	style={"text-align": "center"}
)

# @callback(
# 	Output("click-output-2", "children"),
# 	Input("click-div-2", "n_clicks")
# )
# def click_counter(n_clicks):
# 	return f"The html.Div above has been clicked this many times: {n_clicks}"


# TODO: Add a callback that will switch between the Layout and Query based on loadResults
@callback(
	Output("layout", "loadResults"),
	Input("layout", "loadResults")
)
@callback(
	Output("query", "loadResults"),
	Input("query", "loadResults")
)
def click_counter(loadResults):
	global _loadResults
	print(f"{loadResults=}")
	_loadResults = not _loadResults
	return _loadResults


if __name__ == "__main__":
	from os import getenv
	debug = getenv("DEBUG", "false").lower() == "true"
	while True:
		app.run(debug=debug, port=getenv("PORT", 3000), host="0.0.0.0")
