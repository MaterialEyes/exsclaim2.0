"""
HomePage component - the main landing page for EXSCLAIM dashboard.
Converted from React HomePage.js component.
"""
from dash import html, register_page

register_page(__name__, path="/")


def layout() -> html.Div:
	"""
	Create the complete HomePage layout.
	
	Returns:
		html.Div: Complete HomePage layout
	"""
	try:
		from ...journal import JournalFamily
		from components.common import create_header_component, create_footer_component
		from components.query import create_query_component, get_llms
	except ImportError:
		from exsclaim.journal import JournalFamily
		from exsclaim.dashboard.components.common import create_header_component, create_footer_component
		from exsclaim.dashboard.components.query import create_query_component, get_llms

	journal_families = [name for name, cls in JournalFamily]
	available_llms, show_api_key, requires_api_key = get_llms()
	return html.Div([
		# Header
		create_header_component(),

		# Query form
		create_query_component(journal_families, available_llms),

		# Footer
		create_footer_component()
	], id="exsclaim-app")
