"""
Query component - the main form for EXSCLAIM queries.
Converted from React Query.js component.
"""

import dash_bootstrap_components as dbc
import httpx2

from dash import html, dcc, callback, Output, Input, State, clientside_callback, ClientsideFunction
from dash.exceptions import PreventUpdate
from re import compile
from typing import Optional


name_regex = compile(r"^[\w_\-]+$")


def get_llms() -> tuple[dict[str, dict[str, str | bool]], dict[str, bool], dict[str, bool]]:
	try:
		from ...caption import LLMMeta
	except ImportError:
		from exsclaim.caption import LLMMeta

	available_llms = dict()
	for cls in LLMMeta.classes:
		models = cls.available_models()
		if not models:
			continue
		available_llms[cls.__name__] = [dict(
			model_name=model_name,
			show_api_key=show_api_key,
			needs_api_key=needs_api_key,
			display_name=label if label is not None else model_name.title()
		) for model_name, show_api_key, needs_api_key, label in models]

	show_api_key = {llm["model_name"]: llm["show_api_key"] for models in available_llms.values() for llm in models}
	required_api_key = {llm["model_name"]: llm["needs_api_key"] for models in available_llms.values() for llm in models}

	return available_llms, show_api_key, required_api_key


def create_query_component(available_llms, debounce=True):
	"""
	Create the main query form component.
	
	Args:
		available_llms (dict[str, dict[str, str | bool]]): List of available LLM models

	Returns:
		dbc.Container: Query form component
	"""
	return dbc.Container(fluid=True, style={
		"width": "95%",
		"padding": "20px",
		"margin": "20px",
		"justifyContent": "center",
		"display": "flex",
		"flex-direction": "column",
	}, children=[
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
					html.H4([
						"Input Query",
						html.Button(
							html.Img(
								src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDMwMCAzMDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+Cgk8Y2lyY2xlIGN4PSI1MCUiIGN5PSI1MCUiIHI9IjUwJSIgZmlsbD0icmdiYSgxMywgMTEwLCAyNTMsIDEpIiAvPgoJPHJlY3QgeD0iMjAlIiB5PSIzMCUiIHdpZHRoPSI2MCUiIGhlaWdodD0iOCUiIHJ4PSIzJSIgZmlsbD0icmdiYSgyNTUsIDI1NSwgMjU1LCAxKSIgLz4KCTxyZWN0IHg9IjIwJSIgeT0iNDYuNjclIiB3aWR0aD0iNjAlIiBoZWlnaHQ9IjglIiByeD0iMyUiIGZpbGw9InJnYmEoMjU1LCAyNTUsIDI1NSwgMSkiIC8+Cgk8cmVjdCB4PSIyMCUiIHk9IjYzLjMzJSIgd2lkdGg9IjYwJSIgaGVpZ2h0PSI4JSIgcng9IjMlIiBmaWxsPSJyZ2JhKDI1NSwgMjU1LCAyNTUsIDEpIiAvPgo8L3N2Zz4K",
								alt="Menu for advanced options.",
								style=dict(
									height="60px",
								)
							),
							style={
								"background-color": "rgba(13, 110, 253, 0)",
								"border-width": "0",
								"height": "100%",
								"position": "absolute",
								"top": 0,
								"right": "10px",
								"margin": 0
							},
							id="advanced-options-button",
						)
					], className="text-center text-white")
				]),
			]),

			# Left column - Basic inputs
			dbc.Col(width=6, children=[
				create_output_name_component(debounce=debounce),
				create_num_articles_component(debounce=debounce),
				create_input_term_component(debounce=debounce),
				create_input_synonyms_component(debounce=debounce),
				create_inheritance_component(),
			]),

			# Right column - Advanced inputs
			dbc.Col(width=6, children=[
				create_journal_family_component(),
				create_sort_by_component(),
				create_open_access_component(),
				create_save_methods_component(),
				create_model_component(available_llms, debounce=debounce),
			])
		]),

		# Advanced controls for the pipeline
		dbc.Collapse([
			html.Hr(style=dict(color="rgb(255, 255, 255)")),
			dbc.Row([
				dbc.Col(width=6, children=[
					create_ntfy_component(),
				]),
				dbc.Col(width=6, children=[]),
			]),
			],
			id="advanced-options",
			is_open=False,
		),

		dbc.Row([
			dbc.Col(width=6),
			dbc.Col(width=6, children=[
				create_submit_button_component(),
			]),
		])
	])


