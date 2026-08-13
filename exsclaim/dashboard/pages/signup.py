try:
	from components.login_page import create_login_page_layout, FormMode
except ImportError:
	from exsclaim.dashboard.components.login_page import create_login_page_layout, FormMode

import dash


dash.register_page(__name__, path="/signup", title="EXSCLAIM Sign Up")
layout = create_login_page_layout(FormMode.SIGNUP)
