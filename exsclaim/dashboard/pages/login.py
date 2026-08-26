try:
	from components.login_page import create_login_page_layout, FormMode
except ImportError:
	from exsclaim.dashboard.components.login_page import create_login_page_layout, FormMode
import dash


dash.register_page(__name__, path="/login", title="EXSCLAIM Login", description="Login page for EXSCLAIM dashboard.")
layout = create_login_page_layout(FormMode.LOGIN)
