from ...config import settings
from ...db import get_db_session
from ..models import Results, User, ExsclaimJSONResponse, Status, get_guest_uuid, ClassificationCodes, PreviousRunFilters, QueryTools, Query, gen_uuid7, SaveExtensions
from .users import ActiveUser, CurrentUser

import fastapi
import logging
import tarfile

from asyncio import all_tasks, create_task, CancelledError, Task
from base64 import b64encode
from datetime import datetime as dt
from exsclaim.__main__ import run_pipeline as exsclaim_pipeline
from fastapi import Body, Depends, status
from hashlib import sha256
from json import dump
from os import listdir
from pathlib import Path
from sqlalchemy import select, update, insert, delete
from shutil import make_archive, get_archive_formats
from starlette.requests import Request
from starlette.responses import Response, FileResponse, JSONResponse
from sqlalchemy import text
from tarfile import open as tar_open
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Annotated, Literal, Optional
from uuid import UUID
from zoneinfo import ZoneInfo


router = fastapi.APIRouter()
_EXAMPLE_UUID = get_guest_uuid()
cache = dict()
ARCHIVE_FORMATS = set(map(lambda _format: _format[0], get_archive_formats()))


async def get_temp_dir():
	"""Creates a temporary directory that won't be destroyed until after the response has been sent."""
	tmp_dir = TemporaryDirectory()
	try:
		yield tmp_dir.name
	finally:
		tmp_dir.cleanup()


def get_pipeline_task_name(result_id: UUID) -> str:
	return f"pipeline_{result_id}"


async def run_exsclaim(_id: UUID, search_query_location: Path, logger: logging.Logger, tools: QueryTools):
	db_result: Status = Status.ERROR
	pipeline_task = create_task(
		name=get_pipeline_task_name(_id),
		coro=exsclaim_pipeline(query=search_query_location, compress="gztar", verbose=settings.DEBUG,
		                       compress_location=str(settings.RESULTS_PATH / str(_id)), **tools.model_dump())
	)

	try:
		result_code = await pipeline_task
		if result_code == 0:
			db_result = Status.FINISHED
	except (KeyboardInterrupt, CancelledError) as e:
		db_result = Status.STOPPED
		logger.info(f"Run {_id} was stopped during processing: {e}")
		result_code = 1
	except Exception as e:
		db_result = Status.ERROR
		logger.exception(f"An error occurred when running pipeline with Result ID: {_id}.", exc_info=e)
		result_code = -1
	finally:
		async with get_db_session() as session:
			await session.execute(update(Results).where(Results.id == _id).values(status=db_result, end_time=dt.now()))
			await session.commit()

	return result_code


