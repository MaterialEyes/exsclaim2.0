from .pipeline import Pipeline, PipelineInterruptionException
try:
	from . import __version__
except ImportError:
	__version__ = None

from argparse import ArgumentParser
from atexit import register
from os import PathLike
from os.path import isfile
from pathlib import Path
from typing import Optional
from uuid import UUID

import json


@register
def on_terminate():
	import logging
	logger = logging.getLogger(__name__)

	for handler in logger.handlers:
		handler.flush()
		handler.close()

	logging.shutdown()


async def run_pipeline(query=None, verbose: bool = False, compress: Optional[str] = None, compress_location: Optional[str] = None,
					   journal_scraper: bool = False, pdf_scraper: bool = False, caption_distributor: bool = False,
					   figure_separator: bool = False):
	if query is None:
		raise ValueError("The search query is required.")

	compress = compress or ""

	path = Path(query).absolute()
	if not path.exists():
		raise ValueError(f"The search query file \"{path}\" does not exist.")

	with open(path, "r") as f:
		search_query = json.load(f)

	if verbose:
		if not search_query.get("logging", None):
			search_query["logging"] = ["print"]

		elif "print" not in search_query["logging"]:
			search_query["logging"].append("print")

	pipeline = Pipeline(search_query)
	try:
		await pipeline.run(caption_distributor=caption_distributor, pdf_scraper=pdf_scraper,
						   journal_scraper=journal_scraper, figure_separator=figure_separator)
		exit_code = 0
	except PipelineInterruptionException as e:
		pipeline.logger.exception("The pipeline could not successfully finish running.", exc_info=e)
		exit_code = e.errno if hasattr(e, "errno") else 1
	finally:
		pipeline.close_file_handlers()
		if compress is not None:
			pipeline.compress_results(compress, compress_location)

	return exit_code


async def ui(dashboard_configuration: Optional[PathLike[str]] = None, api_configuration: Optional[PathLike[str]] = None,
			 blocking: bool = False, pid_folder: Optional[Path] = None):
	import signal
	from subprocess import Popen

	exsclaim_dir = Path(__file__).parent.resolve()

	def get_configuration(configuration: Optional[PathLike[str]], folder: str) -> str:
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

	if pid_folder is None:
		pid_folder = Path("/tmp")
		if not pid_folder.exists():
			pid_folder = None

	if pid_folder is not None:
		with open(pid_folder / "exsclaim-dashboard.pid", 'w') as f:
			f.write(f"{dashboard.pid}")

		with open(pid_folder / "exsclaim-api.pid", 'w') as f:
			f.write(f"{api.pid}")

	if not blocking:
		return 0

	def signal_handler(*args):
		dashboard.kill()
		api.kill()
		return 0

	for sig in {signal.SIGINT, signal.SIGTERM, signal.SIGQUIT}:
		signal.signal(sig, signal_handler)

	api.wait()
	dashboard.wait()
	return 0


async def init_db():
	from .db import Database
	db = Database()
	await db.initialize_database()


