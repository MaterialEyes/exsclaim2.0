from dash import dcc, html, Output, Input, State, clientside_callback, ClientsideFunction
from dash_extensions import Purify
import dash_bootstrap_components as dbc
from .common import create_header_component, create_footer_component


__all__ = ["create_previous_runs_layout"]


def create_runs_component():
	return html.Div([
		dcc.Interval(id="load-previous-runs", max_intervals=1),
		dbc.Table(
			Purify(id="previous-runs"),
			id="previous-runs-table",
			bordered=True,
			color="dark",
			hover=True,
			responsive=True,
			striped=True,
		),
		dcc.Loading(
			color="#93fad9",
			display="show",
			fullscreen=False,
			type="circle",
			id="exsclaim-runs"
		),
	])


def create_previous_runs_layout():
	return html.Div([
		# Header
		create_header_component(),

		# Results
		create_runs_component(),

		# Footer
		create_footer_component()
	], id="exsclaim-app")


clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="previous_runs_regular_table"
	),
	[
		Output("previous-runs", "html", allow_duplicate=True),
		Output("exsclaim-runs", "display"),
	],
	[
		Input("load-previous-runs", "n_intervals")
	],
	[
		State("exsclaim-store", "data"),
	],
	prevent_initial_call=True
)


clientside_callback(
	"(data) => { return data.theme; }",
	Output("previous-runs-table", "color"),
	Input("theme", "data")
)
