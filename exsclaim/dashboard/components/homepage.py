"""
HomePage component - the main landing page for EXSCLAIM dashboard.
Converted from React HomePage.js component.
"""
from dash import html

from .common import create_header_component, create_footer_component
from .query import create_query_component


def create_homepage_layout(title, journal_families, available_llms):
    """
    Create the complete HomePage layout.
    
    Args:
        journal_families (list): List of available journal families
        available_llms (list): List of available LLM models

    Returns:
        html.Div: Complete HomePage layout
    """
    return html.Div([
		html.Title(title),

		# Header
		create_header_component(),

		# Query form
		create_query_component(journal_families, available_llms),

		html.Div(style={"margin": "60px"}),

		# Footer
		create_footer_component()
    ], id="exsclaim-app")