@router.api_route("/query", methods=["POST", "HEAD"], responses={
	202: {
		"description": "Query successfully submitted.",
		"content": {
			"application/json": {
				"schema": {
					"type": "object",
					"properties": {
						"message": {
							"type": "string",
						},
						"result_id": {
							"type": "string",
							"format": "uuid"
						},
					}
				},
				"example": {
					"message": "Thank you, your request is currently being processed.",
					"result_id": str(_EXAMPLE_UUID)
				}
			},
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": f"Thank you, your request is currently being processed, and the results can be found using id: {_EXAMPLE_UUID}."
			}
		}
	},
	500: {
		"description": "An internal database error stopped the query from being submitted.",
		"content": {
			"application/json": {
				"schema": {
					"type": "object",
					"properties": {
						"message": {
							"type": "string",
						},
					}
				},
				"example": {
					"message": "An error occurred connecting to the database. Please try again later.",
				}
			},
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": "An error occurred connecting to the database. Please try again later."
			}
		}
	},
	503: {
		"description": "An internal error stopped the query from being submitted.",
		"content": {
			"application/json": {
				"schema": {
					"type": "object",
					"properties": {
						"message": {
							"type": "string",
						},
					}
				},
				"example": {
					"message": "An unknown error occurred within the EXSCLAIM! API. Please try again later.",
				}
			},
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": "An unknown error occurred within the EXSCLAIM! API. Please try again later."
			}
		}
	}
}, tags=["Using EXSCLAIM"])
async def query(request: Request, search_query: Query, background_tasks: fastapi.BackgroundTasks, user: CurrentUser) -> Response:
	logger: logging.Logger = request.state.logger

	send_json = request.headers.get("accept", "") == "application/json"
	try:
		uuid = gen_uuid7()
		str_uuid = str(uuid)

		exsclaim_input = {
			"name": search_query.name if search_query else "exsclaim_results",
			"run_id": str_uuid,
			"journal_family": search_query.journal_family.lower(),
			"maximum_scraped": search_query.maximum_scraped,
			"sortby": search_query.sortby,
			"query": {
				"search_field_1": {
					"term": search_query.term,
					"synonyms": search_query.synonyms
				}
			},
			"llm": search_query.llm,
			"model_key": search_query.model_key,
			"open": search_query.open,
			"save_format": search_query.save_format,
			"logging": ["exsclaim.log"],
			"notifications": search_query.notifications.model_dump(),
			"base_run_id": str(search_query.base_run_id) if search_query is not None else None,
		}

		results_dir = settings.RESULTS_PATH / str_uuid
		results_dir.mkdir(exist_ok=True, parents=True)
		logger = request.app.logger
		with open(results_dir / "search_query.json", "w") as f:
			dump(exsclaim_input, f, indent='\t')

		background_tasks.add_task(run_exsclaim, uuid, results_dir / "search_query.json", logger, search_query.tools)

		db_json = exsclaim_input.copy()
		db_json["model_key"] = "model_key" in db_json.keys()
		for unnecessary_key in ["notifications", "results_dir", "logging"]:
			if unnecessary_key in db_json:
				db_json.pop(unnecessary_key)

		for sanitized_keys in ("name", "term", "synonyms"):
			...  # TODO: Sanitize these user inputs

		async with get_db_session() as session:
			await session.execute(insert(Results).values(
				id=uuid,
				user_id=user.id,
				search_query=db_json,
				extension=SaveExtensions.TAR)
			)
			await session.commit()

		if send_json:
			response = ExsclaimJSONResponse(
				{"message": "Thank you, your request is currently being processed.", "result_id": str_uuid},
				status_code=status.HTTP_202_ACCEPTED, media_type="application/json")
		else:
			response = Response(
				f"Thank you, your request is currently being processed, and the results can be found using id: {str_uuid}.",
				status_code=status.HTTP_202_ACCEPTED, media_type="text/plain")
	except OSError as e:
		logger.exception(e)
		message = "An error occurred connecting to the database. Please try again later."
		if send_json:
			response = ExsclaimJSONResponse({"message": message}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, media_type="application/json")
		else:
			response = Response(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, media_type="text/plain")
	except Exception as e:
		print(f"{e}")
		logger.exception("An unknown error occurred when querying.", exc_info=e)
		message = "An unknown error occurred within the EXSCLAIM! API. Please try again later."
		if send_json:
			response = ExsclaimJSONResponse({"message": message}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, media_type="application/json")
		else:
			response = Response(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, media_type="text/plain")

	return response


