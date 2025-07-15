from multiprocessing import cpu_count
from os import getenv
from exsclaim.api import settings
from pathlib import Path


def get_variables(port_env:str, default_port:str, keyfile_env:str, certfile_env:str, access_file:str, error_file:str,
				  insecure_bind_port:str=None) -> dict:
	log_dir = Path(getenv("EXSCLAIM_LOGS", "/exsclaim/logs")).resolve()
	log_dir.mkdir(parents=True, exist_ok=True)

	config = dict(
		bind=f"0.0.0.0:{getenv(port_env, default_port)}",
		workers=max(cpu_count() // 2, 1),
		reload=settings.DEBUG,
		settings=settings,
		include_date_header=True,
		accesslog=str(log_dir / access_file),
		errorlog=str(log_dir / error_file),
	)

	if (keyfile := getenv(keyfile_env)):
		config["keyfile"] = keyfile

	if (certfile := getenv(certfile_env)):
		config["certfile"] = certfile

	if (insecure_port := getenv(insecure_bind_port)):
		config["insecure_bind"] = f"0.0.0.0:{insecure_port}"

	return config
