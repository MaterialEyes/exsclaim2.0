"""
Layout component - the results page with menu and figure display.
Converted from React Layout.js component.
"""

import dash_bootstrap_components as dbc

from .api_client import *

from exsclaim.api import Status
from certifi import where
from dash import html, dcc, callback, clientside_callback, Output, Input, State
from httpx import AsyncClient, Client
from re import sub
from typing import Dict, List, Any
from uuid import UUID
from ssl import create_default_context


def create_layout_component(result_id: UUID, base_url: str):
	"""
	Create the main layout component for the results page.

	Args:
		result_id (UUID): The result ID to fetch data for

	Returns:
		html.Div: Layout component
	"""
	return html.Div([
		# Store components for state management
		dcc.Store(id="layout-state", data={
			"results_id": str(result_id),
			"articles": [],
			"figures": [],
			"all_subfigures": [],
			"subfigures": [],
			"license": False,
			"classes": {
				"MC": True, "DF": True, "GR": True, "PH": True,
				"IL": True, "UN": True, "PT": True
			},
			"scales": {
				"threshold": 0, "minWidth": 0, "maxWidth": 1600,
				"minHeight": 0, "maxHeight": 1600
			},
			"keyword_type": "caption",
			"keyword": "",
			"articles_loaded": False,
			"figures_loaded": False,
			"subfigures_loaded": False,
			"figure_page": 1,
			"subfigure_page": 1
		}),

		# Interval component for polling API status
		dcc.Interval(
			id="api-polling-interval",
			interval=60_000
		),

		# Interval to fix the padding of the slider once the page loads
		dcc.Interval(
			id="page-load",
			max_intervals=1
		),

		# Loading component
		html.Div(id="loading-container", children=create_loading_component()),

		# Main content (hidden while loading)
		html.Div(id="main-content", style={"display": "none", "width": "95%"}, children=[
			dbc.Container([
				dbc.Row([
					# Left side - Search menu
					dbc.Col(width=4, children=[
						dbc.Card(color="primary", className="mb-3 label-column", children=[
							dbc.CardBody([
								html.H5("Menu", className="text-center text-white label-column")
							])
						]),
						create_search_page_component(base_url)
					]),

					# Right side - Images display
					dbc.Col(width=8, children=[
						dbc.Card(color="primary", className="mb-3 label-column", children=[
							dbc.CardBody([
								html.H5("Figure Results", className="text-center text-white label-column")
							])
						]),
						create_images_page_component()
					])
				])
			], fluid=True, style={
				"width": "95%",
				"padding": "20px",
				"margin": "20px",
				"justifyContent": "center",
				"alignItems": "center",
				"display": "flex"
			})
		])
	], id="layout")


def create_loading_component():
	"""Create loading component."""
	return dbc.Container([
		dbc.Row([
			dbc.Col([
				dcc.Loading(
					[html.Div("Loading results...", className="text-center")],
					color="#93fad9",
					fullscreen=True
				)
			], width=12, className="text-center")
		])
	], fluid=True)


def create_search_page_component(base_url):
	"""Create the search page component (left side menu)."""
	return html.Div(id="filter-components", style={"width": "100%"}, children=[
		# Result ID display
		create_result_id_component(),

		# Keywords section
		dbc.Card([
			dbc.CardBody([
				html.H6("Keywords", className="text-center text-white")
			])
		], color="info", className="mb-3 result-label"),
		create_keywords_component(),

		# Classification section
		dbc.Card([
			dbc.CardBody([
				html.H6("Classification", className="text-center text-white")
			])
		], color="info", className="mb-3 result-label"),
		create_classification_component(base_url),

		# License section
		dbc.Card([
			dbc.CardBody([
				html.H6("License", className="text-center text-white")
			])
		], color="info", className="mb-3 result-label"),
		create_license_component(),

		# Scale section
		dbc.Card([
			dbc.CardBody([
				html.H6("Scale", className="text-center text-white")
			])
		], color="info", className="mb-3 result-label"),
		create_scale_component(),

		# Submit button
		create_submit_component()
	])


