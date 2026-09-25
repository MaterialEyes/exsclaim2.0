"""Handles location of output files"""

from ..config import settings
from pathlib import Path
from typing import Any


__all__ = ["initialize_results_dir"]


def initialize_results_dir(query_dict: dict[str, Any]) -> Path:
	"""Determine where to save results for a pipeline run

	Args:
		query_dict (dict[str, Any]): The query dictionary used for the run, which holds the run's name and optional id.
	Returns:
		results_dir (pathlib.Path): Full path to output directory
	Modifies:
		Creates results_dir if it doesn't exist.
	"""
	if (results_dir := query_dict.get("results_dir")) is not None:
		results_dir = Path(results_dir)
	elif (run_id := query_dict.get("run_id")) is not None:
		results_dir = settings.RESULTS_PATH / str(run_id) / query_dict["name"]
	else:
		results_dir = settings.RESULTS_PATH / query_dict["name"]

	results_dir.mkdir(parents=True, exist_ok=True)
	return results_dir
