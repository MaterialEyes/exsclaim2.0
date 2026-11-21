import dash_bootstrap_components as dbc
import re

from dash import html, ClientsideFunction, Output, Input, State, no_update, ALL, get_app
from dash_extensions import Purify
from exsclaim.api import Status

app = get_app()


app.clientside_callback(
	ClientsideFunction(
		namespace="clientside",
		function_name="update_layout_state"
	),
	Output("layout-state", "data"),
	Output("api-polling-interval", "disabled"),
	Output("main-content", "style"),
	Output("loading-container", "display"),
	Input("api-polling-interval", "n_intervals"),
	State("layout-state", "data"),
	State("exsclaim-store", "data"),
)


@app.callback(
	Output("result-id-display", "children"),
	Input("layout-state", "data"),
	prevent_initial_call=True
)
def update_result_id(data):
	"""Update result ID display."""
	if data and "results_id" in data:
		return data["results_id"]
	return no_update


@app.callback(
	Output("keyword-dropdown", "options"),
	[
		Input("keyword-type", "value"),
		Input("layout-state", "data")
	],
	prevent_initial_call=True
)
def update_keywords(keyword_type, data):
	"""Update keywords dropdown based on keyword type."""
	if not data:
		return []

	all_subfigures = data.get("all_subfigures", [])
	articles = data.get("articles", [])

	keywords = []

	match keyword_type:
		case "caption" | "general":
			for subfigure in all_subfigures:
				if subfigure.get(keyword_type):
					if isinstance(subfigure[keyword_type], str):
						keywords.extend(subfigure[keyword_type].split(" "))
					else:
						keywords.extend(subfigure[keyword_type])

		case "title":
			for article in articles:
				if article.get("title"):
					keywords.extend(article["title"].split(" "))

	# Remove duplicates and create options
	kw_regex = re.compile(r"[^\w\d<>_-]", re.I)
	unique_keywords = sorted({kw_regex.sub("", kw) for kw in keywords}, key=lambda kw: kw.upper())
	return [{"label": Purify(html=kw), "value": kw} for kw in unique_keywords]


@app.callback(
	Output("visible-ids", "data", allow_duplicate=True),
	Output("images-container", "children"),
	Output("scale-max-width", "value"),
	Output("scale-max-height", "value"),
	Input("layout-state", "data"),
	State("scale-max-width", "value"),
	State("scale-max-height", "value"),
	prevent_initial_call=True,
	_allow_dynamic_callbacks=True
)
async def update_images(data, max_width, max_height):
	"""Update images display based on filters."""
	if not data:
		return no_update, [html.Div("No data available", className="text-center")], no_update, no_update

	if not data.get("results_available", True):
		match data.get("status", Status.ERROR.value).rstrip("."):
			case Status.STOPPED.value:
				return no_update, [html.Div("This run was stopped by the user or admin, please re-submit your query.", className="text-center")], no_update, no_update
			case Status.ERROR.value:
				return no_update, [html.Div("The results for this run are unavailable due to an error interrupting the pipeline. Please re-submit your query later.", className="text-center")], no_update, no_update

	all_subfigures = data.get("all_subfigures", [])

	if not all_subfigures:
		return no_update, html.Div("No articles/figures available.", className="text-center"), no_update, no_update

	# Create image grid
	image_items: list = [
		html.Div("No results match the selected filters.", id="filter-error", className="text-center", style={"display": "none"}),
	]
	for index, subfigure in enumerate(all_subfigures):
		figure = subfigure["figure"]
		article = subfigure["article"]

		x1, y1 = subfigure["x1"], subfigure["y1"]
		width, height = subfigure["width"], subfigure["height"]
		max_width = max(max_width, width)
		max_height = max(max_height, height)
		subfigure["article"] = article
		subfigure["figure"] = figure

		url = figure["url"]

		scale = 290 / max(width, height)

		image_items.append(
			dbc.Col(id=dict(type="subfigure", index=index, id=subfigure["id"]), children=[
				dbc.Card(className="mb-3", children=[
					html.Div(className="crop-container", children=[
						dbc.CardImg(src=url, alt="Sample Image", className="crop-image",
									style={
										"--x1": f"{x1:.2f}",
										"--y1": f"{y1:.2f}",
										"--scale": f"{scale:.4f}",
										"--width": f"{width:.4f}",
										"--height": f"{height:.4f}",
									}),
					]),
					dbc.CardBody([
						html.H6(subfigure.get("id", "Unknown"), className="card-title"),
						Purify(
							html=subfigure.get("caption", "No caption available"),
							className="text-muted"
						),
						html.Small(
							html.A(
								Purify(
									html=article.get("title", "Unknown Article")
								),
								href=article.get("url", "#"),
								target="_blank"
							) if article else "Unknown Article",
							className="card-text"
						)
					])
				])
			])
		)

	return all_subfigures, dbc.Row(image_items), max_width, max_height


app.clientside_callback(
	ClientsideFunction(
		namespace="clientside",
		function_name="filterImages"
	),
	Output("visible-ids", "data", allow_duplicate=True),
	Input("apply-filters", "n_clicks"),
	State("keyword-dropdown", "value"),
	State("keyword-type", "value"),
	State("classification-checklist", "value"),
	State("license-checkbox", "value"),
	State("layout-state", "data"),
	State("scale-min-width", "value"),
	State("scale-max-width", "value"),
	State("scale-min-height", "value"),
	State("scale-max-height", "value"),
	State("scale-threshold", "value"),
	prevent_initial_call=True,
	_allow_dynamic_callbacks=True,
)


app.clientside_callback(
	ClientsideFunction(
		namespace="clientside",
		function_name="update_ids_and_banner"
	),
	Output(dict(type="subfigure", index=ALL, id=ALL), "style"),
	Output("figure-results-header", "children"),
	Output("filter-error", "style"),
	Input("visible-ids", "data"),
	State(dict(type="subfigure", index=ALL, id=ALL), "id"),
	prevent_initial_call=True,
)


app.clientside_callback(
	ClientsideFunction(
		namespace="clientside",
		function_name="update_title"
	),
	Output("result-id-display", "draggable"),
	Input("result-id-display", "children")
)


app.clientside_callback(
	ClientsideFunction(
		namespace="clientside",
		function_name="updateImagePageHeight"
	),
	Output("images-container", "style"),
	Input("images-container", "children"),
	State("images-container", "style"),
)


# Fixes an issue with the padding on the slider
app.clientside_callback(
	ClientsideFunction(
		namespace="clientside",
		function_name="updateScalePadding"
	),
	Output("scale-threshold", "style"),
	Input("page-load", "n_intervals"),
	prevent_initial_call=True
)
