from dash import Output, Input, State, ClientsideFunction, get_app

app = get_app()


app.clientside_callback(
	ClientsideFunction(
		namespace="clientside",
		function_name="setTheme"
	),
	Output("storage", "data", allow_duplicate=True),
	Input("theme-button", "value"),
	State("storage", "data"),
	prevent_initial_call=True
)


# app.clientside_callback( # TODO: Figure this out
# 	ClientsideFunction(
# 		namespace="clientside",
# 		function_name="update_info_banner"
# 	),
# 	Output("banner", "is_open"),
# 	Output("banner-html", "html"),
# 	Output("storage", "data", allow_duplicate=True),
# 	State("storage", "data"),
# 	State("exsclaim-store", "data"),
# 	_allow_dynamic_callbacks=True
# )


app.clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="logout"
	),
	[
		Output("notification", "is_open", allow_duplicate=True),
		Output("notification", "children", allow_duplicate=True),
		Output("notification", "color", allow_duplicate=True),
		Output("url", "href", allow_duplicate=True),
		Output("url", "refresh", allow_duplicate=True),
	],
	[
		Input("logout-button", "n_clicks", allow_optional=True)
	],
	[
		State("exsclaim-store", "data"),
		State("url", "href"),
	],
	prevent_initial_call=True
)
