try:
	from ... import ui_settings
	from components.common import create_header_component, create_footer_component
except ImportError:
	from exsclaim import ui_settings
	from exsclaim.dashboard.components import create_header_component, create_footer_component

from dash import html, dcc, clientside_callback, ClientsideFunction, Output, Input, State, callback, register_page
from json import dumps
# from plotly.graph_objs import Figure

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import numpy as np

register_page(__name__, path="/train", title="Training")


# https://dash.plotly.com/annotations
def get_image_annotator() -> dcc.Graph:
	config = {
		"modeBarButtonsToAdd": [
			"drawrect", "eraseshape"
		]
	}

	fig = np.zeros((256, 256, 3))
	graph = dcc.Graph(id="figure", figure=fig, config=config)
	return graph


def get_full_caption():
	return dbc.Textarea(id="full_caption", placeholder="Full Caption", debounce=True)


def get_article_button():
	return html.A(html.Button("Go to Article", id="article_button"), id="article_url", target="_blank")


def get_data_table():
	from httpx2 import Client

	client = Client(base_url=ui_settings.FAST_API_URL)
	response = client.get("/classification_codes")
	if response.is_success:
		classes = [i["name"] for i in response.json()]
	else:
		classes = [] # TODO: Handle if the API doesn't respond

	columnsDefs = [
		dict(field="label", headerName="Label", cellStyle=dict(function="colorByLabel(params)")),
		dict(field="classification", headerName="Classification", cellEditor="agSelectCellEditor", cellEditorParams=dict(values=classes)),
		dict(field="x0", headerName="Left"),
		dict(field="y0", headerName="Top"),
		dict(field="x1", headerName="Right"),
		dict(field="y1", headerName="Bottom"),
		dict(field="label_x0", headerName="Label Left"),
		dict(field="label_y0", headerName="Label Top"),
		dict(field="label_x1", headerName="Label Right"),
		dict(field="label_y1", headerName="Label Bottom"),
		dict(field="subcaption", headerName="Caption", resizable=True),
	]

	grid = dag.AgGrid(
		id="training_data",
		defaultColDef={"editable": True},
		rowData=[],
		columnDefs=columnsDefs,
		columnSize="autoSize",
	)

	add_row_button = html.Button("Add New Row", id="add-row-button")

	return html.Div(children=[
		grid, add_row_button
	])


def layout():
	return dbc.Container(fluid=True, style={
		"width": "95%",
		"padding": "20px",
		"margin": "20px",
		"justifyContent": "center",
		"display": "flex",
		"flex-direction": "column",
	}, children=[
		create_header_component(),
		dcc.Store(
			id="training_data_store",
			storage_type="local",
			data=dict()
		),
		dbc.Row(
			align="stretch", justify="center", children=[
				dbc.Col(align="center", children=[
					dcc.Upload(
						["Drag and Drop or ", html.A("Select a File"), " to Upload Training Data"],
						id="upload_data",
						accept="application/json",
						style={
							"width": "100%",
							'height': '60px',
							'lineHeight': '60px',
							'borderWidth': '1px',
							'borderStyle': 'dashed',
							'borderRadius': '5px',
							'textAlign': 'center',
						}
					),
				]),
				dbc.Col(align="center", children=[
					html.Button(
						id="download_button",
						children="Download Training Data!",
						style={
							"width": "100%",
							"height": "60px",
							"backgroundColor": "var(--accent-dark)"
						}
					),
				])
			]
		),
		dcc.Download(id="download_data"),
		dcc.Interval(id="start-interval", max_intervals=1),
		dbc.Row(align="stretch", justify="center", children=[
			dbc.Label("Previous Runs:", html_for="run_selector"),
			dcc.Dropdown(id="run_selector", multi=True),
			dbc.Label("Figures in Training Set:", html_for="figure_selector"),
			dcc.Dropdown(id="figure_selector", multi=True),
			dbc.Label("Current Figure:", html_for="current_figure"),
			dcc.Dropdown(id="current_figure"),
		]),
		dbc.Row(align="stretch", justify="center", children=[
			dbc.Col(align="center", children=[
				get_image_annotator(),
				get_full_caption(),
			]),
			dbc.Col(align="center", children=[
				get_article_button(),
				get_data_table()
			]),
		]),
		html.Pre(id="store-output"),
		create_footer_component()
	])


clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="add_new_row"
	),
	Output("training_data", "rowTransaction"),
	Input("add-row-button", "n_clicks"),
	prevent_initial_call=True
)

clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="load_previous_runs"
	),
	[
		Output("run_selector", "options"),
		Output("run_selector", "value"),
		Output("start-interval", "disabled")
	],
	[
		Input("start-interval", "n_intervals")
	],
	[
		State("exsclaim-store", "data"),
	],
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="populate_figures"
	),
	[
		Output("figure_selector", "options")
	],
	[
		Input("run_selector", "value")
	],
	[
		State("exsclaim-store", "data"),
	],
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="update_available_figures"
	),
	[
		Output("current_figure", "options"),
		Output("current_figure", "value"),
	],
	[
		Input("figure_selector", "value")
	],
	[
		# State("exsclaim-store", "data"),
		State("current_figure", "value"),
	],
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="update_current_figure"
	),
	[
		Output("training_data", "rowData"),
		Output("training_data_store", "data"),
		Output("figure", "figure"),
		Output("full_caption", "value"),
		Output("article_url", "href"),
		Output("article_button", "hidden"),
	],
	[
		Input("current_figure", "value"),
		# Input("training_data_store", "data"),
	],
	[
		State("training_data_store", "data"),
	],
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="update_coordinates"
	),
	[
		Output("figure", "figure"),
		Output("training_data_store", "data"),
	],
	[
		Input("training_data", "cellValueChanged"),
	],
	[
		State("training_data_store", "data"),
		State("current_figure", "value"),
	],
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="update_full_caption"
	),

	Output("training_data_store", "data"),
	[
		Input("full_caption", "value"),
	],
	[
		State("training_data_store", "data"),
		State("current_figure", "value"),
	],
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="download"
	),
	Output("download_data", "data"),
	Input("download_button", "n_clicks"),
	State("training_data_store", "data"),
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="upload"
	),
	Output("training_data_store", "data"),
	Input("upload_data", "contents"),
	prevent_initial_call=True
)


@callback(
	Output("store-output", "children"),
	Input("training_data_store", "data")
)
def update_preview(data):
	return dumps(data, indent="\t")