@router.api_route("/status/{result_id}", methods=["GET", "HEAD"], tags=["Using EXSCLAIM"],
		responses={
			200: {
				"description": "Status Found for ID.",
				"content": {
					"application/json": {
						"schema": {
							"type": "object",
							"properties": {
								"results_status": {
									"type": "string",
								},
								"start_time": {
									"type": "string",
									"format": "date-time"
								},
								"end_time": {
									"type": "string",
									"format": "date-time"
								},
								"run_time": {
									"type": "number",
									"format": "float"
								},
							}
						},
						"example": {
							"results_status": "Finished.",
							"start_time": "2024-07-15T13:00:12.712358+00:00",
							"end_time": "2024-07-15T13:06:58.928669+00:00",
							"run_time": 3641.92811
						}
					}
				}
			},
			404: {
				"description": "ID Not Found.",
				"content": {
					"application/json": {
						"schema": {
							"type": "object",
							"properties": {
								"results_status": {
									"type": "string"
								},
								"message": {
									"type": "string"
								}
							}
						},
						"example": {
							"results_status": "Finished",
							"message": f"There is no query recorded in our database with id: \"{_EXAMPLE_UUID}\".",
						}
					}
				}
			},
			422: {
				"description": "Improper UUID Format for ID.",
				"content": {
					"application/json": {
						"schema": {
							"type": "object",
							"properties": {
								"results_status": {
									"type": "null"
								},
								"message": {
									"type": "string"
								}
							}
						},
						"example": {
							"results_status": None,
							"message": f"\"{_EXAMPLE_UUID}\"is not a valid UUID.",
						}
					}
				}
			},
			500: {
				"description": "Unknown Internal Server Error.",
				"content": {
					"application/json": {
						"schema": {
							"type": "object",
							"properties": {
								"results_status": {
									"type": "string"
								},
								"start_time": {
									"type": "string"
								},
								"end_time": {
									"type": "string"
								},
								"run_time": {
									"type": "number",
									"format": "float"
								},
							}
						},
						"example": {
							"results_status": "Closed due to an error.",
							"start_time": "2024-07-15T13:00:12.712358+00:00",
							"end_time": "2024-07-15T13:06:58.928669+00:00",
							"run_time": 3641.92811
						}
					}
				}
			},
			210: {
				"description": "Internal Database Error.",
				"content": {
					"application/json": {
						"schema": {
							"type": "object",
							"properties": {
								"results_status": {
									"type": "string"
								},
								"message": {
									"type": "string"
								}
							}
						},
						"example": {
							"results_status": "Unknown",
							"message": "An unknown error has occurred within the database. Please try again later.",
						}
					}
				}
			},
		})
async def status_def(request: Request, result_id: UUID, user: CurrentUser):
	logger: logging.Logger = request.state.logger
	async with get_db_session() as session:
		results = await session.execute(select(Results).where(Results.id == result_id))
		result: Results = results.scalar_one_or_none()

	if not User.has_permission(user, result):
		return ExsclaimJSONResponse({
			"results_status": "Not Found",
			"message": f"There is no query recorded in our database with id: {result_id}."
		}, status_code=status.HTTP_404_NOT_FOUND, media_type="application/json")

	results_status, start_time, end_time = result.status, result.start_time, result.end_time

	time_diff = (end_time or dt.now(tz=start_time.tzinfo)) - start_time

	match results_status:
		case Status.RUNNING:
			status_code = status.HTTP_200_OK
		case Status.FINISHED:
			status_code = status.HTTP_202_ACCEPTED
		case Status.STOPPED:
			status_code = 209
		case Status.ERROR:
			status_code = 210
		case _:
			logger.exception(f"Unknown results_status {results_status} when checking results_status of {result_id}.")
			return ExsclaimJSONResponse(dict(message="An unknown results_status was saved in our database. Try again later."),
						 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, media_type="application/json")

	json = dict(
		status=f"{results_status}.",
		start_time=start_time,
		end_time=end_time,
		run_time=time_diff.total_seconds()
	)

	headers = dict()
	if results_status == Status.FINISHED:
		headers = {"Location": f"/results/{result_id}"}

	return ExsclaimJSONResponse(json, status_code=status_code, media_type="application/json", headers=headers)