def create_output_name_component(debounce=True):
	"""Create output name input component."""
	return html.Div([
		dbc.Tooltip(
			"Allowed characters: letters, numbers, '-', '_'.",
			id="output-name-tooltip",
			target="output-name",
			is_open=False,
		),
		dbc.Label(
			"Output Name *",
			html_for="output-name",
		),
		dbc.Input(
			id="output-name",
			type="text",
			pattern=r"[\w_\-]+",
			placeholder="Enter output file name...",
			className="form-control",
			debounce=debounce,
			required=True
		)
	], className="mb-3")


def create_num_articles_component(debounce=True):
	"""Create number of articles input component."""
	return html.Div([
		dbc.Tooltip(
			"Number of articles must be between 1 and 200 (inclusive).",
			id="num-articles-tooltip",
			target="num-articles",
			is_open=False,
		),
		dbc.Label(
			"Max Number of Articles *",
			html_for="num-articles",
		),
		dbc.Input(
			id="num-articles",
			type="number",
			min=1,
			max=200,
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
		dbc.Tooltip(
			"The search term must have 1 non-whitespace character.",
			id="input-term-tooltip",
			target="input-term",
			is_open=False,
		),
		dbc.Label(
			"Search Term *",
			html_for="input-term",
		),
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
		dbc.Label(
			"Synonyms",
			html_for="input-synonyms",
		),
		dbc.Textarea(
			id="input-synonyms",
			placeholder="Enter synonyms (one per line)...",
			className="form-control",
			rows=3,
			debounce=debounce
		)
	], className="mb-3")


def create_inheritance_component():
	return html.Div([
		dbc.Label(
			"Extend Results From:",
			html_for="base-run-id"
		),
		dcc.Dropdown(
			id="base-run-id",
			placeholder="Add results from run...",
			className="form-control",
			multi=False,
		)
	])


@callback(
	Output("base-run-id", "options"),
	Output("base-run-id", "value"),
	State("exsclaim-store", "data")
)
async def load_previous_runs(data):
	try:
		async with httpx2.AsyncClient(base_url=data["fast_api_url"], timeout=30) as client:
			response = await client.get("/previous_runs?return_values=id&return_values=name")
			runs = response.json()
	except httpx2.HTTPError as e:
		print(f"{e=}", flush=True)
		return [], None

	options = [None] * (len(runs) + 1)
	options[0] = {"value": None, "label": "-"}

	for i, run in enumerate(runs, start=1):
		options[i] = {"value": str(run["id"]), "label": f"{run['name']} ({run['id']})"}

	return options, None


DAGGER = "\u2020"


def create_journal_family_component():
	"""Create journal family dropdown component."""
	try:
		from ...journals import JournalFamily, JournalFamilyDynamic
	except ImportError:
		from exsclaim.journals import JournalFamily, JournalFamilyDynamic

	options = [None] * len(JournalFamily)
	for i, (name, cls) in enumerate(JournalFamily):
		option = {"label": name, "value": name}
		if JournalFamilyDynamic in cls.__bases__ or name.lower() == "wiley":
			option["label"] = html.Div([name, html.Sup(DAGGER)])

		if name.lower() == "wiley":
			option["disabled"] = True

		options[i] = option

	initial_value = "Nature"

	return html.Div([
		dbc.Label(
			"Journal Family *",
			html_for="journal-family",
		),
		dcc.Dropdown(
			id="journal-family",
			options=options,
			value=initial_value,
			className="form-control",
			persistence=True,
			persistence_type="local",
		),
		html.P(
			f"{DAGGER} The selected Journal Family's website is protected by CloudFlare, so there is a higher chance of information not being retrieved for this run.",
			id="journal-family-warning",
			hidden=True
		)
	], className="mb-3")


def create_sort_by_component():
	"""Create sort by radio buttons component."""
	return html.Div([
		dbc.Label("Sort By *"),
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
			value=True
		)
	], className="mb-3")


