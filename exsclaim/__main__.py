from . import Pipeline
try:
	from . import __version__
except ImportError:
	__version__ = None
from argparse import ArgumentParser, BooleanOptionalAction
from atexit import register
from functools import wraps
from json import load
from os import getenv
from pathlib import Path


@register
def on_terminate():
	import logging
	logger = logging.getLogger(__name__)

	for handler in logger.handlers:
		handler.flush()

	logging.shutdown()


def ntfy(ntfy_link:str, topic:str, on_completion="results", on_error="error"):
	"""
	Notify a user about the running of a function.
	:param str ntfy_link: The link to the NTFY server.
	:param str topic: The topic to notify.
	:param str | None on_completion: The message that should be sent when the function has successfully completed.
	Put "results" to send the exact results to the NTFY server.
	:param str | None on_error: The message that should be sent when the function has hit an error and did not finish.
	Put "error" to send the exact error to the NTFY server.
	:return:
	"""
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			data = None
			try:
				result = func(*args, **kwargs)
				if on_completion is None:
					return result
				elif on_completion == "results":
					data = str(result)
				else:
					data = on_completion
				return result
			except Exception as e:
				if on_error is None:
					raise e
				elif on_error == "error":
					from traceback import format_exception
					data = ' '.join(format_exception(e))
				else:
					data = on_error
				raise e
			finally:
				if data is None or ntfy_link is None:
					return

				from requests import post
				post(f"{ntfy_link.rstrip('/')}/{topic}", data=data)
		return wrapper
	return decorator


@ntfy(getenv("NTFY_LINK", None), "exsclaim")
def main():
	parser = ArgumentParser(prog="exsclaim")
	# subparsers = parser.add_subparsers(dest="command", required=True)
	# subparser = subparsers.add_parser("file", help="The path to the JSON file holding the search query.")

	parser.add_argument("-v", "--version", action="version",
						version=f"EXSCLAIM v{__version__}" if __version__ is not None else "EXSCLAIM! version is currently unavailable.")
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

	kwargs = {key: args.get(key, False) for key in {"caption_distributor", "journal_scraper", "figure_separator", "html_scraper"}}
	return Pipeline(path).run(**kwargs)


if __name__ == "__main__":
	main()
