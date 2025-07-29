"""
ResultPage component - the results page that uses Layout.
Converted from React ResultPage.js component.
"""
from dash import html
from uuid import UUID

from .common import create_header_component, create_footer_component
from .layout import create_layout_component


def create_resultpage_layout(result_id: UUID, base_url:str) -> html.Div:
    """
    Create the ResultPage layout.
    
    Args:
        result_id (UUID): The result ID to fetch data for

    Returns:
        html.Div: ResultPage layout
    """
    return html.Div([
		html.Title(f"EXSCLAIM Results: {result_id}"),

        # Header
        create_header_component(),

        # Layout component (contains the main results interface)
        create_layout_component(result_id, base_url),

        # Footer
        create_footer_component()
    ], id="exsclaim-results")