@router.api_route("/stop/{result_id}", methods=["GET", "HEAD"], tags=["Using EXSCLAIM"])
async def stop_run(result_id: UUID, user: CurrentUser):
	async with get_db_session() as session:
		results = await session.execute(select(Results).where(Results.id == result_id))
		result: Results = results.scalar_one_or_none()

	if result.user_id != user.id:
		return ExsclaimJSONResponse({
			"status": "Not Found",
			"message": f"There is no query recorded in our database with id: {result_id}."
		}, status_code=status.HTTP_404_NOT_FOUND)

	match result.status:
		case Status.FINISHED:
			return ExsclaimJSONResponse({
				"message": f"Run {result_id} has already finished running."
			}, status_code=status.HTTP_406_NOT_ACCEPTABLE)
		case Status.ERROR:
			return ExsclaimJSONResponse({
				"message": f"Run {result_id} has already stopped running due to an error."
			}, status_code=status.HTTP_412_PRECONDITION_FAILED)
		case Status.STOPPED:
			return ExsclaimJSONResponse({
				"message": f"Run {result_id} has already stopped early."
			}, status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

	# The pipeline is still running for the pipeline
	task_name = get_pipeline_task_name(result_id)
	tasks = tuple(filter(lambda task: task.get_name() == task_name, all_tasks()))

	if len(tasks) == 0:
		return ExsclaimJSONResponse({
			"message": f"Could not find a running pipeline for {result_id}. Please try again later."
		}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
	elif len(tasks) > 1:
		return ExsclaimJSONResponse({
			"message": f"Found too many running pipelines for {result_id}. Please try again later."
		}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

	task: Task = tasks[0]
	task.cancel("Pipeline stopped upon user request.")
	return ExsclaimJSONResponse({
		"message": f"Stopped the pipeline for {result_id}."
	}, status_code=status.HTTP_200_OK)


@router.api_route("/results/{result_id}", methods=["GET", "HEAD"], tags=["Using EXSCLAIM"], responses={
	200: {
		"description": "Results Compressed and Included.",
		"content": {
			"application/octet-stream": {
				"schema": {
					"type": "string"
				},
				"example": ""
			}
		}
	},
	202: {
		"description": "Query Currently Running.",
		"content": {
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": "The results are still being compiled.",
			}
		}
	},
	404: {
		"description": "ID Not Found.",
		"content": {
			"text/plain": {
				"schema": {
					"type": "string"
				},
				"example": f"There is no query recorded in our database with id: \"{_EXAMPLE_UUID}\"."
			}
		}
	},
	422: {
		"description": "Improper UUID Format for ID or Improper Compression Value.",
		"content": {
			"text/plain": {
				"schema": {
				"type": "string",
			},
			"example": "unknown archive format 'gztar21'",
			}
		}
	},
	501: {
		"description": "Internal Database Error.",
		"content": {
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": f"The database has an unknown status for id \"{_EXAMPLE_UUID}\" and cannot send the results at this time."
			}
		}
	},
	503: {
		"description": "Error caused the query to not finish which results in no results.",
		"content": {
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": "The results could not be compiled due to an error. Please submit your query again."
			}
		}
	},
})
async def download(request: Request, result_id: UUID, user: CurrentUser, compression: str = "default",
                   filename: Literal["name", "id"] = "id", tmp_dir_name: str = Depends(get_temp_dir)) -> Response:
	async with get_db_session() as session:
		results = await session.execute(select(Results).where(Results.id == result_id))
		result: Results = results.scalar_one_or_none()

	if not User.has_permission(user, result):
		return Response(f"There is no query recorded in our database with id: {result_id}.", status_code=status.HTTP_404_NOT_FOUND,
		                media_type="text/plain")

	# Set the filename to be id by default
	if compression != "default":
		if compression not in ARCHIVE_FORMATS:
			return Response(
				f"Unknown archive format '{compression}'. Check /compression_types to see what values are allowed.",
				status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, media_type="text/plain")

	else:  # compression == "default"
		if platform := request.headers.get("sec-ch-ua-platform", ""):
			match platform.replace('"', ""):
				case "Linux":
					compression = "gztar"
				case "Android" | "Chrome OS" | "Chromium OS" | "iOS" | "macOS" | "Windows" | "Unknown" | _:
					compression = "zip"
		else:
			os = request.headers.get("user-agent", "")
			if "Linux" in os:
				compression = "gztar"
			else:
				compression = "zip"

	match result.status:
		case Status.RUNNING:
			return Response("The results are still being compiled.", status_code=status.HTTP_202_ACCEPTED, media_type="text/plain")
		case Status.STOPPED:
			return Response("The results were closed by user or admin intervention.",
	               status_code=status.HTTP_200_OK, media_type="text/plain")
		case Status.ERROR:
			return Response("The results could not be compiled due to an error. Please submit your query again.",
	               status_code=status.HTTP_503_SERVICE_UNAVAILABLE, media_type="text/plain")
		case Status.FINISHED:
			...
		case _:
			return Response(
				f"The database has an unknown status for id \"{result_id}\" and cannot send the results at this time.",
				status_code=status.HTTP_501_NOT_IMPLEMENTED, media_type="text/plain")

	results_file = (settings.RESULTS_PATH / str(result_id)).with_suffix(".tar.gz")
	if not results_file.exists():
		return Response(
			"The result id was found in our database, but the corresponding results file could not be found. Please try again later.",
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, media_type="text/plain")

	if compression == "gztar":
		return FileResponse(results_file, status_code=status.HTTP_200_OK, stat_result=results_file.stat())

	tmp_dir = Path(tmp_dir_name)

	with tar_open(results_file) as f:
		f.extractall(tmp_dir)

	name = [file for file in listdir(tmp_dir) if "." not in file][0]

	results_file = Path(
		make_archive(str(tmp_dir / str(result_id)), compression, root_dir=str(tmp_dir), base_dir=name)
	)

	if filename == "name":
		filename = results_file.with_stem(name).name
	elif filename == "id":
		filename = results_file.name

	return FileResponse(results_file, status_code=status.HTTP_200_OK, stat_result=results_file.stat(),
	                    headers={"Content-Disposition": f"inline ; filename = \"{filename}\""})


