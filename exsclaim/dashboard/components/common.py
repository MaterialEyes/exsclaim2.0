"""
Common Dash components converted from React components.
"""
from .login_page import create_login_form_modal, create_signup_form_modal

import dash_bootstrap_components as dbc
from dash import html
from dash.development.base_component import Component
from dash_extensions import Purify
from typing import Optional

__all__ = ["create_header_component", "create_notification_component", "create_footer_component"]


def create_menu_component():
	return html.Div(
		[
			dbc.Button(
				"Login/Signup",
				id="user-button",
				className="dropbtn"
			),
			html.Div(children=[
				html.Button(
					"Logout",
					id="logout-button",
					style={"display": "none"}
				),
				html.A(
					children="See Previous Runs",
					href="/previous"
				)
				],
				className="dropdown-content",
			)
		],
		className="dropdown"
	)


def create_header_component(description: Optional[list[Component]] = None):
	"""
	Create the header component with logo, welcome message, and notification.

	Returns:
		dbc.Container: Header component
	"""
	description = description or [html.P(style={"textAlign": "center", "marginBottom": "20px"}, children=[
		"On this website, you can submit a query for EXSCLAIM to run through.",
		html.Br(),
		"Once you submit, a list of subfigures will appear on the right and a menu on the left. Then, you can query through the subfigures with the left-hand menu. ",
		html.Br(),
		"Have fun querying!"
	])]

	return dbc.Container([
		# Logo section
		html.Div([
			html.A(
				html.Img(
					id="exsclaim-logo",
					src="/assets/ExsclaimLogo-Inverted.png",
					alt="EXSCLAIM Logo",
					style={
						"maxWidth": "350px",
						"height": "auto",
						"display": "block",
						"margin": "0 auto"
					},
				),
				href="/"
			)
		], style={"textAlign": "center", "marginBottom": "20px"}),

		# Welcome message
		html.H5(
			"Welcome to the EXSCLAIM UI!",
			style={"fontWeight": "bold", "textAlign": "center", "marginBottom": "15px"},
			id="welcome-banner"
		),

		create_menu_component(),
		create_login_form_modal(),
		create_signup_form_modal(),

		dbc.Switch(
			id="theme-button",
			label_class_name="checkbox-label",
			label_id="theme-label",
			label=[
				html.I(className="fas fa-moon"),
				html.I(className="fas fa-sun"),
				html.Span(className="ball")
			],
			value=False,
			persistence=True,
			className="checkbox",
			style={
				"position": "fixed",
				"zIndex": "100",
				"top": "20px",
				"right": "20px"
			}
		),

		*description,

		# Notification component
		create_notification_component(),

		create_banner_component()
	], fluid=True)


def create_notification_component() -> html.Center:
	"""
	Create notification component for alerts.

	Returns:
		dbc.Alert: Notification component
	"""

	return html.Center([
		dbc.Alert(
			Purify(id="notification-html"),
			id="notification",
			dismissable=True,
			is_open=False,
			fade=False
		)
	])


def create_banner_component() -> html.Center:
	"""
	Create notification component for alerts.

	Returns:
		html.Center: Centered Banner
	"""

	return html.Center([
		dbc.Alert(
			Purify(id="banner-html"),
			id="banner",
			dismissable=True,
			is_open=False,
			fade=False
		)
	])


def create_footer_component():
	"""
	Create the footer component with Argonne logo and links.

	Returns:
		dbc.Container: Footer component
	"""
	return dbc.Container(fluid=True, className="footer", style={
		"width": "100%",
		# "height": "120px",
		"position": "relative",
		"bottom": "0",
		"className": "footer"
	}, children=[
		dbc.Row(align="stretch", justify="center", children=[
			dbc.Col(align="center", children=[
				# Argonne logo and link
				html.A(
					html.Img(
						id="argonne-logo",
						src="/assets/Argonnelablogo-White.png",
						alt="Argonne Logo",
						height=60
					),
					href="https://www.anl.gov/",
					target="_blank"
				)
			]),
			dbc.Col(align="center", children=[
				html.H6("More Info", style={"fontWeight": "bold", "marginBottom": "10px"}),
				html.Div([
					html.A(
						"EXSCLAIM GitHub Page",
						href="https://github.com/MaterialEyes/exsclaim2.0",
						target="_blank",
						style={"display": "block", "marginBottom": "5px"}
					),
					html.A(
						"EXSCLAIM Paper",
						href="https://arxiv.org/abs/2103.10631",
						target="_blank",
						style={"display": "block", "marginBottom": "5px"}
					),
					html.A(
						"Terms of Service",
						href="/terms-of-service",
						target="_blank",
						style={"display": "block", "marginBottom": "5px"}
					),
					html.A(
						"Privacy Policy",
						href="/privacy-policy",
						target="_blank",
						style={"display": "block", "marginBottom": "5px"}
					)
				])
			])
		])
	])
