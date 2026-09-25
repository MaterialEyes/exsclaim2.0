"""
ResultPage component - the results page that uses Layout.
Converted from React ResultPage.js component.
"""
from dash import html, register_page
from typing import Optional
from uuid import UUID

try:
	from components.common import create_header_component, create_footer_component
	from components.layout import create_layout_component
except ImportError:
	from exsclaim.dashboard.components.common import create_header_component, create_footer_component
	from exsclaim.dashboard.components.layout import create_layout_component

register_page(__name__, path_template="/results/<result_id>", title="Results", description="Results from the EXSCLAIM Pipeline for a given result id..")


def layout(result_id: Optional[UUID] = None):
	"""
	Create the ResultPage layout.

	Args:
		result_id (UUID): The result ID to fetch data for

	Returns:
		html.Div: ResultPage layout
	"""
	try:
		from ...config import ui_settings
	except ImportError:
		from exsclaim.config import ui_settings

	children = [
		# Header
		create_header_component(),

		None,

		# Footer
		create_footer_component()
	]

	if result_id is not None:
		# Layout component (contains the main results interface)
		children[1] = create_layout_component(result_id, ui_settings.FAST_API_URL, ui_settings.PUBLIC_API_URL)
	else:
		children = [child for child in children if child is not None]

	return html.Div(children, id="exsclaim-results")