@router.delete("/results/{result_id}", tags=["Using EXSCLAIM"])
async def delete_results(result_id: UUID, user: CurrentUser) -> Response:
	async with get_db_session() as session:
		results = await session.execute(select(Results).where(Results.id == result_id))
		result: Results = results.scalar_one_or_none()

		if result is None or not User.has_permission(user, result):
			return JSONResponse(dict(detail=f"There is no query recorded in our database with id: {result_id}.", result_id=str(result_id)),
								status_code=status.HTTP_404_NOT_FOUND)
		if result.user_id == get_guest_uuid():
			return JSONResponse(dict(detail="Runs started by guest users (anonymous/not logged in) cannot be deleted."),
								status_code=status.HTTP_401_UNAUTHORIZED)

		await session.execute(delete(Results).where(Results.id == result_id))
	return JSONResponse(dict(detail="Run deleted", result_id=str(result_id)), status_code=status.HTTP_200_OK)


STARTED_BACKING_UP_LOGS = dt(2026, 7, 8, 9, 30, tzinfo=ZoneInfo("America/Chicago"))


@router.api_route("/results/{result_id}/logs", methods=["GET", "HEAD"], tags=["Using EXSCLAIM"])
async def download_logs(request: Request, result_id: UUID, user: CurrentUser):
	logger = request.state.logger

	async with get_db_session() as session:
		results = await session.execute(select(Results).where(Results.id == result_id))
		result: Optional[Results] = results.scalar_one_or_none()

	if result is None or not User.has_permission(user, result):
		return Response(f"There is no query recorded in our database with id: {result_id}.",
		                status_code=status.HTTP_404_NOT_FOUND, media_type="text/plain")

	name = result.search_query["name"]
	if result.start_time < STARTED_BACKING_UP_LOGS:
		missing_logs = Response("Results for runs started before July 8, 2026 weren't ensured to be saved.",
								status_code=status.HTTP_404_NOT_FOUND, media_type="text/plain")
	else:
		missing_logs = Response("Could not find the saved results in our server, even though they should have been saved.",
								status_code=status.HTTP_404_NOT_FOUND, media_type="text/plain")

	if result.status == Status.RUNNING:
		logs_path = settings.RESULTS_PATH / str(result_id) / name / "exsclaim.log"
		if not logs_path.exists():
			logger.error(f"Could not find the log file for run \"{result_id}\" in {logs_path}.")
			return missing_logs

		with open(logs_path, "rb") as f:
			logs = f.read()
	else:
		results_path = settings.RESULTS_PATH / f"{result_id}.tar.gz"
		if not (results_path.exists() and tarfile.is_tarfile(results_path)):
			logger.error(f"Could not find the log file for run \"{result_id}\" in {results_path}.")
			return missing_logs

		with tarfile.open(results_path, "r:gz") as tar:
			try:
				f = tar.extractfile(f"{name}/exsclaim.log")
				logs: bytes = f.read().strip()
			except KeyError as e:
				logger.exception(f"Could not find the log file for run \"{result_id}\" in {results_path}.", exc_info=e)
				return Response("Could not find log file in the saved results file.", status_code=status.HTTP_404_NOT_FOUND, media_type="text/plain")

	digest = sha256(logs).hexdigest()
	return Response(logs, status_code=status.HTTP_200_OK, headers={"ETag": digest, "Content-Length": str(len(logs))},
	                media_type="text/plain")


