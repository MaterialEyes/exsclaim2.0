"""
Query component - the main form for EXSCLAIM queries.
Converted from React Query.js component.
"""

import dash_bootstrap_components as dbc

from .api_client import fetch_status
from dash import html, dcc, callback, Output, Input, State
from exsclaim.api import Status
from httpx import AsyncClient
from typing import Optional


def create_query_component(journal_families, available_llms, debounce=True):
	"""
	Create the main query form component.
	
	Args:
		journal_families (list): List of available journal families
		available_llms (list): List of available LLM models

	Returns:
		dbc.Container: Query form component
	"""
	return dbc.Container([
		# Interval to check if the results are ready
		dcc.Interval(
			id="results-finished",
			interval=60_000,
			disabled=True,
		),

		dcc.Location(
			id="new_url",
			refresh=True
		),

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
				create_output_name_component(debounce=debounce),
				create_num_articles_component(debounce=debounce),
				create_input_term_component(debounce=debounce),
				create_input_synonyms_component(debounce=debounce),
			]),
			
			# Right column - Advanced inputs
			dbc.Col([
				create_journal_family_component(journal_families),
				create_sort_by_component(),
				create_open_access_component(),
				create_model_component(available_llms, debounce=debounce),
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


def create_output_name_component(debounce=True):
	"""Create output name input component."""
	return html.Div([
		dbc.Label("Output Name *"),
		dbc.Input(
			id="output-name",
			type="text",
			placeholder="Enter output file name...",
			className="form-control",
			debounce=debounce,
			required=True
		)
	], className="mb-3")


def create_num_articles_component(debounce=True):
	"""Create number of articles input component."""
	return html.Div([
		dbc.Label("Max Number of Articles *"),
		dbc.Input(
			id="num-articles",
			type="number",
			min=0,
			value=5,
			inputmode="numeric",
			placeholder="Enter number of articles...",
			className="form-control",
			debounce=debounce,
			required=True
		)
	], className="mb-3")


def create_input_term_component(debounce=True):
	"""Create search term input component."""
	return html.Div([
		dbc.Label("Search Term *"),
		dbc.Input(
			id="input-term",
			type="text",
			placeholder="Enter search term...",
			className="form-control",
			required=True,
			debounce=debounce
		)
	], className="mb-3")


def create_input_synonyms_component(debounce=True):
	"""Create synonyms input component."""
	return html.Div([
		dbc.Label("Synonyms"),
		dbc.Textarea(
			id="input-synonyms",
			placeholder="Enter synonyms (one per line)...",
			className="form-control",
			rows=3,
			debounce=debounce
		)
	], className="mb-3")


def create_journal_family_component(journal_families):
	"""Create journal family dropdown component."""
	options = [{"label": family, "value": family} for family in journal_families]
	
	return html.Div([
		dbc.Label("Journal Family *"),
		dbc.Select(
			id="journal-family",
			options=options,
			value=journal_families[0] if journal_families else "Nature",
			className="form-control",
			valid=True,
			invalid=False,
			persistence=True,
			persistence_type="local"
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


def create_model_component(available_llms, debounce=True):
	"""Create model selection component."""
	options = [
		{"label": llm["display_name"], "value": llm["model_name"]}
		for llm in available_llms
	]
	
	return html.Div([
		dbc.Label("Model *", html_for="model-select"),
		dbc.Select(
			id="model-select",
			options=options,
			value=available_llms[0]["model_name"] if available_llms else "llama3.2",
			className="form-control",
			valid=True,
			invalid=False,
			persistence=True,
			persistence_type="local"
		),
		dbc.Label(id="api-key-label", html_for="model-key"),
		dbc.Input(
			id="model-key",
			type="password",
			placeholder="API Key *",
			className="form-control mt-2",
			debounce=debounce,
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
		Output("api-key-label", "disabled"),
		Output("model-key", "disabled"),
		Output("model-key", "valid"),
		Output("model-key", "invalid"),
		Output("model-key", "required"),
		Output("model-key", "style")
	],
	[
		Input("model-select", "value"),
		Input("model-key", "value")
	],
	[
		State("exsclaim-store", "data")
	]
)
def show_api_key(selected_model:str, key:Optional[str], data) -> tuple[bool, bool, bool, bool, bool, dict[str, str]]:
	needs_key = data["show_api_key"].get(selected_model, True)

	disabled = not needs_key
	required = needs_key
	style = dict(display="block" if needs_key else "none")

	if not needs_key:
		return disabled, disabled, True, False, False, style

	if needs_key and key is not None and key.strip():
		return True, True, True, False, True, style

	return disabled, disabled, False, True, required, style


@callback(
	[
		Output("output-name", "valid"),
		Output("output-name", "invalid"),
	],
	[
		Input("output-name", "value")
	]
)
def valid_output_name(name: Optional[str]) -> tuple[bool, bool]:
	valid_name = name and bool(name.strip())

	return valid_name, not valid_name


@callback(
	[
		Output("num-articles", "valid"),
		Output("num-articles", "invalid"),
	],
	[
		Input("num-articles", "value")
	]
)
def valid_number_of_articles(num_articles: Optional[int]) -> tuple[bool, bool]:
	if num_articles is None:
		return False, True

	valid_num = num_articles > 0

	return valid_num, not valid_num


@callback(
	[
		Output("input-term", "valid"),
		Output("input-term", "invalid"),
	],
	[
		Input("input-term", "value")
	]
)
def valid_search_term(search_term: Optional[int]) -> tuple[bool, bool]:
	"""Disable submit button if no search term is provided."""

	# These have the same requirements as of now
	return valid_output_name(search_term)


@callback(
	Output("submit-query", "disabled"),
	[
		Input("output-name", "invalid"),
		Input("num-articles", "invalid"),
		Input("sort-by", "invalid"),
		Input("input-term", "invalid"),
		Input("input-synonyms", "invalid"),
		Input("open-access", "invalid"),
		Input("model-key", "invalid"),
	],
)
def enable_submit_button(*invalidity):
	# If any of the elements are invalid, the button is set to disabled=True, so users won't be able to select it
	return any(invalidity)


@callback(
	[
		Output("results-finished", "disabled"),
		Output("notification", "is_open"),
		Output("notification", "children"),
		Output("notification", "color"),
		Output("exsclaim-store", "data"),
	],
	[
		Input("submit-query", "n_clicks")
	],
	[
		State("exsclaim-store", "data"),
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
async def handle_submit_query(n_clicks, stored_data, output_name, journal_family, num_articles,
					   sort_by, term, synonyms, open_access, model, model_key):
	"""Handle form submission and API call."""
	if not n_clicks:
		return True, False, "", "success", stored_data
	
	# Validate required fields
	if not term or term.strip() == "":
		return True, True, "A search term is required.", "danger", stored_data

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

	async with AsyncClient() as client:
		response = await client.post(f"{api_url}/query", json=input_data, headers={
			"Accept": "application/json",
			"Access-Control-Allow-Origin": "*",
			"Access-Control-Allow-Headers": "Accept, Content-Type, mode",
			"Content-Type": "application/json",
		})

		if not response.is_success:
			return True, True, response.text, "error", stored_data

		json = response.json()
		result_id = json["result_id"]
		stored_data["query_id"] = result_id

	status_link = f"{stored_data['public_fastapi_url']}/status/{result_id}"
	return False, True, html.P([
			"Query: ",
			html.A(result_id, href=f"/results/{result_id}"),
			" was submitted to the server. This page will automatically update when the results are available. You can also check the run's status at ",
			html.A(status_link, href=status_link, target="blank"),
			"."
		]), "success", stored_data


@callback(
	[
		Output("new_url", "href"),
		Output("new_url", "refresh")
	],
	Input("results-finished", "n_intervals"),
	[
		State("exsclaim-store", "data"),
		State("new_url", "href")
	],
	prevent_initial_call=True
)
async def check_results_status(n_intervals, data, current_url):
	query_id = data["query_id"]
	fast_api_url = data["fast_api_url"]

	async with AsyncClient() as client:
		match await fetch_status(client, fast_api_url, query_id):
			case Status.RUNNING:
				# Not ready
				return current_url, False
			case Status.FINISHED | Status.ERROR | Status.KILLED:
				return f"/results/{query_id}", True
