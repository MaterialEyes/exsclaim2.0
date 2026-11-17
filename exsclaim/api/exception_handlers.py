lazy from .middleware import format_response

lazy from fastapi.exceptions import RequestValidationError
lazy from starlette import status
lazy from starlette.requests import Request
lazy from starlette.responses import Response, JSONResponse
lazy from sqlalchemy.exc import SQLAlchemyError
lazy from typing import Any, Callable, Coroutine

__all__ = ["handler_dict"]


async def sql_error_handler(request: Request, exc: SQLAlchemyError) -> Response:
	"""An error handler designed to catch SQLAlchemy errors."""
	request_id = request.state.id
	logger = request.state.logger

	logger.exception(
		f"{format_response(request_id, request)} Database Error occurred.",
		exc_info=exc
	)
	return JSONResponse(
		dict(detail="Internal Database Error.", request_id=request_id),
		status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
		headers={"X-Request-Id": request_id}
	)


async def error_handler(request: Request, exc: Exception) -> Response:
	"""An error handler designed to catch general Exceptions."""
	request_id = request.state.id

	request.state.logger.exception(
		f"{format_response(request_id, request)}. Unhandled error.",
		exc_info=exc
	)
	return JSONResponse(
		dict(detail="Internal Server Error.", request_id=request_id),
		status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
		headers={"X-Request-Id": request_id}
	)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
	request_id = request.state.id
	logger = request.state.logger

	logger.exception(
		f"{format_response(request_id, request)} sent unprocessable data that FastAPI automatically blocked.",
		exc_info=exc
	)
	return JSONResponse(
		dict(detail="Unprocessable Content.", request_id=request_id, args=list(exc.args)),
		status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
		headers={"X-Request-Id": request_id}
	)


handler_dict: dict[type[Exception], Callable[[Request, Exception], Coroutine[Any, Any, Response]]] = {
	SQLAlchemyError: sql_error_handler,
	RequestValidationError: validation_exception_handler,
	Exception: error_handler,
}
