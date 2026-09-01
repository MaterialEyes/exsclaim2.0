from .models import gen_uuid7
from ..db import get_db_session

from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette import status
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse, JSONResponse
from starlette.types import ASGIApp
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from time import perf_counter
from typing import AsyncGenerator
from uuid import UUID

import ipaddress
import logging
import re

__all__ = ["RequestLoggerMiddleware", "PreflightCacheMiddleware"]


request_id_ctx = ContextVar("request_id")
BLOCKED_PATHS = [
	re.compile(r"\.env$", re.IGNORECASE),
	re.compile(r"^/?.git.*", re.IGNORECASE),
	re.compile(r"\.php$", re.IGNORECASE),
]


def format_response(_id, request: Request, ip: Optional[ipaddress._BaseAddress] = None) -> str:
	if ip is None:
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

	@staticmethod
	def path_is_blocked(url: "starlette.datastructures.URL") -> bool:
		# TODO: Create a more comprehensive set of banned endpoints
		for regex in BLOCKED_PATHS:
			if regex.match(url.path):
				return True
		return False

	def block_request(self, address: ipaddress._BaseAddress, request: Request, immediately_stop_request: bool = True):
		self.logger.warning(f"Banned IP: {address} tried to reach {request.url.path}. Immediately stopping request: {immediately_stop_request}.")

		if immediately_stop_request:
			return Response(status_code=status.HTTP_404_NOT_FOUND)
		else:
			async def send_infinite_zeroes() -> AsyncGenerator[bytes, None]:
				while not await request.is_disconnected():
					yield b"000"

			return StreamingResponse(send_infinite_zeroes(), status_code=404)

	async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
		start_time = perf_counter()

		try:
			address = ipaddress.ip_address(request.headers.get('X-Forwarded-For', request.client.host))
		except ValueError as e:
			self.logger.error(f"Could not extract an IP address for {request.client.host}, so the attempt was blocked.", exc_info=e)
			return Response(status_code=status.HTTP_404_NOT_FOUND)

		is_banned = False
		async with get_db_session() as session:
			results = await session.execute(text("SELECT EXISTS (SELECT 1 FROM settings.banned_ips WHERE address=:address)"),
			                             dict(address=address))
			is_banned = results.scalar()

		if is_banned:
			return self.block_request(address, request)

		if self.path_is_blocked(request.url):
			async with get_db_session() as session:
				await session.execute(
					text("INSERT INTO settings.banned_ips(address, reason) VALUES (:address, :reason);"),
					dict(address=address, reason=f"Attempted to access: {request.url.path}")
				)
				await session.commit()

			return self.block_request(address, request)

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

			self.logger.info(f"{format_response(request_id, request, address)} ({response.status_code}) in {self.get_log_time(diff)}.")
			return response
		except SQLAlchemyError as e:
			self.logger.exception(f"{format_response(request_id_ctx.get(), request)} Database Error occurred.", exc_info=e)
			return JSONResponse(dict(detail="Internal Database Error.", request_id=request.state.id),
									status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
									media_type="text/plain", headers={"X-Request-Id": request_id_ctx.get()})
		except BaseException as e:
			end_time = perf_counter()
			diff = end_time - start_time

			self.logger.exception(f"{format_response(request_id_ctx.get(), request, address)} Time to error: {self.get_log_time(diff)}. Unhandled error: {e}.")
			return JSONResponse(dict(detail="Internal Server Error.", request_id=request.state.id),
								status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
