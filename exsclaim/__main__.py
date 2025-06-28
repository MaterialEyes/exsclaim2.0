from . import Pipeline, PipelineInterruptionException

try:
	from . import __version__
except ImportError:
	__version__ = None
from argparse import ArgumentParser
from atexit import register
from json import load
from os import PathLike, getenv
from os.path import splitext, isfile
from pathlib import Path


@register
def on_terminate():
	import logging
	logger = logging.getLogger(__name__)

	for handler in logger.handlers:
		handler.flush()

	logging.shutdown()


async def run_pipeline(query=None, verbose:bool=False, compress:str=None, compress_location:str=None,
				 caption_distributor:bool=False, journal_scraper:bool=False, figure_separator:bool=False, **kwargs):
	if query is None:
		raise ValueError("The search query is required.")

	if not any((caption_distributor, journal_scraper, figure_separator)):
		raise ValueError("You must run run the pipeline with at least one tool.")

	compress = compress or ""

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
		results = await pipeline.run(caption_distributor=caption_distributor, journal_scraper=journal_scraper,
								   figure_separator=figure_separator)

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


async def ui(dashboard_configuration:PathLike[str] = None, api_configuration:PathLike[str] = None,
			  blocking:bool = False, api_port:str = "8000", dashboard_port:str = "3000"):
	from signal import signal, SIGINT, SIGTERM, SIGQUIT
	from subprocess import Popen

	exsclaim_dir = Path(__file__).parent.resolve()

	def get_configuration(configuration:PathLike[str], folder:str) -> str:
		configuration = configuration or (exsclaim_dir / folder / "config.py")

		if not isfile(configuration):
			raise FileNotFoundError(f"The configuration file \"{configuration}\" does not exist.")

		configuration = f"file:{configuration}"

		return configuration

	api_configuration = get_configuration(api_configuration, "api")
	dashboard_configuration = get_configuration(dashboard_configuration, "dashboard")

	api = Popen(["/usr/local/bin/hypercorn", "exsclaim.api:app", "-c", api_configuration])
	dashboard = Popen(["/usr/local/bin/gunicorn", "exsclaim.dashboard:server", "-c", dashboard_configuration],
		  cwd=str(exsclaim_dir / "dashboard"))

	def signal_handler(*args):
		api.kill()
		dashboard.kill()
		return 0

	if not blocking:
		return 0

	for sig in (SIGINT, SIGTERM, SIGQUIT):
		signal(sig, signal_handler)
	api.wait()
	dashboard.wait()
	return 0


async def init_db():
	from .db import Database
	db = Database()
	await db.initialize_database()


async def launch(args=None):
	parser = ArgumentParser(prog="exsclaim")

	parser.add_argument("-v", "--version", action="version",
						version=f"EXSCLAIM v{__version__}" if __version__ is not None else "EXSCLAIM! version is currently unavailable.")

	subparsers = parser.add_subparsers(dest="command", required=True)
	query_subparser = subparsers.add_parser("query", help="The path to the JSON file holding the search query.")

	query_subparser.add_argument("query", help="The path to the JSON file holding the search query.")
	query_subparser.add_argument("--caption_distributor", "-cd", action="store_true")
	query_subparser.add_argument("--journal_scraper", "-js", action="store_true")
	query_subparser.add_argument("--figure_separator", "-fs", action="store_true")
	query_subparser.add_argument("--html_scraper", "-hs", action="store_true")
	query_subparser.add_argument("--compress", "-c", choices=["zip", "tar", "gztar", "bztar", "xztar"], help="Compress the search results into a tar.gz file to save space. Deletes the original folder after compression.")
	query_subparser.add_argument("--compress_location", "-cl", help="The location where the compressed search results will be stored.")
	query_subparser.add_argument("--verbose", "-v", action="store_true")

	view_subparser = subparsers.add_parser("ui", help="View search results from EXSCLAIM!")
	view_subparser.add_argument("-dc", "--dashboard_configuration", help="The path to the gunicorn configuration file for the dashboard. Example at https://github.com/benoitc/gunicorn/blob/bacbf8aa5152b94e44aa5d2a94aeaf0318a85248/examples/example_config.py")
	view_subparser.add_argument("-ac", "--api_configuration", help="The path to the gunicorn configuration file for the api.")
	view_subparser.add_argument("-B", "--blocking", action="store_true", help="If the program should wait for the subprocesses to finish before closing.")

	db_subparser = subparsers.add_parser("initialize_db", help="Initializes the PostgreSQL database.")

	for subparser in (query_subparser, view_subparser):
		subparser.add_argument("--force_ollama", action="store_true", help="Fails if EXSCLAIM can't connect to the Ollama API.")

	args = vars(parser.parse_args(args))

	if "force_ollama" in args:
		if args["force_ollama"]:
			from .captions.ollama_llms import Ollama
			Ollama.available_models(silent_fail=False)

		del args["force_ollama"]

	exit_code = None
	match args["command"]:
		case "query":
			exit_code = await run_pipeline(**args)
		case "ui":
			del args["command"]
			exit_code = await ui(**args)
		case "initialize_db":
			exit_code = await init_db()
		case "train":
			...

	if exit_code is not None:
		exit(exit_code)


def main(args=None):
	from asyncio import run
	run(launch(args))


if __name__ == "__main__":
	main()