def create_result_id_component():
	"""Create result ID display component."""
	return html.Div([
		dbc.Label("Result ID"),
		html.Div(id="result-id-display", className="form-control")
	], className="mb-3")


def create_keywords_component():
	"""Create keywords component."""
	return html.Div([
		dbc.Label("Subfigures containing keywords in:"),
		dbc.RadioItems(
			id="keyword-type",
			options=[
				{"label": "Subfigure Caption", "value": "caption"},
				{"label": "General Article", "value": "general"},
				{"label": "Article's Title", "value": "title"}
			],
			value="caption",
			inline=False,
			className="mb-2"
		),
		dcc.Dropdown(
			id="keyword-dropdown",
			placeholder="Select keywords...",
			multi=True,
			className="form-control"
		)
	], className="mb-3")


def create_classification_component(base_url):
	"""Create classification component."""
	ssl_context = create_default_context(cafile=where())
	with Client(verify=ssl_context) as client:
		response = client.get(f"{base_url}/classification_codes")
		if not response.is_success:
			raise ValueError(f"Could not get classification codes from the API: {response.text}.")
		codes = response.json()

	codes = [{"label": code["name"].replace("_", ' ').title(), "value": code["code"]} for code in codes]

	return html.Div([
		dbc.Checklist(
			id="classification-checklist",
			options=codes,
			value=tuple(map(lambda code: code["value"], codes)),
			# inline=True
		)
	], className="mb-3 classification-checklist")


def create_license_component():
	"""Create license component."""
	return html.Div([
		dbc.Checkbox(
			id="license-checkbox",
			label="Only Include Open Access",
			value=False
		)
	], className="mb-3")


def create_scale_component():
	"""Create scale component."""
	def get_pixel_adornment(_id:int):
		# TODO: Replace this with dbc.InputGroup (https://www.dash-bootstrap-components.com/docs/components/input_group/)
		return html.Div(["px"], key=f"pix-{_id}", className="px-unit")

	style = {"position": "relative"}
	kwargs = dict(
		type="number",
		inputmode="numeric",
		min=0,
		className="form-control mb-2"
	)
	return html.Div([
		dbc.Row([
			dbc.Col([
				dbc.Label("Min Width", html_for="scale-min-width"),
				dbc.Input(
					id="scale-min-width",
					value=0,
					**kwargs
				),
				get_pixel_adornment(1)
			], style=style),
			dbc.Col([
				dbc.Label("Max Width", html_for="scale-max-width"),
				dbc.Input(
					id="scale-max-width",
					value=1600,
					**kwargs
				),
				get_pixel_adornment(2)
			], style=style),
		]),
		dbc.Row([
			dbc.Col([
				dbc.Label("Min Height", html_for="scale-min-height"),
				dbc.Input(
					id="scale-min-height",
					value=0,
					**kwargs
				),
				get_pixel_adornment(3)
			], style=style),
			dbc.Col([
				dbc.Label("Max Height", html_for="scale-max-height"),
				dbc.Input(
					id="scale-max-height",
					value=1600,
					**kwargs
				),
				get_pixel_adornment(4)
			], style=style),
		]),
		dbc.Label("Specify confidence threshold;"),
		dcc.Slider(0, 1, 0.01,
				   id="scale-threshold",
				   value=0,
				   className="form-control mb-2 slider",
				   marks={f"{num/10:.1f}": "" for num in range(11)},
				   tooltip={
					   "placement": "top", "always_visible": False},
				   ),
	], className="mb-3")


