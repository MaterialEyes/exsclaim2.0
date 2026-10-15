from dash import html
from enum import StrEnum
import dash_bootstrap_components as dbc

__all__ = ["FormMode", "create_login_form_modal", "create_signup_form_modal"]


class FormMode(StrEnum):
	LOGIN = "Log in"
	SIGNUP = "Sign up"

	def get_form_value(self) -> str:
		match self:
			case FormMode.LOGIN:
				return "login"
			case FormMode.SIGNUP:
				return "signup"


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


def create_email_component(mode: FormMode, debounce=True):
	"""Create user's email component."""
	return html.Div([
		dbc.Label(
			"Email:",
			html_for="email",
		),
		dbc.Input(
			id={"form": mode.get_form_value(), "field": "email"},
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


def create_password_component(mode: FormMode, debounce=True):
	"""Create number of articles input component."""
	signup_elements = []
	if mode == FormMode.SIGNUP:
		signup_elements = [
			dbc.Label(
				"Verify Password:",
				html_for="password_verify",
			),
			dbc.Input(
				id="password_verify",
				name="password_verify",
				type="password",
				className="form-control",
				debounce=debounce,
				required=True
			),
			html.Ul([
				html.Li("8 or more characters", id="password_length", className="li-password password-failed"),
				html.Li("At least one uppercase (capital) letter", id="password_upper", className="li-password password-failed"),
				html.Li("At least one lowercase letter", id="password_lower", className="li-password password-failed"),
				html.Li("At least one number", id="password_number", className="li-password password-failed"),
				html.Li(r"At least one special character: !#$&?@^_(){}<>[]\/|=+,-.:;", id="password_special",
						className="li-password password-failed"),
				html.Li(r"Passwords match", id="password_match", className="li-password password-passed")
			], id="password_requirements")
		]
	return html.Div([
		dbc.Label(
			"Password:",
			html_for="password",
		),
		dbc.Input(
			id={"form": mode.get_form_value(), "field": "password"},
			name="password",
			type="password",
			className="form-control",
			debounce=debounce,
			required=True
		),
		*signup_elements
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
			id="signup" if mode == FormMode.SIGNUP else "login",
			className="button-link",
			size="lg",
			style={"width": "200px"}
		)
	], className="mb-3")


def create_login_form_component(mode: FormMode = FormMode.LOGIN, debounce=False):
	match mode:
		case FormMode.LOGIN:
			form_components = [
				create_orcid_button_component(mode),
				create_email_component(mode, debounce),
				create_password_component(mode, debounce),
				create_login_button_component(mode),
			]
		case FormMode.SIGNUP:
			form_components = [
				create_orcid_button_component(mode),
				create_username_component(debounce),
				create_email_component(mode, debounce),
				create_password_component(mode, debounce),
				create_login_button_component(mode)
			]

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


def create_login_form_modal(mode: FormMode = FormMode.LOGIN, debounce=False) -> dbc.Modal:
	return dbc.Modal(
		[
			dbc.ModalHeader(
				dbc.ModalHeader(
					dbc.ModalTitle(mode.value),
				),
			),
			dbc.ModalBody([
				html.P(style={"textAlign": "center", "marginBottom": "20px"}, children=[
					"Login to your account here.",
				]),
				create_login_form_component(mode, debounce),
			]),
			dbc.ModalFooter(
				dbc.Button(
					"Don't have an account, sign up for one instead.",
					id="switch-to-signup"
				)
			)
		],
		id="login-modal",
		centered=True,
		is_open=False,
		size="xl"
	)


def create_signup_form_modal(mode: FormMode = FormMode.SIGNUP, debounce=False) -> dbc.Modal:
	return dbc.Modal(
		[
			dbc.ModalHeader(
				dbc.ModalHeader(
					dbc.ModalTitle(mode.value),
				),
			),
			dbc.ModalBody([
				html.P(style={"textAlign": "center", "marginBottom": "20px"}, children=[
					"Sign up for your own account here.",
					html.Br(),
					"Using EXSCLAIM is possible without having an account, but running queries with your account allows them to be private and only viewable by you.",
				]),
				create_login_form_component(mode, debounce),
			]),
			dbc.ModalFooter(
				dbc.Button(
					"Already have an account, login to it here.",
					id="switch-to-login"
				)
			)
		],
		id="signup-modal",
		centered=True,
		is_open=False,
		size="xl"
	)
