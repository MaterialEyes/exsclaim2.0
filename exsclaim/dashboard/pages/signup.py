try:
	from components.login_page import FormMode, create_login_page_layout
except ImportError:
	from exsclaim.dashboard.components.login_page import FormMode, create_login_page_layout

import dash


dash.register_page(__name__, path="/signup", title="EXSCLAIM Sign Up", description="Create an account with EXSCLAIM.")
layout = create_login_page_layout(FormMode.SIGNUP)
