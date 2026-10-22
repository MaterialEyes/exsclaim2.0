from dash import ClientsideFunction, get_app, Output, Input, State
from json import dumps

app = get_app()


app.clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="add_new_row"
	),
	Output("training_data", "rowTransaction"),
	Input("add-row-button", "n_clicks"),
	prevent_initial_call=True
)

app.clientside_callback(
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


app.clientside_callback(
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


app.clientside_callback(
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


app.clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="update_current_figure"
	),
	[
		Output("training_data", "rowData"),
		Output("training_data_store", "data", allow_duplicate=True),
		Output("figure", "figure", allow_duplicate=True),
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


app.clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="update_coordinates"
	),
	[
		Output("figure", "figure", allow_duplicate=True),
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


app.clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="update_full_caption"
	),

	Output("training_data_store", "data", allow_duplicate=True),
	[
		Input("full_caption", "value"),
	],
	[
		State("training_data_store", "data"),
		State("current_figure", "value"),
	],
	prevent_initial_call=True
)


app.clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="download"
	),
	Output("download_data", "data"),
	Input("download_button", "n_clicks"),
	State("training_data_store", "data"),
	prevent_initial_call=True
)


app.clientside_callback(
	ClientsideFunction(
		namespace="train",
		function_name="upload"
	),
	Output("training_data_store", "data", allow_duplicate=True),
	Input("upload_data", "contents"),
	prevent_initial_call=True
)


@app.callback(
	Output("store-output", "children"),
	Input("training_data_store", "data")
)
def update_preview(data):
	return dumps(data, indent="\t")