@router.api_route("/results/{result_id}/publicize", methods=["POST", "HEAD"], tags=["Using EXSCLAIM"])
async def publicize_result(result_id: UUID, user: ActiveUser, publicize: bool = Body(...)):
	async with get_db_session() as session:
		results = await session.execute(select(Results).where(Results.id == result_id))
		results: Optional[Results] = results.scalar_one_or_none()

		if results is None or results.user_id != user.id:
			return Response(f"There is no query recorded in our database with id: {result_id}.",
							status_code=status.HTTP_404_NOT_FOUND, media_type="text/plain")

		if results.user_id == get_guest_uuid():
			return Response("Publicization status for queries run by guests cannot be changed.",
							status_code=status.HTTP_403_FORBIDDEN, media_type="text/plain")

		if publicize == results.publicize_results:
			return Response(f"Publicization status for {result_id} is already {publicize}.",
							status_code=status.HTTP_202_ACCEPTED, media_type="text/plain")

		await session.execute(update(Results).where(Results.id == result_id).values(publicize_results=publicize))
	return Response("Publicization status updated.", status_code=status.HTTP_200_OK, media_type="text/plain")


@router.api_route("/compression_types", methods=["GET", "HEAD"], tags=["Using EXSCLAIM"], responses={
	200: {
		"description": "Possible Compression Algorithms/Extensions",
		"content": {
			"application/json": {
				"schema": {
					"type": "object",
					"properties": {
						"compression_types": {
							"type": "object"
						}
					}
				},
				"example": {
					"compression_types": ["tar", "gztar", "zip", "bztar", "xztar"],
				}
			},
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": '["tar","gztar","zip","bztar","xztar"]'
			}
		}
	},
	202: {
		"description": "The given compression type is allowed.",
		"content": {
			"application/json": {
				"schema": {
					"type": "object",
					"properties": {
						"allowed": {
							"type": "boolean"
						}
					}
				},
				"example": {
					"allowed": True,
				}
			},
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": "zip is an allowed value."
			}
		}
	},
	404: {
		"description": "The given compression type is not allowed.",
		"content": {
			"application/json": {
				"schema": {
					"type": "object",
					"properties": {
						"allowed": {
							"type": "boolean"
						}
					}
				},
				"example": {
					"allowed": False,
				}
			},
			"text/plain": {
				"schema": {
					"type": "string",
				},
				"example": "zip is NOT an allowed value."
			}
		}
	}
		 })
async def get_possible_compressions(request: Request, compression_type: Optional[str] = None) -> Response:
	send_json = request.headers.get("accept", "") == "application/json"
	compression_types = frozenset(map(lambda i: i[0], get_archive_formats()))

	if compression_type is None: # TODO: Add E-Tag header for compression types
		compression_types = list(compression_types)
		if send_json:
			return ExsclaimJSONResponse({"compression_types": compression_types}, status_code=status.HTTP_200_OK,
										media_type="application/json")
		return Response(str(compression_types), status_code=status.HTTP_200_OK, media_type="text/plain")

	allowed = compression_type in compression_types
	status_code = status.HTTP_202_ACCEPTED if allowed else status.HTTP_404_NOT_FOUND
	if send_json:
		return ExsclaimJSONResponse({"allowed": allowed}, status_code=status_code, media_type="application/json")

	return Response(f"{compression_type} is {'NOT ' if not allowed else ''}an available compression type.",
					status_code=status_code, media_type="text/plain")


