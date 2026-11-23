from dash import Output, Input, State, get_app, ClientsideFunction, MATCH

app = get_app()


app.clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="check_password_signup"
	),
	Output(dict(form="signup", field="password"), "valid"),
	Output(dict(form="signup", field="password"), "invalid"),
	Output("password_verify", "valid"),
	Output("password_verify", "invalid"),
	Input(dict(form="signup", field="password"), "value"),
	Input("password_verify", "value", allow_optional=True),
	prevent_initial_call=True
)


app.clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="check_password"
	),
	Output(dict(form="login", field="password"), "valid"),
	Output(dict(form="login", field="password"), "invalid"),
	Input(dict(form="login", field="password"), "value"),
	prevent_initial_call=True
)


app.clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="check_username"
	),
	Output("username", "valid"),
	Output("username", "invalid"),
	Input("username", "value"),
	prevent_initial_call=True
)


app.clientside_callback(
	"""
	function(button_clicked, login_button, signup_button, login_open, signup_open){
		const show_login = [true, false];
		const show_signup = [false, true];

		if(!button_clicked){
			return [false, false];
		}

		if(login_open){
			return show_signup;
		}

		if(signup_open){
			return show_login;
		}

		return [true, false];
	}
	""",
	Output("login-modal", "is_open"),
	Output("signup-modal", "is_open", allow_duplicate=True),
	Input("user-button", "n_clicks"),
	Input("switch-to-login", "n_clicks"),
	Input("switch-to-signup", "n_clicks"),
	State("login-modal", "is_open"),
	State("signup-modal", "is_open"),
	prevent_initial_call=True,
)


app.clientside_callback(
	"""
	function(email_validity, password_validity, username_validity) {
		if(username_validity === undefined || username_validity === null) { username_validity = true; }
		return !(username_validity && email_validity && password_validity);
	}
	""",
	Output("signup", "disabled"),
	Input(dict(form="signup", field="email"), "valid"),
	Input(dict(form="signup", field="password"), "valid"),
	Input("username", "valid"),
)


app.clientside_callback(
	"""
	function(email_validity, password_validity) {
		return !(email_validity && password_validity);
	}
	""",
	Output("login", "disabled"),
	Input(dict(form="login", field="email"), "valid"),
	Input(dict(form="login", field="password"), "valid"),
)


app.clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="check_email"
	),
	Output(dict(form=MATCH, field="email"), "valid"),
	Output(dict(form=MATCH, field="email"), "invalid"),
	Input(dict(form=MATCH, field="email"), "value"),
	prevent_initial_call=True
)


app.clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="send_signup_data"
	),
	Output("notification", "is_open", allow_duplicate=True),
	Output("notification", "children", allow_duplicate=True),
	Output("notification", "color", allow_duplicate=True),
	Output("signup-modal", "is_open", allow_duplicate=True),
	Output("check-credentials", "interval", allow_duplicate=True),
	Output("check-credentials", "disabled", allow_duplicate=True),
	Input("signup", "n_clicks"),
	State(dict(form="signup", field="email"), "value"),
	State(dict(form="signup", field="password"), "value"),
	State("exsclaim-store", "data"),
	prevent_initial_call=True
)

app.clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="send_login_data"
	),
	Output("notification", "is_open", allow_duplicate=True),
	Output("notification", "children", allow_duplicate=True),
	Output("notification", "color", allow_duplicate=True),
	Output("login-modal", "is_open", allow_duplicate=True),
	Output("check-credentials", "interval", allow_duplicate=True),
	Output("check-credentials", "disabled", allow_duplicate=True),
	Input("login", "n_clicks"),
	State(dict(form="login", field="email"), "value"),
	State(dict(form="login", field="password"), "value"),
	State("exsclaim-store", "data"),
	prevent_initial_call=True
)


app.clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="check_credentials"
	),
	Output("check-credentials", "interval"),
	Output("check-credentials", "disabled"),
	Output("user-button", "children"),
	Output("logout-button", "style"),
	Input("check-credentials", "n_intervals"),
	State("exsclaim-store", "data"),
)
