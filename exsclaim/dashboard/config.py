from exsclaim.config import get_variables
# Gunicorn

globals().update(get_variables("DASHBOARD_PORT", "3000", "DASHBOARD_KEY_FILE",
							   "DASHBOARD_CERT_FILE", "dashboard_access.log", "dashboard_error.log",
							   "DASHBOARD_INSECURE_PORT"))

