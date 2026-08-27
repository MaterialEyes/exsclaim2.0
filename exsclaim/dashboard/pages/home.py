"""
HomePage component - the main landing page for EXSCLAIM dashboard.
Converted from React HomePage.js component.
"""
from dash import html, register_page

register_page(__name__, path="/",
			  description="Home page for Extraction, Separation, and Caption-based natural Language Annotation of Images from scientific figures (EXSCLAIM) dashboard.")


def layout() -> html.Div:
	"""
	Create the complete HomePage layout.
	
	Returns:
		html.Div: Complete HomePage layout
	"""
	try:
		from components.common import create_header_component, create_footer_component
		from components.query import create_query_component, get_llms
	except ImportError:
		from exsclaim.dashboard.components.common import create_header_component, create_footer_component
		from exsclaim.dashboard.components.query import create_query_component, get_llms

	available_llms, show_api_key, requires_api_key = get_llms()
	return html.Div([
		# Header
		create_header_component(),

		# Query form
		create_query_component(available_llms),

		# Footer
		create_footer_component()
	], id="exsclaim-app")
