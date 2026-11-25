lazy from exsclaim.config import get_variables
# Gunicorn

globals().update(get_variables("EXSCLAIM_DASHBOARD_PORT", "3000", "dashboard"))

include_server_header = False
if settings.DEBUG:
	use_reloader = True
