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
		from ..components import common, query
	except ImportError:
		from exsclaim.dashboard.components import common, query

	available_llms, *_ = query.get_llms()
	return html.Div([
		# Header
		common.create_header_component(),

		# Query form
		query.create_query_component(available_llms),

		# Footer
		common.create_footer_component()
	], id="exsclaim-app")
