from exsclaim.config import get_variables
# Hypercorn

globals().update(get_variables("FAST_API_PORT", "8000", "api"))

include_server_header = False
if settings.DEBUG:
	use_reloader = True
