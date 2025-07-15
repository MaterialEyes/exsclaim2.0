from exsclaim.config import get_variables
# Hypercorn

globals().update(get_variables("FAST_API_PORT", "8000", "FAST_API_KEY_FILE",
							   "FAST_API_CERT_FILE", "api_access.log", "api_error.log",
							   "FAST_API_INSECURE_PORT"))

include_server_header = False
if settings.DEBUG:
	use_reloader = True