def create_submit_component():
	"""Create submit component."""
	return dbc.Row([
		dbc.Col([
			html.Div([
				dbc.Button(
					"Apply Filters",
					id="apply-filters",
					className="button-link"
				)
			], className="mb-3")
		]),
		dbc.Col([
			html.Div([
				html.A(
					"Back to Query",
					id="back-to-query",
					className="button-link",
					href="/"
				)
			], className="mb-3")
		]),
	])


def create_images_page_component():
	"""Create the images page component (right side display)."""
	return html.Div([
		html.Div(id="images-container", children=[
			html.Div("No articles/figures available", className="text-center")
		])
	])


# Callbacks for API integration and layout functionality
@callback(
	[
		Output("layout-state", "data"),
		Output("api-polling-interval", "disabled"),
		Output("loading-container", "style"),
		Output("main-content", "style")
	],
	[Input("api-polling-interval", "n_intervals")],
	[
		State("layout-state", "data"),
		State("exsclaim-store", "data"),
	]
)
async def update_layout_state(n_intervals, current_data:dict, data):
	"""Update layout state by fetching data from API."""
	results_pending = {"display": "block"}, {"display": "none"}
	results_loaded = {"display": "none"}, {"display": "block"}

	if not current_data:
		return current_data, False, *results_pending

	result_id = current_data.get("results_id")
	fast_api_url = data["fast_api_url"]

	ssl_context = create_default_context(cafile=where())
	updated_data = current_data.copy()

	async with AsyncClient(verify=ssl_context) as client:
		# Check if results are ready
		match (status := await fetch_status(client, fast_api_url, result_id)):
			case Status.RUNNING:
				return current_data, False, *results_pending  # Still loading, return current state
			case Status.FINISHED:
				pass
			case Status.ERROR | Status.KILLED:
				updated_data.update({
					"status": status,
					"results_available": False,
					"articles_loaded": True,
					"figures_loaded": True,
					"subfigures_loaded": True
				})
				return updated_data, True, *results_loaded

		# Results are ready, fetch all data
		articles = await fetch_articles(client, fast_api_url, result_id)
		figures = await fetch_figures(client, fast_api_url, result_id)
		subfigures = await fetch_subfigures(client, fast_api_url, result_id)

	# Update the state
	all_subfigures = updated_data.get("all_subfigures", [])
	all_subfigures.extend(subfigures)
	updated_data.update({
		"results_available": True,
		"articles": articles,
		"figures": figures,
		"all_subfigures": all_subfigures,
		"subfigures": subfigures,
		"articles_loaded": True,
		"figures_loaded": True,
		"subfigures_loaded": True
	})

	articles_loaded = updated_data.get("articles_loaded", False)
	figures_loaded = updated_data.get("figures_loaded", False)
	subfigures_loaded = updated_data.get("subfigures_loaded", False)

	if articles_loaded and figures_loaded and subfigures_loaded:
		return updated_data, True, *results_loaded
	else:
		return updated_data, False, *results_pending


@callback(
	Output("result-id-display", "children"),
	Input("layout-state", "data"),
	prevent_initial_call=True
)
def update_result_id(data):
	"""Update result ID display."""
	if data and "results_id" in data:
		return data["results_id"]
	return ""


