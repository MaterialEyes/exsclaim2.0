import httpx2

from dash import ctx, Output, Input, State, get_app, ClientsideFunction, no_update
from dash.exceptions import PreventUpdate
from exsclaim import llms
from exsclaim.dashboard.components.query import DAGGER
from typing import Optional


app = get_app()


@app.callback(
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


@app.callback(
	Output("advanced-options", "is_open"),
	Input("advanced-options-button", "n_clicks"),
	State("advanced-options", "is_open"),
)
def collapse_advanced_options(n_clicks, is_open):
	if n_clicks is None:
		raise PreventUpdate
	return not is_open


@app.callback(
	Output("model-select", "options"),
	Output("model-api-requirement", "is_open"),
	Output("model-select", "value"),
	Output("model-key", "value"),
	Input("model-provider", "value"),
	Input("model-key", "value"),
	State("exsclaim-store", "data")
)
def update_model_list(current_provider, api_key, data):
	# If the provider was just changed, remove the value in the API key input so it isn't sent to a remote provider
	if ctx.triggered_id == "model-provider":
		new_api_key_value = ""
		api_key = None
	else:
		new_api_key_value = no_update

	for name, cls in llms.LLM.classes.items():
		if name != current_provider:
			continue

		if cls._api_key_needed_for_list():
			if api_key is None:
				return [], True, None, new_api_key_value

			models = cls.available_models(api_key)
			models = [dict(value=model.id, label=model.display_name) for model in models]
		else:
			models = data["available_llms"][current_provider]
			models = [dict(value=model["model_name"], label=model["display_name"]) for model in models]

		default = models[0]["value"] if len(models) > 0 else None
		return models, False, default, new_api_key_value
	else:
		raise PreventUpdate


@app.callback(
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


@app.callback(
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


@app.callback(
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


@app.callback(
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


@app.callback(
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


@app.callback(
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


app.clientside_callback(
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
		State("model-provider", "value"),
		State("model-select", "value"),
		State("model-key", "value"),
		State("save-methods", "value"),
		State("ntfy-url", "value"),
		State("ntfy-priority", "value"),
		State("webhook-url", "value"),
	],
	prevent_initial_call=True
)


app.clientside_callback(
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
