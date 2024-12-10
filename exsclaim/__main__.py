from . import Pipeline, PipelineInterruptionException

try:
	from . import __version__
except ImportError:
	__version__ = None
from argparse import ArgumentParser
from asyncio import run
from atexit import register
from json import load
from os import PathLike
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


def run_pipeline(query=None, verbose:bool=False, compress:str=None, compress_location:str=None,
				 caption_distributor:bool=False, journal_scraper:bool=False, figure_separator:bool=False, html_scraper:bool=False, **kwargs):
	compress = compress or ""

	if query is None:
		raise ValueError("The search query is required.")

	if not any((caption_distributor, journal_scraper, figure_separator, html_scraper)):
		raise ValueError("You must run run the pipeline with at least one tool.")

	path = Path(query).absolute()
	if not path.exists():
		raise ValueError(f"The search query file \"{path}\" does not exist.")

	with open(path, "r") as f:
		search_query = load(f)

	if verbose:
		if not search_query.get("logging", None):
			search_query["logging"] = ["print"]

		if "print" not in search_query["logging"]:
			search_query["logging"].append("print")

	pipeline = Pipeline(search_query)
	try:
		results = run(pipeline.run(caption_distributor=caption_distributor, journal_scraper=journal_scraper, figure_separator=figure_separator, html_scraper=html_scraper))

		for handler in pipeline.logger.handlers:
			handler.flush()

		if compress:
			from shutil import make_archive
			name = search_query["name"]
			save_location, _ = splitext(compress_location or str(pipeline.results_directory))
			make_archive(save_location, compress, root_dir=str(pipeline.results_directory.parent), base_dir=name)
	except PipelineInterruptionException as e:
		pipeline.logger.exception("The pipeline could not successfully finish running.")
		if hasattr(e, "errno"):
			return e.errno
		return -1

	return 0


def dashboard(configuration:PathLike[str]=None, port:str=None, fastapi_port:str=None, **kwargs):
	from .dashboard import app as dashboard
	from .api import app as fastapi, StandaloneApplication
	from threading import Thread

	fastapi.configuration_ini = configuration
	port = port or "8000"
	fastapi_port = fastapi_port or "3000"

	fastapi_app = StandaloneApplication(fastapi, bind=f"127.0.0.1:{fastapi_port}")
	dashboard_app = StandaloneApplication(dashboard, bind=f"127.0.0.1:{port}")

	threads = [
		Thread(target=lambda app: app.run(), args=(fastapi_app,)),
		Thread(target=lambda app: app.run(), args=(dashboard_app,)),
	]

	for thread in threads:
		thread.start()

	for thread in threads:
		thread.join()


def main(args=None):
	parser = ArgumentParser(prog="exsclaim")

	parser.add_argument("-v", "--version", action="version",
						version=f"EXSCLAIM v{__version__}" if __version__ is not None else "EXSCLAIM! version is currently unavailable.")

	subparsers = parser.add_subparsers(dest="command", required=True)
	subparsers.add_parser("install-deps", help="Install dependencies for EXSCLAIM!'s dependencies.")
	query_subparser = subparsers.add_parser("query", help="The path to the JSON file holding the search query.")

	query_subparser.add_argument("query", help="The path to the JSON file holding the search query.")
	query_subparser.add_argument("--caption_distributor", "-cd", action="store_true")
	query_subparser.add_argument("--journal_scraper", "-js", action="store_true")
	query_subparser.add_argument("--figure_separator", "-fs", action="store_true")
	query_subparser.add_argument("--html_scraper", "-hs", action="store_true")
	query_subparser.add_argument("--compress", "-c", choices=["zip", "tar", "gztar", "bztar", "xztar"], help="Compress the search results into a tar.gz file to save space. Deletes the original folder after compression.")
	query_subparser.add_argument("--compress_location", "-cl", help="The location where the compressed search results will be stored.")
	query_subparser.add_argument("--verbose", "-v", action="store_true")

	view_subparser = subparsers.add_parser("view", help="View search results from EXSCLAIM!")
	view_subparser.add_argument("-c", "--configuration", help="The path to the ini configuration file.")
	view_subparser.add_argument("-p", "--port", help="The port for the dashboard.")
	view_subparser.add_argument("-fp", "--fastapi_port", help="The port for the API.")

	args = vars(parser.parse_args(args))

	match args["command"]:
		case "install-deps":
			install_dependencies()
			exit(0)
		case "query":
			run_pipeline(**args)
		case "view":
			dashboard(**args)
		case "train":
			...


if __name__ == "__main__":
	exit(main())
