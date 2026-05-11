from .pipeline import Pipeline, PipelineInterruptionException

try:
	from . import __version__
except ImportError:
	__version__ = None
from argparse import ArgumentParser
from atexit import register
from json import load
from os import PathLike, chmod
from os.path import splitext, isfile
from pathlib import Path
from shutil import make_archive
from uuid import UUID


@register
def on_terminate():
	import logging
	logger = logging.getLogger(__name__)

	for handler in logger.handlers:
		handler.flush()

	logging.shutdown()


async def run_pipeline(query=None, verbose: bool = False, compress: str = None, compress_location: str = None,
					   journal_scraper: bool = False, pdf_scraper: bool = False, caption_distributor: bool = False,
					   figure_separator: bool = False, run_id: UUID = None, **kwargs):
	if query is None:
		raise ValueError("The search query is required.")

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
		results = await pipeline.run(caption_distributor=caption_distributor, pdf_scraper=pdf_scraper,
									 journal_scraper=journal_scraper, figure_separator=figure_separator, run_id=run_id)

		for handler in pipeline.logger.handlers:
			handler.flush()

		if compress:
			name = search_query["name"]
			save_location, _ = splitext(compress_location or str(pipeline.results_directory))
			make_archive(save_location, compress, root_dir=str(pipeline.results_directory.parent), base_dir=name)

			try:
				chmod(save_location, 0o775)
			except PermissionError:
				pipeline.logger.warning(f"Could not change the permissions of {save_location} to 775.")

	except PipelineInterruptionException as e:
		pipeline.logger.exception("The pipeline could not successfully finish running.")
		if hasattr(e, "errno"):
			return e.errno
		return -1

	return 0


async def ui(dashboard_configuration:PathLike[str] = None, api_configuration:PathLike[str] = None, blocking:bool = False):
	from signal import signal, SIGINT, SIGTERM, SIGQUIT
	from subprocess import Popen

	exsclaim_dir = Path(__file__).parent.resolve()

	def get_configuration(configuration: PathLike[str], folder:str) -> str:
		configuration = configuration or (exsclaim_dir / folder / "config.py")

		if not isfile(configuration):
			raise FileNotFoundError(f"The configuration file \"{configuration}\" does not exist.")

		configuration = f"file:{configuration}"

		return configuration

	api_configuration = get_configuration(api_configuration, "api")
	dashboard_configuration = get_configuration(dashboard_configuration, "dashboard")

	api = Popen(["/usr/local/bin/hypercorn", "-c", api_configuration, "exsclaim.api:get_app()"])
	dashboard = Popen(["/usr/local/bin/gunicorn", "-c", dashboard_configuration, "exsclaim.dashboard:server"],
		  cwd=str(exsclaim_dir / "dashboard"))

	if not blocking:
		return 0

	def signal_handler(*args):
		dashboard.kill()
		api.kill()
		return 0

	for sig in {SIGINT, SIGTERM, SIGQUIT}:
		signal(sig, signal_handler)

	api.wait()
	dashboard.wait()
	return 0


async def init_db():
	from .db import Database
	db = Database()
	await db.initialize_database()


async def train_model(**kwargs):
	from .figures.train import train_model

	del kwargs["command"]

	for (argname, actual_name) in (
		("json", "json_file_path"),
		("detection_output_model", "detection_save_path"),
		("classification_output_model", "classification_save_path"),
	):
		kwargs[actual_name] = kwargs[argname]
		del kwargs[argname]

	await train_model(**kwargs)


async def upload_results(csv_dir: PathLike[str], result_id: UUID, strict: bool = False):
	from .db import Database
	from csv import reader
	from re import compile

	csv_path = Path(csv_dir).resolve()
	if not csv_path.is_dir():
		raise FileNotFoundError(f"Could not find csv directory {csv_path}.")

	file_regex = compile("_")
	csv_info = {
		"article": [],
		"figure": [],
		"subfigure": [],
		"subfigure_label": [],
		"scale_label": [],
		"scale": []
	}

	for key in csv_info.keys():
		file = csv_path / f"{file_regex.sub('', key)}.csv"
		if not file.is_file():
			if strict:
				raise FileNotFoundError(f"Could not find file {file}.")
			print(f"Cannot find file {file}, skipping these contents.")

		with open(csv_path / file, "r") as f:
			csv_reader = reader(f)
			csv_info[key] = [list(row) for row in csv_reader]

	db = Database()
	await db.ensure_connection()
	await db.upload(csv_info, result_id)