@callback(
	Output("keyword-dropdown", "options"),
	[Input("keyword-type", "value"),
	 Input("layout-state", "data")],
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
	unique_keywords = sorted(set(map(lambda kw: sub(r"[^a-zA-Z\d_-]", "", kw), keywords)), key=lambda kw: kw.upper())
	return [{"label": kw, "value": kw} for kw in unique_keywords]


@callback(
	Output("images-container", "children"),
	[
		Input("layout-state", "data"),
		Input("apply-filters", "n_clicks")
	],
	[
		State("keyword-dropdown", "value"),
		State("classification-checklist", "value"),
		State("license-checkbox", "value")
	],
	prevent_initial_call=True,
	_allow_dynamic_callbacks=True
)
async def update_images(data, n_clicks, keywords, classifications, license_only):
	"""Update images display based on filters."""
	if not data:
		return html.Div("No data available", className="text-center")

	if not data.get("results_available", True):
		match data.get("status", Status.ERROR):
			case Status.KILLED:
				return html.Div("This run was stopped by the user or admin, please re-submit your query.", className="text-center")
			case Status.ERROR:
				return html.Div("The results for this run are unavailable due to an error interrupting the pipeline. Please re-submit your query later.", className="text-center")

	subfigures = data.get("subfigures", [])
	figures = data.get("figures", [])
	articles = data.get("articles", [])

	if not subfigures:
		return html.Div("No articles/figures available.", className="text-center")

	# Apply filters
	filtered_subfigures = subfigures

	# Filter by keywords
	if keywords:
		filtered_subfigures = [
			sf for sf in filtered_subfigures
			if kw.lower() in sf.get("keywords", [])
			   or kw.lower() in sf.get("general", [])
			for kw in keywords
		]

	# Filter by classification
	if classifications:
		filtered_subfigures = filter(
			lambda subfigure: subfigure.get("classification_code") in classifications,
			filtered_subfigures
		)

	# Filter by license
	if license_only:
		filtered_subfigures = filter(
			lambda subfigure: subfigure.get("license", False),
			filtered_subfigures
		)

	filtered_subfigures = tuple(filtered_subfigures)
	if not filtered_subfigures:
		return html.Div("No results match the selected filters", className="text-center")

	# Create image grid
	image_items = []
	# figure_sizes = dict()
	for subfigure in filtered_subfigures:
		figure = next(filter(lambda figure: subfigure["figure_id"] == figure["id"], figures), None)
		article = dict()
		if figure:
			article = next(filter(lambda article: figure["article_id"] == article["id"], articles), article)

		x1, y1 = subfigure["x1"], subfigure["y1"]
		width, height = subfigure["width"], subfigure["height"]

		url = figure["url"]

		scale = 290 / max(width, height)

		image_items.append(
			dbc.Card([
				html.Div([
					dbc.CardImg(src=url, alt="Sample Image", className="crop-image",
								style={
									"--x1": f"{x1:.2f}",
									"--y1": f"{y1:.2f}",
									"--scale": f"{scale:.4f}",
									"--width": f"{width:.4f}",
									"--height": f"{height:.4f}",
								}),
				], className="crop-container"),
				dbc.CardBody([
					html.H6(subfigure.get("id", "Unknown"), className="card-title"),
					html.P(
						subfigure.get("caption", "No caption available"),
						className="text-muted"
					),
					html.Small(
						html.A(
							article.get("title", "Unknown"),
							href=article.get("url", "#"),
							target="_blank"
						) if article else "Unknown",
						className="card-text"
					)
				])
			], className="mb-3")
		)

	return dbc.Row([
		dbc.Col(image_item) for image_item in image_items
	])


clientside_callback(
	"""
	function updateImagePageHeight(images, style){
		const filter_components = document.querySelector("#filter-components");
		style = style !== undefined ? style : {};
		style.overflowX = "auto"; //hidden
	
		const children = images.props.children;
	
		if(typeof(children) !== "string" && images.props.children.length > 1){
			console.log(`Number of children: ${images.props.children.length} ${images.props.children}.`);
			style.overflowY = "scroll";
			style.maxHeight = filter_components.clientHeight;
		} else {
			delete style.overflowY;
		}

		return style;
	}
	""",
	Output("images-container", "style"),
	Input("images-container", "children"),
	State("images-container", "style"),
)


# Fixes an issue with the padding on the slider
clientside_callback(
	"""
	function updateScalePadding(value){
		const scale = document.querySelector("#scale-threshold");
		if(scale === undefined){ return; }

		scale.removeAttribute("style");

		return {};
	}
	""",
	Output("scale-threshold", "style"),
	Input("page-load", "n_intervals"),
	prevent_initial_call=True
)
