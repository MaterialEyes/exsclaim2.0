from . import Pipeline, PipelineInterruptionException

try:
	from . import __version__
except ImportError:
	__version__ = None
from argparse import ArgumentParser
from asyncio import run
from atexit import register
from json import load
from os.path import splitext
from pathlib import Path


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
	subparser.add_argument("--compress", "-c", choices=["zip", "tar", "gztar", "bztar", "xztar"], help="Compress the search results into a tar.gz file to save space. Deletes the original folder after compression.")
	subparser.add_argument("--compress_location", "-cl", help="The location where the compressed search results will be stored.")
	subparser.add_argument("--verbose", "-v", action="store_true")
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

	if args.get("verbose", False):
		if not search_query.get("logging", None):
			search_query["logging"] = ["print"]

		if "print" not in search_query["logging"]:
			search_query["logging"].append("print")

	kwargs = {key: args.get(key, False) for key in {"caption_distributor", "journal_scraper", "figure_separator", "html_scraper"}}

	pipeline = Pipeline(search_query)
	try:
		results = run(pipeline.run(**kwargs))

		for handler in pipeline.logger.handlers:
			handler.flush()

		compress = args.get("compress", "")
		if compress:
			from shutil import make_archive
			name = search_query["name"]
			save_location, _ = splitext(args.get("compress_location", str(pipeline.results_directory)))
			make_archive(save_location, compress, root_dir=str(pipeline.results_directory.parent), base_dir=name)
	except PipelineInterruptionException as e:
		pipeline.logger.exception("The pipeline could not successfully finish running.")
		if hasattr(e, "errno"):
			return e.errno
		return -1

	return 0


if __name__ == "__main__":
	exit(main())
