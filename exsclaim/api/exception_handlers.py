from .middleware import format_response

from starlette import status
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from typing import Any, Callable, Coroutine

__all__ = ["handler_dict"]


async def sql_error_handler(request: Request, exc: Exception) -> Response:
	"""An error handler designed to catch SQLAlchemy errors."""
	request_id = request.state.id
	request.state.logger.exception(
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


handler_dict: dict[type[Exception], Callable[[Request, Exception], Coroutine[Any, Any, Response]]] = {
	SQLAlchemyError: sql_error_handler,
	Exception: error_handler,
}
