from exsclaim.api import settings
from multiprocessing import cpu_count
from os import getenv

workers = max(cpu_count() // 2, 1)
bind = f"0.0.0.0:{getenv('FAST_API_PORT', '8000')}"
include_date_header = True

if settings.DEBUG:
	use_reloader = True
	debug = True
