import logging

from ..db import async_engine

from contextvars import ContextVar
from hashlib import sha256
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from time import perf_counter
from uuid import UUID
from uuid_utils import uuid7


__all__ = ["RequestLoggerMiddleware", "PreflightCacheMiddleware", "SQLAlchemyMiddleware", "HashMiddleware"]


request_id_ctx = ContextVar("request_id")


def format_response(_id, request:Request) -> str:
	log = f"[{request_id_ctx.get()}] {request.url.path}"
	if request.url.query:
		log += f"?{request.url.query}"

	return log


# https://medium.com/the-pythonworld/15-useful-middlewares-for-fastapi-that-you-should-know-about-8c2d67ea0d86
class RequestLoggerMiddleware(BaseHTTPMiddleware):
	"""Logs each HTTP request made to the server, along with its unique request id and response status code."""
	def __init__(self, app: ASGIApp, logger: logging.Logger, dispatch=None):
		super().__init__(app, dispatch)
		self.logger = logger

	@staticmethod
	def get_log_time(diff:float) -> str:
		if diff < 1:
			return f"{diff * 1000:,.4f}ms"
		return f"{diff:,.2f}s"

	async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
		start_time = perf_counter()

		request_id = request.headers.get("X-Request-Id", str(uuid7()))
		request.state.logger = self.logger

		try:
			request_id = str(UUID(request_id))
		except ValueError:
			request_id = str(uuid7())

		request_id_ctx.set(request_id)

		try:
			response = await call_next(request)
			response.headers["X-Request-Id"] = request_id

			end_time = perf_counter()
			diff = end_time - start_time

			# Don't care about logging these
			match request.url.path:
				case "/favicon.ico" | "/healthcheck":
					return response

			self.logger.info(f"{format_response(request_id, request)} ({response.status_code}) in {self.get_log_time(diff)}.")

			return response
		except Exception as e:
			end_time = perf_counter()
			diff = end_time - start_time

			self.logger.exception(f"{format_response(request_id_ctx, request)} Time to error: {self.get_log_time(diff)}. Unhandled error: {e}.")
			return Response(status_code=500, content="Internal Server Error.",
								media_type="text/plain", headers={"X-Request-Id": request_id})
		finally:
			for handler in self.logger.handlers:
				handler.flush()


class PreflightCacheMiddleware(BaseHTTPMiddleware):
	async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
		response = await call_next(request)

		if request.method != "OPTIONS":
			return response

		response.headers["Access-Control-Max-Age"] = "600"
		response.headers["Access-Control-Request-Headers"] = "X-Request-Id"

		# Have the request specify if users want light mode or dark mode
		for header in ("Accept-CH", "Vary", "Critical-CH"):
			if header in response.headers:
				response.headers[header] += ", Sec-Ch-Prefers-Color-Scheme"
			else:
				response.headers[header] = "Sec-Ch-Prefers-Color-Scheme"

		return response


class SQLAlchemyMiddleware(BaseHTTPMiddleware):
	def __init__(self, app:ASGIApp, logger, dispatch=None):
		super().__init__(app, dispatch)
		self.logger = logger
		self.session_factory = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

	async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
		session = self.session_factory()
		request.state.session = session
		try:
			response = await call_next(request)
			await session.commit()
		except SQLAlchemyError as e:
			response = Response("Internal database error detected.", status_code=500, media_type="text/plain",
								headers={"X-Request-Id": request_id_ctx.get()})
			session.rollback()
			self.logger.exception(f"{format_response(request_id_ctx.get(), request)} Database Error occurred: {e}.")
		finally:
			await session.close()

		return response


class HashMiddleware(BaseHTTPMiddleware):
	"""Sends the hash of the content to the user for certain paths."""
	__slots__ = ("hashes",)

	def __init__(self, app:ASGIApp, dispatch=None):
		super().__init__(app, dispatch)
		self.hashes = dict()

	async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
		response = await call_next(request)

		path = request.url.path
		path_with_params = f"{path}?{request.query_params}"

		if response.status_code > 400 or not any((
			# Specify the conditions of the responses that should be hashes
			path.startswith("/checkpoints"),	# Any of the model checkpoint files
			path.startswith("/results")			# Any of the result files
		)):
			return response

		content = [section async for section in response.body_iterator]
		response.body_iterator = iterate_in_threadpool(iter(content))

		digest = self.hashes.get(path_with_params, None)

		if not digest:
			hash_obj = sha256()
			for part in content:
				hash_obj.update(part)
			digest = hash_obj.hexdigest()
			self.hashes[path_with_params] = digest

		response.headers["X-Sha256-Hash"] = digest

		return response