async def train_model(**kwargs):
	from .train import train_model

	del kwargs["command"]

	for (argname, actual_name) in (
		("figures_output_model", "figures_save_path"),
		("labels_output_model", "labels_save_path"),
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


async def upload_training_data(args):
	from .train import append_to_hub, convert_json_to_ds

	json_file: Path = args.json
	image_repo: Optional[str] = args.figure_dataset
	caption_repo: Optional[str] = args.caption_dataset

	if not args.prioritize_old_data and not args.prioritize_new_data:
		prioritize_old_data = True
	else:
		prioritize_old_data = args.prioritize_old_data

	image_ds, caption_ds = convert_json_to_ds([json_file])

	if image_repo is not None:
		append_to_hub(image_repo, image_ds, prioritize_old_data=prioritize_old_data)

	if caption_repo is not None:
		append_to_hub(caption_repo, caption_ds, prioritize_old_data=prioritize_old_data)

	return 0


async def launch(args=None):
	parser = ArgumentParser(prog="exsclaim")

	parser.add_argument("-v", "--version", action="version",
						version=f"EXSCLAIM v{__version__}" if __version__ is not None else "EXSCLAIM! version is currently unavailable.")
	parser.add_argument("-db", "--initialize_db", help="Initializes the PostgreSQL database.", action="store_true")

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
	view_subparser.add_argument("-p", "--pid-folder", type=Path, help="The path to the folder where the pid files are stored. Default is /tmp if it exists, else None.")

	results_subparsers = subparsers.add_parser("upload_results", help="Upload the EXSCLAIM results to the PostgreSQL database if they results weren't fully uploaded.")
	results_subparsers.add_argument("json", help="The path to the `exsclaim.json` file.")

	train_subparser = subparsers.add_parser("train", help="Train a new YOLOv11 model.")
	train_subparser.add_argument("-fi", "--figures_input_model", default=None, help="The path to the detection YOLOv11 model that is being used to train the subfigure coordinate finder.")
	train_subparser.add_argument("-fo", "--figures_output_model", default=None, help="The path where the refined model should be saved.")
	train_subparser.add_argument("-fn", "--detector_name", default=None, help="The name of the detector.")
	train_subparser.add_argument("-li", "--labels_input_model", default=None, help="The path to the detection YOLOv11 model that is being used to train the label coordinate finder.")
	train_subparser.add_argument("-lo", "--labels_output_model", default=None, help="The path where the refined model should be saved.")
	train_subparser.add_argument("-ln", "--labels_name", default=None, help="The name of the detector.")
	train_subparser.add_argument("-ci", "--classification_input_model", default=None, help="The path to the classification YOLOv11 model that is being used to train.")
	train_subparser.add_argument("-co", "--classification_output_model", default=None, help="The path where the refined model should be saved.")
	train_subparser.add_argument("-cn", "--classifier_name", default=None, help="The name of the classifier.")
	train_subparser.add_argument("-ts", "--test_size", default=0.1, help="The size of the test set.")
	train_subparser.add_argument("-r", "--random_state", type=int, default=42, help="The random state to use.")
	train_subparser.add_argument("-d", "--dataset_dir", default=None, help="The path to the dataset directory.")
	train_subparser.add_argument("-p", "--project", default=None, help="The name of the wandb project.")

	dataset_subparser = subparsers.add_parser("upload_training_data", help="Uploads training data instances to a HuggingFace dataset.")
	dataset_subparser.add_argument("json", help="The path to the training data json downloaded from the EXSCLAIM site.", type=Path),
	dataset_subparser.add_argument("-f", "--figure_dataset", help="The repo id of the dataset where the figure information should be stored.")
	dataset_subparser.add_argument("-c", "--caption_dataset", help="The repo id of the dataset where the caption information should be stored.")
	group = dataset_subparser.add_mutually_exclusive_group()
	group.add_argument("-o", "--prioritize_old_data", action="store_true",
	                   help="If there is a collision between the current dataset and the new dataset, the data in the old dataset with the same conflicting IDs will be kept.")
	group.add_argument("-n", "--prioritize_new_data", action="store_true",
	                   help="If there is a collision between the current dataset and the new dataset, the data in the new dataset with the same conflicting IDs will be kept.")

	parsed_args = parser.parse_args(args)
	args = vars(parsed_args)

	if parsed_args.initialize_db:
		await init_db()
	del args["initialize_db"]

	exit_code = None
	match args["command"]:
		case "query":
			exit_code = await run_pipeline(**args)
		case "ui":
			del args["command"]
			exit_code = await ui(**args)
		case "train":
			exit_code = await train_model(**args)
		case "upload_results":
			exit_code = await upload_results(args["json"])
		case "upload_training_data":
			exit_code = await upload_training_data(parsed_args)

	return exit_code


def main(args=None):
	from asyncio import run
	exit_code = run(launch(args))

	if exit_code is not None:
		exit(exit_code)


if __name__ == "__main__":
	main()
