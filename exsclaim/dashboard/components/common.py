"""
Common Dash components converted from React components.
"""
import dash_bootstrap_components as dbc
from dash import html, clientside_callback, Output, Input, State


def create_header_component():
	"""
	Create the header component with logo, welcome message, and notification.
	
	Returns:
		dbc.Container: Header component
	"""
	return dbc.Container([
		# Logo section
		html.Div([
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
			)
		], style={"textAlign": "center", "marginBottom": "20px"}),

		# Welcome message
		html.H5(
			"Welcome to the EXSCLAIM UI!",
			style={"fontWeight": "bold", "textAlign": "center", "marginBottom": "15px"}
		),

		dbc.Row([
			dbc.Col([
				# Description
				html.P(style={"textAlign": "center", "marginBottom": "20px"}, children=[
					"On this website, you can submit a query for EXSCLAIM to run through. ",
					html.Br(),
					"Once you submit, a list of subfigures will appear on the right and a menu on the left. Then, you can query through the subfigures with the left-hand-side menu. ",
					html.Br(),
					"Have fun querying!"
				]),
			]),
			dbc.Col(width="auto", children=[
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
					className="checkbox"
				)
			])
		]),

		# Notification component
		create_notification_component()
	], fluid=True)


def create_notification_component() -> dbc.Alert:
	"""
	Create notification component for alerts.

	Returns:
		dbc.Alert: Notification component
	"""

	return dbc.Alert(
		id="notification",
		dismissable=True,
		is_open=False
	)


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
					)
				])
			])
		])
	])


clientside_callback(
	"""
	function setTheme(theme="dark", data) {
		if(data.first_visit === undefined){
			data.first_visit = false;
			if(window.matchMedia){
				if(window.matchMedia("(prefers-color-scheme: dark)")){
					theme = "dark";
				}
			}
		} else if (theme){
			theme = "light";
		} else {
			theme = "dark";
		}
		
		document.body.setAttribute("data-theme", theme);
		data.theme = theme;
		return data;
	}
	""",
	Output("theme", "data"),
	Input("theme-button", "value"),
	State("theme", "data")
)
