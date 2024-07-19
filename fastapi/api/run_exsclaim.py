import logging

from main import get_database_connection_string

from exsclaim.__main__ import main as exsclaim_main
from os import getenv
from pathlib import Path
from psycopg import connect
from shutil import rmtree
from uuid import UUID


def main(_id:UUID, search_query_location:str):
	db_result = "Closed due to an error"
	try:
		args = ["query", search_query_location, "--caption_distributor",
				"--journal_scraper", "--figure_separator", "--compress", "gztar",
				"--compress_location", f"/exsclaim/results/{_id}"]
		if getenv("EXSCLAIM_DEBUG", "").lower() == "true":
			args.append("--verbose")
		results = exsclaim_main(args)
		db_result = "Finished"

		results_dir = Path(search_query_location).parent
		if results_dir.is_dir():
			rmtree(results_dir)
	except Exception as e:
		logging.getLogger(f"run_exsclaim_{_id}").exception(e)
		results = None

	with connect(get_database_connection_string()) as db:
		cursor = db.cursor()
		cursor.execute("UPDATE results SET status = %s, end_time = NOW() WHERE id = %s", (db_result, _id))
		db.commit()
		cursor.close()

	if results is None:
		exit(1)
	return results


if __name__ == "__main__":
	from json import load
	from sys import argv

	try:
		_id = UUID(argv[1], version=4)
	except ValueError:
		raise ValueError("The given argument must be a valid UUID.")

	search_query_location = argv[2]

	main(_id, search_query_location)
