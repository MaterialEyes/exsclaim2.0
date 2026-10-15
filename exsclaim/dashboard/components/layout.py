"""
Layout component - the results page with menu and figure display.
Converted from React Layout.js component.
"""

import dash_bootstrap_components as dbc
import httpx2

from dash import html, dcc
from uuid import UUID


def create_layout_component(result_id: UUID, base_url: str, public_api_url: str):
	"""
	Create the main layout component for the results page.

	Args:
		result_id (UUID): The result ID to fetch data for
		base_url (str): The API's URL

	Returns:
		html.Div: Layout component
	"""
	return html.Div(id="layout", children=[
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

		dcc.Store(
			id="visible-ids"
		),

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
			dbc.Container(fluid=True, style={
					"width": "95%",
					"padding": "20px",
					"margin": "20px",
					"justifyContent": "center",
					"alignItems": "center",
					"display": "flex"
				}, children=[
				dbc.Row([
					# Left side - Search menu
					dbc.Col(width=4, children=[
						dbc.Card(color="primary", className="mb-3 label-column", children=[
							dbc.CardBody([
								html.H5("Menu", className="text-center text-white label-column")
							])
						]),
						create_search_page_component(base_url, public_api_url, result_id)
					]),

					# Right side - Images display
					dbc.Col(width=8, children=[
						dbc.Card(color="primary", className="mb-3 label-column", children=[
							dbc.CardBody([
								html.H5(
									"Figure Results",
									id="figure-results-header",
									className="text-center text-white label-column"
								)
							])
						]),
						create_images_page_component()
					])
				])
			])
		])
	])


def create_loading_component():
	"""Create loading component."""
	return dcc.Loading(
		# html.Div("Loading results...", className="text-center"),
		color="#93fad9",
		display="hide",
		fullscreen=False,
		type="circle"
	)


def create_search_page_component(base_url, public_api_url: str, result_id: UUID):
	"""Create the search page component (left side menu)."""
	return html.Div(id="filter-components", style={"width": "100%"}, children=[
		# Result ID display
		create_result_id_component(result_id),

		# Download Button
		create_download_component(public_api_url, result_id),

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


def create_result_id_component(result_id: UUID):
	"""Create result ID display component."""
	return html.Div([
		dbc.Label("Result ID"),
		html.Div(str(result_id), id="result-id-display", className="form-control")
	], className="mb-3")


def create_download_component(public_api_url: str, result_id: UUID):
	return html.A(
		href=f"{public_api_url}/results/{result_id}",
		children=[
			dbc.Card([
				dbc.CardBody([
					html.H6("Download Results", className="text-center", style={"color": "var(--text)"})
				])
			], color="info", outline=True, className="mb-3", style={"background-color": "#00000000"}),
		],
	)


def create_keywords_component():
	"""Create keywords component."""
	return html.Div([
		dbc.Label("Subfigures containing keywords in:"),
		dbc.RadioItems(
			id="keyword-type",
			options=[
				{"label": "Subfigure Caption", "value": "caption"},
				# {"label": "General Article", "value": "general"},
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
	with httpx2.Client() as client:
		response = client.get(f"{base_url}/classification_codes")
		if not response.is_success:
			raise ValueError(f"Could not get classification codes from the API: {response.text}")
		codes = response.json()

	codes = [{"label": code["name"].replace("_", ' ').title(), "value": code["code"]} for code in codes]

	return html.Div([
		dbc.Checklist(
			id="classification-checklist",
			options=codes,
			value=tuple(map(lambda code: code["value"], codes)),
		)
	], className="mb-3 exsclaim-checklist")


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
	def create_input(text: str, html_id: str, num: int, value: int = 0) -> dbc.Col:
		return dbc.Col(children=[
			dbc.Label(text, html_for=html_id),
			dbc.InputGroup(className="mb-2 image_size_filter", children=[
				dbc.Input(
					id=html_id,
					value=value,
					type="number",
					inputmode="numeric",
					min=0,
					className="form-control mb-2"
				),
				dbc.InputGroupText("px", key=f"pix-{num}", className="mb-2")
			]),
		])

	return html.Div([
		dbc.Row([
			create_input("Min Width", "scale-min-width", 1, value=0),
			create_input("Max Width", "scale-max-width", 2, value=1_600)
		]),
		dbc.Row([
			create_input("Min Height", "scale-min-height", 3, value=0),
			create_input("Max Height", "scale-max-height", 4, value=1_600),
		]),
		dbc.Label("Specify minimum confidence threshold:"),
		dcc.Slider(0, 1, 0.01,
				   id="scale-threshold",
				   value=0,
				   className="form-control mb-2 slider",
				   marks={f"{num / 10:.1f}": "" for num in range(11)},
				   tooltip={"placement": "top", "always_visible": False},
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
	return dbc.Container(id="images-container", children=[
		html.Div("No articles/figures available", className="text-center")
	])