async def launch(args=None):
	parser = ArgumentParser(prog="exsclaim")

	parser.add_argument("-v", "--version", action="version",
						version=f"EXSCLAIM v{__version__}" if __version__ is not None else "EXSCLAIM! version is currently unavailable.")

	subparsers = parser.add_subparsers(dest="command", required=True)
	query_subparser = subparsers.add_parser("query", help="The path to the JSON file holding the search query.")

	query_subparser.add_argument("query", help="The path to the JSON file holding the search query.")
	query_subparser.add_argument("--journal_scraper", "--journal", "-js", action="store_true")
	query_subparser.add_argument("--pdf_scraper", "--pdf", "-ps", action="store_true")
	query_subparser.add_argument("--caption_distributor", "--caption", "-cd", action="store_true")
	query_subparser.add_argument("--figure_separator", "--figure", "-fs", action="store_true")
	query_subparser.add_argument("--html_scraper", "-hs", action="store_true")
	query_subparser.add_argument("--compress", "-c", choices=["zip", "tar", "gztar", "bztar", "xztar"], help="Compress the search results into a tar.gz file to save space. Deletes the original folder after compression.")
	query_subparser.add_argument("--compress_location", "-cl", help="The location where the compressed search results will be stored.")
	query_subparser.add_argument("--verbose", "-v", action="store_true")

	view_subparser = subparsers.add_parser("ui", help="View search results from EXSCLAIM!")
	view_subparser.add_argument("-dc", "--dashboard_configuration", help="The path to the gunicorn configuration file for the dashboard. Example at https://github.com/benoitc/gunicorn/blob/bacbf8aa5152b94e44aa5d2a94aeaf0318a85248/examples/example_config.py")
	view_subparser.add_argument("-ac", "--api_configuration", help="The path to the gunicorn configuration file for the api.")
	view_subparser.add_argument("-B", "--blocking", action="store_true", help="If the program should wait for the subprocesses to finish before closing.")

	subparsers.add_parser("initialize_db", help="Initializes the PostgreSQL database.")

	results_subparsers = subparsers.add_parser("upload_results", help="Upload the EXSCLAIM results to the PostgreSQL database if they results weren't fully uploaded.")
	results_subparsers.add_argument("json", help="The path to the `exsclaim.json` file.")

	train_subparser = subparsers.add_parser("train", help="Train a new YOLOv11 model.")
	train_subparser.add_argument("json", help="The json file holding the training data.")
	train_subparser.add_argument("-di", "--detection_input_model", default=None, help="The path to the detection YOLOv11 model that is being used to train.")
	train_subparser.add_argument("-do", "--detection_output_model", default=None, help="The path where the refined model should be saved.")
	train_subparser.add_argument("-dn", "--detector_name", default=None, help="The name of the detector.")
	train_subparser.add_argument("-ci", "--classification_input_model", default=None, help="The path to the classification YOLOv11 model that is being used to train.")
	train_subparser.add_argument("-co", "--classification_output_model", default=None, help="The path where the refined model should be saved.")
	train_subparser.add_argument("-cn", "--classifier_name", default=None, help="The name of the classifier.")
	train_subparser.add_argument("-ts", "--test_size", default=1_164, help="The size of the test set.")
	train_subparser.add_argument("-r", "--random_state", type=int, default=42, help="The random state to use.")
	train_subparser.add_argument("-d", "--dataset_dir", default=None, help="The path to the dataset directory.")
	train_subparser.add_argument("-p", "--project", default=None, help="The name of the wandb project.")

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
			exit_code = await train_model(**args)
		case "upload_results":
			exit_code = await upload_results(args["json"])

	return exit_code


def main(args=None):
	from asyncio import run
	exit_code = run(launch(args))

	if exit_code is not None:
		exit(exit_code)


if __name__ == "__main__":
	main()
