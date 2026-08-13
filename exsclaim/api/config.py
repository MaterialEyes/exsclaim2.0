from exsclaim.config import get_variables, ui_settings as settings
# Hypercorn

globals().update(get_variables("EXSCLAIM_FAST_API_PORT", "8000", "api"))

include_server_header = False
if settings.DEBUG:
	use_reloader = True
