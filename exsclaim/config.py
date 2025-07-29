from datetime import datetime as dt
from multiprocessing import cpu_count
from os import getenv
from exsclaim.api import settings
from pathlib import Path


def get_variables(port_env:str, default_port:str, log_subfolder:str) -> dict:
	log_dir = Path(getenv("EXSCLAIM_LOGS", "/exsclaim/logs")).resolve() / log_subfolder
	log_dir.mkdir(parents=True, exist_ok=True)
	time = dt.now().isoformat()

	accesslog = log_dir / f"access-{time}.log"
	errorlog = log_dir / f"error-{time}.log"

	for log in (accesslog, errorlog):
		log.touch(mode=0o775, exist_ok=False)

	config = dict(
		bind=f"0.0.0.0:{getenv(port_env, default_port)}",
		workers=max(cpu_count() // 2, 1),
		reload=settings.DEBUG,
		settings=settings,
		include_date_header=True,
		accesslog=str(accesslog),
		errorlog=str(errorlog),
	)

	return config
