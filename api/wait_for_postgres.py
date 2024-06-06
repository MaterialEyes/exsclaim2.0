from os import getenv
import logging
from time import time, sleep
from psycopg import connect, OperationalError


def pg_isready():
	config = {
		"dbname": getenv("POSTGRES_DB", "exsclaim"),
		"user": getenv("POSTGRES_USER", "postgres"),
		"password": getenv("POSTGRES_PASSWORD", "exsclaimtest!9700"),
		"host": getenv("DATABASE_URL", "postgres")
	}

	logger = logging.getLogger()
	logger.setLevel(logging.INFO)
	logger.addHandler(logging.StreamHandler())

	start_time = time()
	check_timeout = getenv("POSTGRES_CHECK_TIMEOUT", 30)
	check_interval = getenv("POSTGRES_CHECK_INTERVAL", 1)
	interval_unit = "second" if check_interval == 1 else "seconds"

	while time() - start_time < check_timeout:
		try:
			conn = connect(**config)
			logger.info("Postgres is ready! ✨ 💅")
			conn.close()
			return True
		except OperationalError:
			logger.info(f"Postgres isn't ready. Waiting for {check_interval} {interval_unit}...")
			sleep(check_interval)

	logger.error(f"We could not connect to Postgres within {check_timeout} seconds.")
	return False


if __name__ == "__main__":
	pg_isready()
