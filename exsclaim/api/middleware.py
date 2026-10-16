from .models import gen_uuid7
from ..db import get_db_session
from ..config import ui_settings

from contextlib import suppress
from contextvars import ContextVar
from starlette import status
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from sqlalchemy import text
from time import perf_counter
from uuid import UUID

import asyncio
import ipaddress
import logging
import re

__all__ = ["RequestLoggerMiddleware", "MetricsMiddleware", "IPBlockerMiddleware"]


request_id_ctx = ContextVar("request_id")
BLOCKED_PATHS = [
	re.compile(r"\.env$", re.IGNORECASE),
	re.compile(r"^/?.git.*", re.IGNORECASE),
	re.compile(r"\.php$", re.IGNORECASE),
]


def path_is_blocked(path: str) -> bool:
	for regex in BLOCKED_PATHS:
		if regex.match(path):
			return True
	return False


def get_ip_address(headers: Headers, default: str) -> ipaddress._BaseAddress:
	address = headers.get("X-Forwarded-For", headers.get("X-Real-IP"))
	return ipaddress.ip_address(address or default)


def get_log_time(diff: float) -> str:
	if diff < 1:
		return f"{diff * 1000:,.4f}ms"
	return f"{diff:,.2f}s"


def format_response(_id, request: Request) -> str:
	ip = get_ip_address(request.headers, request.client.host)
	path = request.url.path if hasattr(request, "url") else "NULL PATH"
	user_agent = request.headers.get("User-Agent", "Unknown User-Agent")
	log = f"[{request_id_ctx.get()}] {{{ip} using {user_agent}}} [{request.method}] {path}"
	if request.url.query:
		log += f"?{request.url.query}"

	return log


def run_middleware(scope: Scope) -> bool:
	return scope["type"] in {"http", "websocket"}


# https://medium.com/the-pythonworld/15-useful-middlewares-for-fastapi-that-you-should-know-about-8c2d67ea0d86
class IPBlockerMiddleware:
	"""This middleware checks the IP of the request to see if it's blocked, and blocks users if they go ..."""
	def __init__(self, app: ASGIApp, logger: logging.Logger):
		self.app = app
		self.logger = logger

	async def block_request(self, scope: Scope, receive: Receive, send: Send, address: ipaddress._BaseAddress,
							immediately_stop_request: bool = True):
		self.logger.warning(f"Banned IP: {address} tried to reach {scope["path"]}. Immediately stopping request: {immediately_stop_request}.")

		headers = [(b"Content-Length", b"0")] if immediately_stop_request else []
		await send({
			"type": "http.response.start",
			"status": status.HTTP_404_NOT_FOUND,
			"headers": headers
		})

		if immediately_stop_request:
			await send({
				"type": "http.response.body",
				"body": b'',
				"more_body": False
			})
			return

		response = b'0' * 1_024 * 4
		while True:
			with suppress(asyncio.TimeoutError):
				async with asyncio.timeout(1):
					message = await receive()
					if message["type"] == "http.disconnect":
						break

			await send({
				"type": "http.response.body",
				"body": response,
				"more_body": True
			})

	async def __call__(self, scope: Scope, receive: Receive, send: Send):
		if not run_middleware(scope):
			await self.app(scope, receive, send)
			return

		headers = Headers(scope=scope)
		address = get_ip_address(headers, scope.get("client", [None])[0])

		is_banned = False
		async with get_db_session() as session:
			results = await session.execute(
				text("SELECT EXISTS (SELECT 1 FROM settings.banned_ips WHERE address=:address)"),
				dict(address=address)
			)
			is_banned = results.scalar()

		if is_banned:
			await self.block_request(scope, receive, send, address)
			return

		if path_is_blocked(scope["path"]):
			async with get_db_session() as session:
				await session.execute(
					text("INSERT INTO settings.banned_ips(address, reason) VALUES (:address, :reason);"),
					dict(address=address, reason=f"Attempted to access: {scope["path"]}")
				)
				await session.commit()

			await self.block_request(scope, receive, send, address)
			return

		await self.app(scope, receive, send)
		return


class RequestLoggerMiddleware:
	def __init__(self, app: ASGIApp, logger: logging.Logger):
		self.app = app
		self.logger = logger

	async def __call__(self, scope: Scope, receive: Receive, send: Send):
		if not run_middleware(scope):
			await self.app(scope, receive, send)
			return

		headers = Headers(scope=scope)

		# Get the Request ID for logging purposes
		request_id = headers.get("X-Request-Id", str(gen_uuid7()))
		scope["state"]["logger"] = self.logger

		# Make sure that the Request ID is UUIDv7
		try:
			request_id = str(UUID(request_id))
		except ValueError:
			request_id = str(gen_uuid7())

		request_id_ctx.set(request_id)
		scope["state"]["id"] = request_id

		# Handle calling the proper page
		status_code = None

		async def send_wrapper(message: Message):
			if message["type"] == "http.response.start":
				nonlocal status_code
				status_code = message["status"]
				response_headers = MutableHeaders(raw=message["headers"])
				response_headers.setdefault("X-Request-Id", request_id)
				response_headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")  # Max-age is 1 year
				response_headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
				response_headers.setdefault("X-Content-Type", "nosniff")
				response_headers.setdefault("X-Frame-Options", "SAMEORIGIN")
				response_headers.setdefault("X-Xss-Protection", "1; mode=block")
				message["headers"] = response_headers.raw

			await send(message)

		start_time = perf_counter()
		await self.app(scope, receive, send_wrapper)
		end_time = perf_counter()
		diff = end_time - start_time

		# Don't care about logging these
		if scope["path"] in {"/favicon.ico", "/healthcheck", "/swagger-dark-ui.css"}:
			return

		self.logger.info(f"{format_response(request_id, Request(scope=scope))} ({status_code}) in {get_log_time(diff)}.")
		# for handler in self.logger.handlers:
		# 	handler.flush()


class MetricsMiddleware:
	def __init__(self, app: ASGIApp):
		self.app = app
		self.metrics_ip = ui_settings.METRICS_IP
		self.metrics_network = ui_settings.METRICS_NETWORK
		self.disallow_metrics_path = self.metrics_ip is None and self.metrics_network is None

	async def __call__(self, scope: Scope, receive: Receive, send: Send):
		if not run_middleware(scope) or scope["path"] != "/metrics":
			await self.app(scope, receive, send)
			return

		if self.disallow_metrics_path:
			await self.block_request(send)
			return

		headers = Headers(scope=scope)
		address = get_ip_address(headers, scope["client"][0])

		if address == self.metrics_ip or address in self.metrics_network:
			await self.app(scope, receive, send)
			return

		await self.block_request(send)

	@staticmethod
	async def block_request(send: Send):
		await send({
			"type": "http.response.start",
			"status": status.HTTP_404_NOT_FOUND,
			"headers": []
		})

		await send({
			"type": "http.response.body",
			"body": b'',
			"more_body": False
		})
