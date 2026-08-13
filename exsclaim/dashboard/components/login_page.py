from dash import html, Output, Input, State, clientside_callback, ClientsideFunction
from enum import StrEnum
import dash_bootstrap_components as dbc
from .common import create_header_component, create_footer_component

__all__ = ["create_login_page_layout", "FormMode"]


class FormMode(StrEnum):
	LOGIN = "Log in"
	SIGNUP = "Sign up"


def create_username_component(debounce=True):
	"""Create user's name component."""
	return html.Div([
		dbc.Label(
			"Username:",
			html_for="username",
		),
		dbc.Input(
			id="username",
			name="username",
			placeholder="",
			className="form-control",
			debounce=debounce,
			required=True,
			autocomplete="username"
		)
	], className="mb-3")


def create_email_component(debounce=True):
	"""Create user's email component."""
	return html.Div([
		dbc.Label(
			"Email:",
			html_for="email",
		),
		dbc.Input(
			id="email",
			name="email",
			type="email",
			inputmode="email",
			placeholder="user@example.com",
			pattern=r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`\{\|\}~\-]+@[a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)*$",
			valid=False,
			className="form-control",
			debounce=debounce,
			required=True,
			autocomplete="email"
		)
	], className="mb-3")


def create_password_component(debounce=False, show_signup_tips: bool = False):
	"""Create number of articles input component."""
	tips = []
	if show_signup_tips:
		tips = [
			html.Ul([
				html.Li("8 or more characters", id="password_length", className="li-password password-failed"),
				html.Li("At least one uppercase (capital) letter", id="password_upper", className="li-password password-failed"),
				html.Li("At least one lowercase letter", id="password_lower", className="li-password password-failed"),
				html.Li("At least one number", id="password_number", className="li-password password-failed"),
				html.Li(r"At least one special character: !#$&?@^_(){}<>[]\/|=+,-.:;", id="password_special",
						className="li-password password-failed")
			], id="password_requirements")
		]
	return html.Div([
		dbc.Label(
			"Password:",
			html_for="password",
		),
		dbc.Input(
			id="password",
			name="password",
			type="password",
			className="form-control",
			debounce=False,
			required=True
		),
		*tips
	], className="mb-3")


def create_orcid_button_component(mode: FormMode = FormMode.LOGIN):
	try:
		from ...config import orcid_settings, ui_settings
	except ImportError:
		from exsclaim.config import orcid_settings, ui_settings

	return html.Div([
		dbc.Button(
			[
				html.Img(src="/assets/ORCID-iD_icon_vector.svg", alt="ORCID Logo."),
				f"  {mode} With ORCID iD"
			],
			id="orcid",
			href=f"{orcid_settings.URL}/oauth/authorize?client_id={orcid_settings.CLIENT_ID}&response_type=code&scope=/authenticate&redirect_uri={ui_settings.PUBLIC_API_URL}/user/login-orcid",
			className="button-link",
			size="lg",
			style={
				# "background-color": "#a6ce39",
				# "color": "var(--text-light)",
			}
		),
		# html.Hr(),
		html.P("OR", className="horizontal_separator")
	], className="mb-3")


def create_login_button_component(mode: FormMode = FormMode.LOGIN):
	return html.Div([
		dbc.Button(
			mode.value.title(),
			type="submit",
			id="submit-info",
			className="button-link",
			size="lg",
			style={"width": "200px"}
		)
	], className="mb-3")


def create_login_form_component(mode: FormMode = FormMode.LOGIN, debounce=True):
	match mode:
		case FormMode.LOGIN:
			form_components = [
				create_orcid_button_component(mode),
				create_email_component(debounce),
				create_password_component(debounce, show_signup_tips=False),
				create_login_button_component(mode),
			]
		case FormMode.SIGNUP:
			form_components = [
				create_orcid_button_component(mode),
				create_username_component(debounce),
				create_email_component(debounce),
				create_password_component(debounce, show_signup_tips=True),
				create_login_button_component(mode)
			]
		case _:
			print(f"Unknown mode: {mode}")
			raise RuntimeError(f"Unknown mode: {mode}")

	return dbc.Container(fluid=True, style={
		"width": "95%",
		"padding": "20px",
		"margin": "20px",
		"justifyContent": "center",
		"display": "flex"
	}, children=[
		dbc.Row([
			dbc.Col(width=12, children=form_components)
		])
	 ])


def handle_callbacks(mode: FormMode = FormMode.LOGIN):
	if mode == FormMode.SIGNUP:
		clientside_callback(
			ClientsideFunction(
				namespace="user",
				function_name="check_password"
			),
			[
				Output("password", "valid"),
				Output("password", "invalid"),
			],
			[
				Input("password", "value")
			]
		)


def create_login_page_layout(mode: FormMode = FormMode.LOGIN, debounce=True) -> html.Div:
	match mode:
		case FormMode.LOGIN:
			description = [html.P(style={"textAlign": "center", "marginBottom": "20px"}, children=[
				"Login to your account here! If you don't have an account, signup for one ",
				html.A("here", href="/signup"),
				"."
			])]
		case FormMode.SIGNUP:
			description = [html.P(style={"textAlign": "center", "marginBottom": "20px"}, children=[
				"Sign up for your own account here.",
				html.Br(),
				"Using EXSCLAIM is possible without having an account, but running queries with your account allows them to be private and only viewable by you.",
				html.Br(),
				"If you already have an account, ",
				html.A("login here", href="/login"),
				"."
			])]
		case _:
			raise NotImplementedError(f"Unknown FormMode: {mode}.")

	handle_callbacks(mode)

	return html.Div([
		# Header
		create_header_component(description=description),

		# Login/Signup form
		create_login_form_component(mode, debounce),

		# Footer
		create_footer_component()
	], id="exsclaim-app")


clientside_callback(
	"""
	function(email_validity, password_validity, username_validity) {
		if(username_validity === undefined || username_validity === null) { username_validity = true; }
		return !(username_validity && email_validity && password_validity);
	}
	""",
	Output("submit-info", "disabled"),
	[
		Input("email", "valid"),
		Input("password", "valid"),
		Input("username", "valid", allow_optional=True),
	]
)


clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="check_email"
	),
	[
		Output("email", "valid"),
		Output("email", "invalid"),
	],
	[
		Input("email", "value"),

	],
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="send_form_data"
	),
	Output("notification", "is_open", allow_duplicate=True),
	Output("notification", "children", allow_duplicate=True),
	Output("notification", "color", allow_duplicate=True),
	Output("url", "href", allow_duplicate=True),
	Output("url", "refresh", allow_duplicate=True),
	Input("submit-info", "n_clicks"),
	State("username", "value", allow_optional=True),
	State("email", "value"),
	State("password", "value"),
	State("exsclaim-store", "data"),
	prevent_initial_call=True
)


clientside_callback(
	ClientsideFunction(
		namespace="user",
		function_name="check_credentials"
	),
	Output("check-credentials", "disabled"),
	Input("check-credentials", "n_intervals"),
	State("exsclaim-store", "data"),
	State("check-credentials", "interval"),
)
