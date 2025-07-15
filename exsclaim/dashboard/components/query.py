"""
Query component - the main form for EXSCLAIM queries.
Converted from React Query.js component.
"""

from httpx import Client
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Output, Input, State


def create_query_component(journal_families, available_llms):
	"""
	Create the main query form component.
	
	Args:
		journal_families (list): List of available journal families
		available_llms (list): List of available LLM models

	Returns:
		dbc.Container: Query form component
	"""
	return dbc.Container([
		# Form content
		dbc.Row([
			# Header box
			dbc.Card(color="primary", className="mb-3 label-column", children=[
				dbc.CardBody([
					html.H4("Input Query", className="text-center text-white")
				])
			]),

			# Left column - Basic inputs
			dbc.Col(width=6, children=[
				create_output_name_component(),
				create_num_articles_component(),
				create_input_term_component(),
				create_input_synonyms_component(),
			]),
			
			# Right column - Advanced inputs
			dbc.Col([
				create_journal_family_component(journal_families),
				create_sort_by_component(),
				create_open_access_component(),
				create_model_component(available_llms),
				create_submit_button_component(),
			], width=6)
		])
	], fluid=True, style={
		"width": "95%",
		"height": "450px",
		"padding": "20px",
		"margin": "20px",
		"justifyContent": "center",
		"display": "flex"
	})


def create_output_name_component():
	"""Create output name input component."""
	return html.Div([
		dbc.Label("Output Name"),
		dbc.Input(
			id="output-name",
			type="text",
			placeholder="Enter output file name...",
			className="form-control"
		)
	], className="mb-3")


def create_num_articles_component():
	"""Create number of articles input component."""
	return html.Div([
		dbc.Label("Max Number of Articles"),
		dbc.Input(
			id="num-articles",
			type="number",
			min=0,
			inputmode="numeric",
			placeholder="Enter number of articles...",
			className="form-control"
		)
	], className="mb-3")


def create_input_term_component():
	"""Create search term input component."""
	return html.Div([
		dbc.Label("Search Term *"),
		dbc.Input(
			id="input-term",
			type="text",
			placeholder="Enter search term...",
			className="form-control",
			required=True
		)
	], className="mb-3")


def create_input_synonyms_component():
	"""Create synonyms input component."""
	return html.Div([
		dbc.Label("Synonyms"),
		dbc.Textarea(
			id="input-synonyms",
			placeholder="Enter synonyms (one per line)...",
			className="form-control",
			rows=3
		)
	], className="mb-3")


def create_journal_family_component(journal_families):
	"""Create journal family dropdown component."""
	options = [{"label": family, "value": family} for family in journal_families]
	
	return html.Div([
		dbc.Label("Journal Family"),
		dcc.Dropdown(
			id="journal-family",
			options=options,
			value=journal_families[0] if journal_families else "Nature",
			className="form-control"
		)
	], className="mb-3")


def create_sort_by_component():
	"""Create sort by radio buttons component."""
	return html.Div([
		dbc.Label("Sort By"),
		dbc.RadioItems(
			id="sort-by",
			options=[
				{"label": "Relevant", "value": "relevant"},
				{"label": "Recent", "value": "recent"},
				# {"label": "Cited", "value": "cited"}
			],
			value="relevant",
			inline=True
		)
	], className="mb-3")


def create_open_access_component():
	"""Create open access checkbox component."""
	return html.Div([
		dbc.Checkbox(
			id="open-access",
			label="Open Access Only",
			value=False
		)
	], className="mb-3")


def create_model_component(available_llms):
	"""Create model selection component."""
	options = [
		{"label": llm["display_name"], "value": llm["model_name"]}
		for llm in available_llms
	]
	
	return html.Div([
		dbc.Label("Model"),
		dcc.Dropdown(
			id="model-select",
			options=options,
			value=available_llms[0]["model_name"] if available_llms else "llama3.2",
			className="form-control"
		),
		dbc.Input(
			id="model-key",
			type="password",
			placeholder="API Key",
			className="form-control mt-2"
		)
	], className="mb-3")


def create_submit_button_component():
	"""Create submit button component."""
	return html.Div([
		dbc.Button(
			"Submit",
			id="submit-query",
			className="button-link",
			size="lg",
			style={"width": "200px"}
		)
	], className="mb-3")


# Callbacks for form handling
@callback(
	[
		Output("model-key", "disabled"),
		Output("model-key", "required"),
		Output("model-key", "style")
	],
	Input("model-select", "value"),
	State("exsclaim-store", "data")
)
def show_api_key(selected_model:str, data) -> tuple[bool, bool, dict[str, str]]:
	needs_key = data["show_api_key"].get(selected_model, True)

	disabled = not needs_key
	required = needs_key
	style = dict(display="block" if needs_key else "none")

	return disabled, required, style


@callback(
	Output("submit-query", "disabled"),
	Input("input-term", "value"),
	prevent_initial_call=True
)
def toggle_submit_button(term:str) -> bool:
	"""Disable submit button if no search term is provided."""
	return not term or term.strip() == ""


@callback(
	[
		Output("notification", "is_open"),
		Output("notification-message", "value"),
		Output("notification", "color")
	],
	[
		Input("exsclaim-store", "data"),
		Input("submit-query", "n_clicks")
	],
	[
		State("output-name", "value"),
		State("journal-family", "value"),
		State("num-articles", "value"),
		State("sort-by", "value"),
		State("input-term", "value"),
		State("input-synonyms", "value"),
		State("open-access", "value"),
		State("model-select", "value"),
		State("model-key", "value")
	],
	prevent_initial_call=True
)
def handle_submit_query(stored_data, output_name, journal_family, num_articles,
					   sort_by, term, synonyms, open_access, model, model_key):
	"""Handle form submission and API call."""
	if not n_clicks:
		return False, "", "success"
	
	# Validate required fields
	if not term or term.strip() == "":
		return True, "A search term is required.", "danger"
	
	# Process synonyms
	synonyms_list = []
	if synonyms:
		synonyms_list = [s.strip() for s in synonyms.split('\n')]
	
	# Prepare data for API
	input_data = {
		"name": output_name or "",
		"journal_family": journal_family or "Nature",
		"maximum_scraped": num_articles or 0,
		"sortby": sort_by or "relevant",
		"term": term.strip(),
		"synonyms": synonyms_list,
		"save_format": ["postgres"],
		"open_access": open_access or False,
		"llm": model or "llama3.2",
		"model_key": model_key or ""
	}

	api_url = stored_data["fast_api_url"]

	with Client() as client:
		response = client.post(f"{api_url}/query", json=input_data, headers={
			"Accept": "application/json",
			"Access-Control-Allow-Origin": "*",
			"Access-Control-Allow-Headers": "Accept, Content-Type, mode",
			"Content-Type": "application/json",
			"mode": "no-cors"
		})

		if response.ok:
			json = response.json()
			result_id = json["result_id"]
		else:
			print(response.text)

	return True, f"Query: <a href=\"/status/{result_id}\">{result_id}</a> was submitted to the server. This page will automatically update when the results are available.", "success"
