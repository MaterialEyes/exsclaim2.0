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
from os.path import splitext, isfile
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


def dashboard(dashboard_configuration:PathLike[str]=None, api_configuration:PathLike[str]=None):
	from subprocess import Popen

	current_directory = Path(__file__).parent

	api_configuration = api_configuration or str(current_directory / "api" / "config.py")
	dashboard_configuration = dashboard_configuration or str(current_directory / "dashboard" / "config.py")

	if not isfile(api_configuration):
		raise ValueError(f"The api configuration file \"{api_configuration}\" does not exist.")

	if not isfile(dashboard_configuration):
		raise ValueError(f"The dashboard configuration file \"{dashboard_configuration}\" does not exist.")

	Popen(["gunicorn", "exsclaim.api:app", "-c", api_configuration])
	Popen(["gunicorn", "exsclaim.dashboard:server", "-c", dashboard_configuration], cwd=str(current_directory / "dashboard"))


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
	view_subparser.add_argument("-dc", "--dashboard_configuration", help="The path to the gunicorn configuration file for the dashboard. Example at https://github.com/benoitc/gunicorn/blob/bacbf8aa5152b94e44aa5d2a94aeaf0318a85248/examples/example_config.py")
	view_subparser.add_argument("-ac", "--api_configuration", help="The path to the gunicorn configuration file for the api.")

	args = vars(parser.parse_args(args))

	match args["command"]:
		case "install-deps":
			install_dependencies()
			exit(0)
		case "query":
			return(run_pipeline(**args))
		case "view":
			del args["command"]
			dashboard(**args)
		case "train":
			...


if __name__ == "__main__":
	exit(main())
