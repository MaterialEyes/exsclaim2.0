from . import Pipeline
try:
	from . import __version__
except ImportError:
	__version__ = None
from argparse import ArgumentParser, BooleanOptionalAction
from atexit import register
from functools import wraps
from json import load
from os import getenv, system
from pathlib import Path
from tarfile import open as tar_open


@register
def on_terminate():
	import logging
	logger = logging.getLogger(__name__)

	for handler in logger.handlers:
		handler.flush()

	logging.shutdown()


def install_dependencies():
	from subprocess import call
	# TODO: Add all of the dependency installation requirements
	call("playwright install-deps".split(" "))
	call("playwright install chromium".split(" "))


def main(args=None):
	parser = ArgumentParser(prog="exsclaim")

	parser.add_argument("-v", "--version", action="version",
						version=f"EXSCLAIM v{__version__}" if __version__ is not None else "EXSCLAIM! version is currently unavailable.")

	subparsers = parser.add_subparsers(dest="command", required=True)
	subparsers.add_parser("install-deps", help="Install dependencies for EXSCLAIM!'s dependencies.")
	subparser = subparsers.add_parser("query", help="The path to the JSON file holding the search query.")

	subparser.add_argument("query", help="The path to the JSON file holding the search query.")
	subparser.add_argument("--caption_distributor", "-cd", action="store_true")
	subparser.add_argument("--journal_scraper", "-js", action="store_true")
	subparser.add_argument("--figure_separator", "-fs", action="store_true")
	subparser.add_argument("--html_scraper", "-hs", action="store_true")
	subparser.add_argument("--compress", "-c", action="store", help="Compress the search results into a tar.gz file to save space. Deletes the original folder after compression.")
	args = vars(parser.parse_args(args))

	if args["command"] == "install-deps":
		install_dependencies()
		exit(0)

	query = args.get("query", None)
	if query is None:
		raise ValueError("The search query is required.")

	path = Path(query).absolute()
	if not path.exists():
		raise ValueError(f"The search query file \"{path}\" does not exist.")

	with open(path, "r") as f:
		search_query = load(f)

	kwargs = {key: args.get(key, False) for key in {"caption_distributor", "journal_scraper", "figure_separator", "html_scraper"}}
	pipeline = Pipeline(search_query)
	results = pipeline.run(**kwargs)

	if args.get("compress", False):
		results_dir = pipeline.results_directory
		with tar_open(args["compress"], "w:gz") as tar:
			tar.add(results_dir, arcname=search_query["name"])
		if Path(args["compress"]).exists():
			from shutil import rmtree
			print(f"Should be removing {results_dir}")
			system("touch ~/removing")
			rmtree(results_dir)
			system("touch ~/removed")

	return results


if __name__ == "__main__":
	main()
