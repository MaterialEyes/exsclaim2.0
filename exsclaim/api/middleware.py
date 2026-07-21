import logging

from .models import get_guest_uuid, gen_uuid7
from .routers.users import get_user_from_session
from ..db import async_engine

from asyncio import wait_for, TimeoutError as AsyncTimeoutError
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette import status
from starlette.types import ASGIApp
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from time import perf_counter
from uuid import UUID


__all__ = ["RequestLoggerMiddleware", "PreflightCacheMiddleware", "SQLAlchemyMiddleware", "UserMiddleware"]


request_id_ctx = ContextVar("request_id")


def format_response(_id, request: Request) -> str:
	ip = request.headers.get('X-Forwarded-For', None)
	if ip is None:
		ip = request.client.host or "Unknown IP"

	path = request.url.path if hasattr(request, "url") else "NULL PATH"
	log = f"[{request_id_ctx.get()}] {{{ip} using {request.headers.get('User-Agent', 'Unknown User-Agent')}}} {path}"
	if request.url.query:
		log += f"?{request.url.query}"

	return log


# https://medium.com/the-pythonworld/15-useful-middlewares-for-fastapi-that-you-should-know-about-8c2d67ea0d86
class RequestLoggerMiddleware(BaseHTTPMiddleware):
	"""Logs each HTTP request made to the server, along with its unique request id and response status code."""
	slots = ("logger",)

	def __init__(self, app: ASGIApp, logger: logging.Logger, dispatch=None):
		super().__init__(app, dispatch)
		self.logger = logger

	@staticmethod
	def get_log_time(diff: float) -> str:
		if diff < 1:
			return f"{diff * 1000:,.4f}ms"
		return f"{diff:,.2f}s"

	async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
		start_time = perf_counter()

		request_id = request.headers.get("X-Request-Id", str(gen_uuid7()))
		request.state.logger = self.logger

		try:
			request_id = str(UUID(request_id))
		except ValueError:
			request_id = str(gen_uuid7())

		request_id_ctx.set(request_id)
		request.state.id = request_id

		try:
			response = await call_next(request)
			response.headers.setdefault("X-Request-Id", request_id)
			response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload") # Max-age is 1 year
			response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
			response.headers.setdefault("X-Content-Type", "nosniff")
			response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
			response.headers.setdefault("X-Xss-Protection", "1; mode=block")

			end_time = perf_counter()
			diff = end_time - start_time

			# Don't care about logging these
			match request.url.path:
				case "/favicon.ico" | "/healthcheck" | "/swagger-dark-ui.css":
					return response

			self.logger.info(f"{format_response(request_id, request)} ({response.status_code}) in {self.get_log_time(diff)}.")

			return response
		except BaseException as e:
			end_time = perf_counter()
			diff = end_time - start_time

			self.logger.exception(f"{format_response(request_id_ctx, request)} Time to error: {self.get_log_time(diff)}. Unhandled error: {e}.")
			return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=f"Internal Server Error. Please try again later. Request ID: {request_id}.",
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
		session: AsyncSession = self.session_factory()
		request.state.session = session
		try:
			response = await call_next(request)
			await session.commit()
		except SQLAlchemyError as e: # TODO: Check if I should use request_id_ctx instead
			response = Response(f"Internal database error detected. Request ID: {request.state.id}.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
								media_type="text/plain", headers={"X-Request-Id": request_id_ctx.get()})
			await session.rollback()
			self.logger.exception(f"{format_response(request_id_ctx.get(), request)} Database Error occurred: {e}.")
		finally:
			await session.close()

		return response


class UserMiddleware(BaseHTTPMiddleware):
	async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
		session_key = request.cookies.get("session_id")
		if session_key is None:
			request.state.user_id = get_guest_uuid()
			return await call_next(request)

		session = await get_user_from_session(request.state.session, session_key)
		match session:
			case None: # Session key is wrong
				response = Response("Session ID is invalid. Please try again.", status_code=status.HTTP_401_UNAUTHORIZED, media_type="text/plain")
				response.delete_cookie("session_id")
				return response
			case False: # Session key is expired
				headers = {
					"Location": "/login",
					"Referer": str(request.url),
				}
				return Response(status_code=status.HTTP_303_SEE_OTHER, headers=headers, media_type="text/plain")
			case _:
				request.state.user_id = session.user
				return await call_next(request)


# TODO: Finish implementing the timeout middleware
class TimeoutMiddleware(BaseHTTPMiddleware):
	def __init__(self, app:ASGIApp, timeout: int = 60, dispatch=None):
		super().__init__(app, dispatch)
		self.timeout = timeout

	async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
		try:
			return await wait_for(call_next(request), self.timeout)
		except AsyncTimeoutError:
			return Response("Timeout waiting for response.", status_code=status.HTTP_503_SERVICE_UNAVAILABLE, media_type="text/plain")
