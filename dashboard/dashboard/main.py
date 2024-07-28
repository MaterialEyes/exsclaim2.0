from dash import Dash, html, Input, Output, callback, dcc
import sd_material_ui as mui
import dash_bootstrap_components as dbc
import dash_material_components as dmc
import exsclaim_ui_components as ui

app = Dash("EXSCLAIM Dashboard", external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])

app.layout = html.Div(
	[
		ui.Header(EXSCLAIM_LOGO_SRC="/assets/ExsclaimLogo.png"),
		html.Div(
			"Div without n_clicks event listener",
			id="click-div-2",
			disable_n_clicks=False,
			style={
				"color": "red",
				"font-weight": "bold",
			},
		),
		html.P(id="click-output-2", disable_n_clicks=False),
		ui.Footer(),
	]
)


@callback(
	Output("click-output-2", "children"),
	Input("click-div-2", "n_clicks")
)
def click_counter(n_clicks):
	return f"The html.Div above has been clicked this many times: {n_clicks}"


if __name__ == "__main__":
	from os import getenv
	debug = getenv("DEBUG", "false").lower() == "true"
	while True:
		app.run(debug=debug, port=getenv("PORT", 8080), host="0.0.0.0")
