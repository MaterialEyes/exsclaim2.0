lazy from exsclaim.config import ui_settings
lazy from exsclaim.db import get_db_session
lazy from exsclaim.api.models import EmailVerification, User
lazy from exsclaim.utilities.email import email_context

lazy from datetime import datetime as dt, timedelta as td, timezone as tz
lazy from email.message import EmailMessage
lazy from fastapi import HTTPException, Request, status
lazy from pathlib import Path
lazy from pydantic import EmailStr
lazy from string import Template
lazy from textwrap import dedent
lazy from typing import Optional
lazy from uuid import UUID

lazy import hashlib
lazy import html
lazy import sqlalchemy as sa
lazy import secrets


__all__ = ["send_verification_email", "verify_email"]

SERVER_KEY = secrets.token_bytes(32)


def get_asset_file(file: str) -> Optional[Path]:
	current_path = Path(__file__).resolve()
	for parent in current_path.parents:
		if parent.name == "exsclaim":
			return parent / "dashboard" / "assets" / "email" / file
	return None


# region Email Verification
async def verify_email(code: str):
	hashed_code = hashlib.sha256(code.encode()).hexdigest()
	exception = HTTPException(status.HTTP_404_NOT_FOUND, detail="Verification code not found.")

	async with get_db_session() as session:
		results = await session.execute(sa.select(EmailVerification).where(EmailVerification.code_hash == hashed_code))
		record: Optional[EmailVerification] = results.scalar_one_or_none()

		if record is None:
			raise exception

		await session.execute(sa.delete(EmailVerification).where(EmailVerification.code_hash == hashed_code))

		if dt.now(tz.utc) > record.expires_at:
			await session.commit()
			raise exception

		await session.execute(sa.update(User).where(User.id == record.user_id).values(email_verified=True))
		await session.commit()


async def create_verification_code(user_id: UUID, valid_minutes: int):
	code = secrets.token_urlsafe(32)
	hashed_code = hashlib.sha256(code.encode()).hexdigest()

	expires_at = dt.now(tz.utc) + td(minutes=valid_minutes)

	async with get_db_session() as session:
		statement = sa.text(
			"INSERT INTO users.email_verification(user_id, code_hash, expires_at) VALUES (:user_id, :code_hash, :expires_at) " +
			"ON CONFLICT (user_id) DO UPDATE SET code_hash = :code_hash, expires_at = :expires_at")
		await session.execute(statement, dict(user_id=user_id, code_hash=hashed_code, expires_at=expires_at))
		await session.commit()

	return code  # Send code through the email, don't store the raw version


async def send_verification_email(email: EmailStr, user_id: UUID):
	valid_minutes = 10
	verification_code = await create_verification_code(user_id, valid_minutes)

	link = f"{ui_settings.PUBLIC_API_URL.domain_with_scheme}/user/validate?code={verification_code}"

	text = Template(dedent("""
		Verify your email address.

		Thanks for signing up. Open the link below to confirm your email address.
		This link expires in $expires minutes.

		$link

		If you didn't create an account, ignore this email.
	"""))

	msg = EmailMessage()
	msg["Subject"] = "Verify your EXSCLAIM account"
	msg["To"] = email

	msg.set_content(text.substitute(link=link, expires=valid_minutes))
	html_template_file = get_asset_file("verification_template.html")
	if html_template_file is not None and html_template_file.exists():
		with open(html_template_file, "r") as f:
			html_template = Template(f.read())
			html_version = html_template.substitute(
				link=link,
				expires=valid_minutes,
				logo_light=f"{ui_settings.DASHBOARD_URL.domain_with_scheme}/assets/ExsclaimLogo.png",
				logo_dark=f"{ui_settings.DASHBOARD_URL.domain_with_scheme}/assets/ExsclaimLogo-Inverted.png"
			)
			msg.add_alternative(html_version, subtype="html")

	with email_context() as (server, account):
		msg["From"] = f"EXSCLAIM <{account}>"
		server.send_message(msg)
# endregion


# region Password Reset
async def create_reset_code(user_id: UUID, valid_minutes: int):
	code = secrets.token_urlsafe(40)
	hashed_code = hashlib.sha256(code.encode()).hexdigest()

	expires_at = dt.now(tz.utc) + td(minutes=valid_minutes)

	async with get_db_session() as session:
		statement = sa.text(
			"INSERT INTO users.password_reset(user_id, code_hash, expires_at) VALUES (:user_id, :code_hash, :expires_at) " +
			"ON CONFLICT (user_id) DO UPDATE SET code_hash = :code_hash, expires_at = :expires_at")
		await session.execute(statement, dict(user_id=user_id, code_hash=hashed_code, expires_at=expires_at))
		await session.commit()

	return code  # Send code through the email, don't store the raw version


async def send_password_reset_email(request: Request, email: EmailStr, user_id: UUID, now: dt):
	valid_minutes = 45
	verification_code = await create_reset_code(user_id, valid_minutes)

	link = f"{ui_settings.PUBLIC_API_URL.domain_with_scheme}/user/reset_password?code={verification_code}"
	details_text = html.escape(f"Request details: {now}, {request.headers['User-Agent']}")

	text = Template(dedent("""
		Reset your password

		We received a request to reset the password for your account.
		Open the link below to choose a new one. It expires in $expires
		and can only be used once.

		$link
		$details_text
		If you didn't request this, you can safely ignore this email. Your password
		won't change unless you use the link above.
	"""))

	msg = EmailMessage()
	msg["Subject"] = "Reset your EXSCLAIM password"
	msg["To"] = email

	msg.set_content(text.substitute(link=link, expires=valid_minutes, details_text=details_text))
	html_template_file = get_asset_file("password_reset.html")
	if html_template_file is not None and html_template_file.exists():
		details_html = html.escape(f"Request details: <time datetime=\"{now.isoformat()}\">{now}<time>, {request.headers['User-Agent']}")
		with open(html_template_file, "r") as f:
			html_template = Template(f.read())
			html_version = html_template.substitute(
				link=link,
				expires=valid_minutes,
				logo_light=f"{ui_settings.DASHBOARD_URL.domain_with_scheme}/assets/ExsclaimLogo.png",
				logo_dark=f"{ui_settings.DASHBOARD_URL.domain_with_scheme}/assets/ExsclaimLogo-Inverted.png",
				details_text=details_html
			)
			msg.add_alternative(html_version, subtype="html")

	with email_context() as (server, account):
		msg["From"] = f"EXSCLAIM <{account}>"
		server.send_message(msg)
# endregion
