from exsclaim.config import settings
from contextlib import contextmanager
from typing import Generator, Optional

lazy from smtplib import SMTP, SMTP_SSL
lazy import ssl


__all__ = ["_EMAIL_AVAILABLE", "email_context"]


_EMAIL_AVAILABLE: bool = settings.EMAIL is not None


@contextmanager
def email_context() -> Generator[Optional[tuple[SMTP, str]], None, None]:
	if not _EMAIL_AVAILABLE:
		yield None
		return

	email_settings = settings.EMAIL
	if email_settings.SERVER == "localhost":
		server = SMTP(email_settings.SERVER, email_settings.PORT)
	else:
		context = ssl.create_default_context()
		server = SMTP_SSL(email_settings.SERVER, email_settings.PORT, context=context)

	with server:
		server.login(email_settings.ACCOUNT, email_settings.PASSWORD)
		yield server, email_settings.ACCOUNT