@router.api_route("/classification_codes", methods=["GET", "HEAD"], tags=["Using EXSCLAIM"],
				  response_model=list[ClassificationCodes])
async def classification_codes(response: Response) -> tuple[ClassificationCodes]:
	async with get_db_session() as session:
		results = await session.execute(select(ClassificationCodes).order_by(ClassificationCodes.code))
		results = tuple(results.scalars().all())

	hash_string = ";".join(map(lambda result: result.code, results))

	etag = b64encode(hash_string.encode("utf-8")).decode()
	response.headers["ETag"] = etag
	return results


@router.api_route("/checkpoints/{checkpoint}", methods=["GET", "HEAD"], tags=["EXSCLAIM Model Checkpoints"])
async def download_checkpoint(checkpoint: str) -> Response:
	checkpoint_folder = settings.CHECKPOINTS_PATH

	if not checkpoint_folder.exists() or not checkpoint_folder.is_dir():
		return Response("Could not find any checkpoints. Please try again later.",
						status_code=status.HTTP_503_SERVICE_UNAVAILABLE, media_type="text/plain")

	checkpoint = Path(checkpoint).name # Prevents users from using ../../.. to read in from external directories
	checkpoint_path = checkpoint_folder / checkpoint
	if not checkpoint_path.exists():
		return Response(f"Could not find checkpoint \"{checkpoint}\".", status_code=status.HTTP_404_NOT_FOUND,
						media_type="text/plain")

	return FileResponse(checkpoint_path, media_type="application/octet-stream", status_code=status.HTTP_200_OK,
						stat_result=checkpoint_path.stat())


@router.api_route("/previous_runs", methods=["GET", "HEAD"], tags=["Using EXSCLAIM"])
async def previous_runs(user: CurrentUser, conditions: Annotated[PreviousRunFilters, fastapi.Query()]) -> JSONResponse:
	query = dedent(f"""
		SELECT {conditions.selection} FROM (
			SELECT
				r.id, r.status, r.search_query->>'name' AS name, r.search_query->'query'->'search_field_1'->'term' AS term,
				r.start_time, r.end_time, COALESCE(r.end_time, NOW()) - r.start_time AS run_time,
				(r.search_query->>'maximum_scraped')::INT AS max_articles,
				(SELECT COUNT(*) AS num_articles FROM results.article a WHERE a.run_id = r.id) AS num_articles,
				(SELECT COUNT(*) AS num_figures FROM results.subfigure s WHERE s.run_id = r.id) AS num_figures
			FROM results.results r
			WHERE r.user_id = :user_id
		) r
	""")

	params = dict(user_id=user.id)
	filter_clause = ""

	if conditions is not None:
		filters, params = conditions.add_conditions_to_sql(params)
		if len(filters) > 0:
			filter_clause = f"WHERE {' AND '.join(filters)} "

	async with get_db_session() as session:
		query = f"{query} {filter_clause} ORDER BY r.start_time DESC;"
		# print(f"{query=}\n{params=}", flush=True)
		results = await session.execute(text(query), params=params)
		runs = results.fetchall()

	output = [None] * len(runs)
	return_values = set(conditions.return_values)
	if "*" in return_values:
		keys = ["id", "status", "name", "term", "start_time", "end_time", "run_time", "max_articles", "num_articles", "num_figures"]
	else:
		keys = conditions.return_values

	for i, run in enumerate(runs):
		run = dict(zip(keys, run))
		if "id" in return_values:
			run["id"] = str(run["id"])

		if "run_time" in return_values:
			run["run_time"] = run["run_time"].total_seconds()

		output[i] = run

	return JSONResponse(fastapi.encoders.jsonable_encoder(output), status_code=status.HTTP_200_OK)
