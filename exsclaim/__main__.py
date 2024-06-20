from . import Pipeline
try:
	from . import __version__
except ImportError:
	__version__ = None
from argparse import ArgumentParser, BooleanOptionalAction
from json import load
from pathlib import Path


def main():
	parser = ArgumentParser(prog="exsclaim")
	# subparsers = parser.add_subparsers(dest="command", required=True)
	# subparser = subparsers.add_parser("file", help="The path to the JSON file holding the search query.")

	parser.add_argument("-v", "--version", action="version",
						version=f"EXSCLAIM v{__version__}" if __version__ is not None else "EXSCLAIM! version is currently unavailable")
	parser.add_argument("query", help="The path to the JSON file holding the search query.")
	parser.add_argument("--caption_distributor", "-cd", action="store_true")
	parser.add_argument("--journal_scraper", "-js", action="store_true")
	parser.add_argument("--figure_separator", "-fs", action="store_true")
	parser.add_argument("--html_scraper", "-hs", action="store_true")
	args = vars(parser.parse_args())

	query = args.get("query", None)
	if query is None:
		raise ValueError("The search query is required.")

	path = Path(query).absolute()
	if not path.exists():
		raise ValueError(f"The search query file \"{path}\" does not exist.")

	return Pipeline(path).run(**args)


if __name__ == "__main__":
	main()
