from ...config import ui_settings
from ...db import get_db_session
from ..models import User, get_guest_uuid

from datetime import datetime as dt, timezone as tz, timedelta as td
from fastapi import status, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, APIKeyCookie
from starlette.requests import Request
from pydantic import EmailStr, BaseModel
from sqlalchemy import select
from sqlalchemy.orm import load_only
from typing import Annotated, Optional
from uuid import UUID

import jwt
import re

__all__ = ["LoginInfo", "ACCESS_TOKEN_EXPIRE_MINUTES", "REFRESH_TOKEN_EXPIRE_DAYS", "ActiveUser", "CurrentUser",
		   "CurrentUserId", "ActiveUserId", "get_guest_user", "create_access_token", "create_refresh_token",
		   "extract_refresh_token", "extract_access_token", "AccessTokenCookie", "RefreshTokenCookie"]


class LoginInfo(BaseModel):
	username: Optional[str] = None
	email: EmailStr
	password: str


ALGORITHM = "RS256"

if (ui_settings.JWT_PUBLIC_KEY_FILE is not None) and (ui_settings.JWT_PRIVATE_KEY_FILE is not None):
	with open(ui_settings.JWT_PRIVATE_KEY_FILE, 'rb') as f:
		PRIVATE_KEY = f.read().strip()

	with open(ui_settings.JWT_PUBLIC_KEY_FILE, 'rb') as f:
		PUBLIC_KEY = f.read().strip()
else:
	from cryptography.hazmat.primitives.asymmetric import rsa
	from logging import getLogger
	getLogger("exsclaim.api").warning(
		f"Could not load secrets for JWT from private={ui_settings.JWT_PRIVATE_KEY_FILE} and public={ui_settings.JWT_PUBLIC_KEY_FILE}, so temporary secrets are being generated instead.")
	PRIVATE_KEY = rsa.generate_private_key(public_exponent=65_537, key_size=4_096)
	PUBLIC_KEY = PRIVATE_KEY.public_key()


ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


async def get_guest_user() -> User:
	async with get_db_session() as session:
		results = await session.execute(select(User).where(User.id == get_guest_uuid()))
		user = results.scalar_one_or_none()
		if user is None:
			raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not find guest user.")
		return user


def create_access_token(user: User) -> str:
	now = dt.now(tz=tz.utc)

	payload = {
		"sub": str(user.id),
		"type": "access",
		"iat": now,
		"exp": now + td(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
	}

	encoded_jwt = jwt.encode(payload, PRIVATE_KEY, algorithm=ALGORITHM)
	return encoded_jwt


def create_refresh_token(user: User, jti: UUID):
	now = dt.now(tz=tz.utc)

	payload = {
		"sub": str(user.id),
		"type": "refresh",
		"iat": now,
		"exp": now + td(days=REFRESH_TOKEN_EXPIRE_DAYS),
		"jti": str(jti)
	}

	encoded_jwt = jwt.encode(payload, PRIVATE_KEY, algorithm=ALGORITHM)
	return encoded_jwt


def extract_access_token(token: Optional[str]) -> Optional[dict]:
	if token is None:
		return None

	try:
		payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
	except jwt.ExpiredSignatureError:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Credentials are expired.",
			headers={"WWW-Authenticate": "Bearer"},
		)
	except jwt.InvalidTokenError as e:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail=f"Could not validate credentials: {e}",
			headers={"WWW-Authenticate": "Bearer"},
		)
	return payload


def extract_user_id_from_access_token(token: Optional[str]) -> Optional[UUID]:
	payload = extract_access_token(token)
	if payload is None:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Cannot refresh credentials when no credentials are given.",
		)

	user_id = payload.get("sub")
	if user_id is None:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Cannot refresh credentials when no credentials are given.",
		)

	return UUID(user_id)


def extract_refresh_token(refresh_token: str) -> dict:
	try:
		payload = jwt.decode(refresh_token, PUBLIC_KEY, algorithms=[ALGORITHM])
	except jwt.ExpiredSignatureError:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is expired.")
	except jwt.InvalidTokenError:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

	if payload.get("type") != "refresh":
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token.")

	return payload


async def _get_user_from_id(user_id: UUID) -> User:
	async with get_db_session() as session:
		statement = select(User).options(load_only(User.id, User.name, User.email, User.orcid, User.created)).where(User.id == user_id)
		user = await session.execute(statement)
		user = user.scalar_one_or_none()

		if user is None:
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="The user credentials were valid, but a user with this information could not be found in the database.",
			)

	return user


bearer_regex = re.compile("Bearer (.+)")


async def get_current_user_from_authorization_header(request: Request) -> UUID:
	auth = request.headers.get("Authorization", "")
	match = bearer_regex.search(auth)
	if match is None:
		return get_guest_uuid()

	user = extract_user_id_from_access_token(match.group(1))
	if isinstance(user, UUID):
		return user

	return get_guest_uuid()


async def get_current_user_id_from_cookie(request: Request) -> UUID:
	cookie = request.cookies.get("access_token")

	if cookie is None:
		return get_guest_uuid()

	user_id = extract_user_id_from_access_token(cookie)
	if isinstance(user_id, UUID):
		return user_id

	return get_guest_uuid()


async def get_current_user_from_cookie(request: Request) -> User:
	user_id = await get_current_user_id_from_cookie(request)
	user = await _get_user_from_id(user_id)
	if isinstance(user, User):
		return user


AccessTokenHeader = Annotated[Optional[str], Depends(OAuth2PasswordBearer(tokenUrl="token"))]
AccessTokenCookie = Annotated[str, Depends(APIKeyCookie(name="access_token", auto_error=False))]
RefreshTokenCookie = Annotated[str, Depends(APIKeyCookie(name="refresh_token", auto_error=False))]


async def get_active_user_from_authorization_header(token: AccessTokenHeader) -> UUID:
	user = extract_user_id_from_access_token(token)

	if user is None:
		raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Credentials were not given.",
							headers={"WWW-Authenticate": "Bearer"})

	return user


async def get_active_user_id_from_cookie(cookie: AccessTokenCookie) -> UUID:
	user_id = extract_user_id_from_access_token(cookie)

	if user_id is None:
		raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.",
							headers={"WWW-Cookie": "Bearer"})

	return user_id


async def get_active_user_from_cookie(cookie: AccessTokenCookie) -> User:
	user_id = await get_active_user_id_from_cookie(cookie)
	return await _get_user_from_id(user_id)


CurrentUserId = Annotated[UUID, Depends(get_current_user_id_from_cookie)]
CurrentUser = Annotated[User, Depends(get_current_user_from_cookie)]
ActiveUserId = Annotated[UUID, Depends(get_active_user_id_from_cookie)]
ActiveUser = Annotated[User, Depends(get_active_user_from_cookie)]
