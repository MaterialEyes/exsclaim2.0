from dash import dcc, html, Output, Input, State, clientside_callback, ClientsideFunction, register_page
from dash_extensions import Purify
import dash_bootstrap_components as dbc

try:
	from components.common import create_header_component, create_footer_component
except ImportError:
	from exsclaim.dashboard.components.common import create_header_component, create_footer_component


register_page(__name__, path="/previous", title="Previous Runs")


def create_runs_component():
	return html.Div([
		dcc.Interval(id="load-previous-runs", max_intervals=1),
		dcc.Interval(id="check-run-status", disabled=True, interval=30_000),
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


def layout():
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
		function_name="previous_runs"
	),
	Output("previous-runs", "html"),
	Output("exsclaim-runs", "display"),
	Output("check-run-status", "disabled"),

	Input("load-previous-runs", "n_intervals"),
	State("exsclaim-store", "data"),
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="update_data_table"
	),
	Output("check-run-status", "disabled"),
	Input("check-run-status", "n_intervals"),
	State("exsclaim-store", "data"),
	prevent_initial_call=True
)


clientside_callback(
	"(data) => { return data.theme; }",
	Output("previous-runs-table", "color"),
	Input("storage", "data")
)