def create_model_component(available_llms, debounce=True):
	"""Create model selection component."""
	options = []
	for i, (provider, llms) in enumerate(available_llms.items()):
		options.append(dict(value=provider, label=provider, disabled=True))
		options.extend((dict(value=llm["model_name"], label=llm["display_name"]) for llm in llms))

		# dbc.Select currently doesn't support html.Option and html.Optgroup
		# options[i] = html.Optgroup(
		# 	label=provider,
		# 	children=[html.Option(value=llm["model_name"], label=llm["display_name"]) for llm in llms]
		# )

	if "LlamaCPP" in available_llms and len(available_llms["LlamaCPP"]) > 0:
		default_llm = available_llms["LlamaCPP"][0]["model_name"]
	elif "Ollama" in available_llms and len(available_llms["Ollama"]) > 0:
		default_llm = available_llms["Ollama"][0]["model_name"]
	else:
		default_llm = options[0]["value"]

	return html.Div([
		dbc.Label("Model *", html_for="model-select"),
		dbc.Select(
			id="model-select",
			options=options,
			value=default_llm,
			className="form-control",
			valid=True,
			invalid=False,
			required=True,
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


def create_save_methods_component():
	"""Create save_methods component."""
	methods = (
		dict(label="Subfigures", value="subfigures"),
		dict(label="Visualization", value="visualization"),
		dict(label="Bounding Boxes", value="boxes"),
		dict(label="Upload to Database", value="postgres", disabled=True),
		dict(label="CSV", value="csv", disabled=True),
	)

	return html.Div([
		dbc.Label("Save Methods:"),
		dbc.Checklist(
			id="save-methods",
			options=methods,
			value=tuple(map(lambda code: code["value"], methods)),
		)
	], className="mb-3 exsclaim-checklist")


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


def create_ntfy_component(debounce=True):
	"""Creates the components that would correspond to NTFY information."""
	return html.Div([
		dbc.Tooltip(
			html.P([
				"The URL to send notifications to your ",
				html.A(
					"NTFY",
					href="https://docs.ntfy.sh/",
					target="blank"
				),
				" server."

			]),
			id="ntfy-url-tooltip",
			target="ntfy-url",
			is_open=False,
		),
		dbc.Label(
			[
				html.A(
					"NTFY",
					href="https://docs.ntfy.sh/",
					target="blank"
				),
				" URL:"
			],
			html_for="ntfy-url",
		),
		dbc.Input(
			id="ntfy-url",
			type="text",
			placeholder="https://ntfy.sh/exsclaim",
			className="form-control",
			required=False,
			debounce=debounce
		),
		dbc.Tooltip(
			"The priority of the message in your server.",
			id="ntfy-priority-tooltip",
			target="ntfy-priority",
			is_open=False,
		),
		dbc.Label(
			[
				html.A(
					"NTFY",
					href="https://docs.ntfy.sh/publish/?h=priority#message-priority",
					target="blank"
				),
				" Priority:"
			],
			html_for="ntfy-priority",
		),
		dbc.Input(
			id="ntfy-priority",
			type="number",
			placeholder="3",
			max=5,
			min=1,
			className="form-control",
			required=False,
			debounce=debounce
		)
	], className="mb-3")


# Callbacks for form handling
@callback(
	Output("advanced-options", "is_open"),
	Input("advanced-options-button", "n_clicks"),
	State("advanced-options", "is_open"),
)
def collapse_advanced_options(n_clicks, is_open):
	if n_clicks is None:
		raise PreventUpdate
	return not is_open


@callback(
	[
		Output("model-key", "placeholder"),
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
def show_api_key(selected_model: str, key: Optional[str], data) -> tuple[bool, bool, bool, bool, dict[str, str]]:
	show_key = data["show_api_key"].get(selected_model, True)
	needs_key = data["required_api_key"].get(selected_model, False)

	disabled = not show_key		# The input is disabled if the LLM says don't show it

	required = needs_key
	placeholder = "API Key *" if required else "API Key"
	style = dict(display="block" if show_key else "none")

	valid = True
	invalid = False

	if needs_key and (key is None or not key.strip()):
		valid = False
		invalid = True

	return placeholder, disabled, valid, invalid, required, style


@callback(
	[
		Output("output-name", "valid"),
		Output("output-name", "invalid"),
		Output("output-name-tooltip", "is_open"),
	],
	[
		Input("output-name", "value")
	],
	prevent_initial_call=True
)
def valid_output_name(name: Optional[str]) -> tuple[bool, bool, bool]:
	if name is None:
		return False, True, True
	valid_name = name_regex.match(name) is not None

	return valid_name, not valid_name, not valid_name


@callback(
	[
		Output("num-articles", "valid"),
		Output("num-articles", "invalid"),
		Output("num-articles-tooltip", "is_open"),
	],
	[
		Input("num-articles", "value")
	],
	prevent_initial_call=True
)
def valid_number_of_articles(num_articles: Optional[int]) -> tuple[bool, bool, bool]:
	if num_articles is None:
		return False, True, True

	valid_num = 1 <= num_articles <= 200

	return valid_num, not valid_num, not valid_num


@callback(
	[
		Output("input-term", "valid"),
		Output("input-term", "invalid"),
		Output("input-term-tooltip", "is_open"),
	],
	[
		Input("input-term", "value")
	],

	prevent_initial_call=True
)
def valid_search_term(search_term: Optional[str]) -> tuple[bool, bool, bool]:
	"""Disable submit button if no search term is provided."""
	if search_term is None:
		return False, True, True

	valid_name = bool(search_term.strip())
	return valid_name, not valid_name, not valid_name


@callback(
	Output("journal-family-warning", "hidden"),
	Input("journal-family", "value"),
	State("journal-family", "options"),
)
def show_journal_warning(journal_family: str, options) -> bool:
	option = next(filter(lambda option: option["value"] == journal_family, options), None)
	if option is None:
		return False

	if isinstance(option["label"], str):
		return True

	children = option["label"]["props"].get("children", ())
	for child in children:
		if isinstance(child, str):
			continue
		if child.get("props", dict()).get("children") == DAGGER:
			return False

	return DAGGER not in option["label"]


@callback(
	Output("submit-query", "disabled"),
	[
		Input("output-name", "invalid"),
		Input("num-articles", "invalid"),
		Input("input-term", "invalid"),
		Input("input-synonyms", "invalid"),
		Input("model-key", "invalid"),
	],
)
def enable_submit_button(*invalidity):
	# If any of the elements are invalid, the button is set to disabled=True, so users won't be able to select it
	return any(invalidity)


clientside_callback(
	ClientsideFunction(
		namespace="query",
		function_name="submit_query"
	),
	[
		Output("results-finished", "disabled"),
		Output("notification", "is_open"),
		Output("notification-html", "html"),
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
		State("base-run-id", "value"),
		State("open-access", "value"),
		State("model-select", "value"),
		State("model-key", "value"),
		State("save-methods", "value"),
		State("ntfy-url", "value"),
		State("ntfy-priority", "value"),
	],
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="query",
		function_name="check_results_status"
	),
	[
		Output("new_url", "href"),
		Output("new_url", "refresh")
	],
	Input("results-finished", "n_intervals"),
	[
		State("exsclaim-store", "data"),
		# State("new_url", "href")
	],
	prevent_initial_call=True
)
