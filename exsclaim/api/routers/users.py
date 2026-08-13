from ...config import ui_settings, orcid_settings
from ...db import get_db_session
from ..models import User, PasswordReset, Results, cryptographic_hash, generate_salt, get_guest_uuid, \
	ExsclaimJSONResponse as JSONResponse

from datetime import datetime as dt, timezone as tz, timedelta as td
from fastapi import APIRouter, Form, status, Depends, HTTPException, Body, Cookie
from fastapi.security import OAuth2PasswordBearer, APIKeyCookie
from httpx import AsyncClient
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse, RedirectResponse, PlainTextResponse
from pydantic import EmailStr, BaseModel
from sqlalchemy import text, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import Annotated, Optional
from uuid import uuid4, UUID

import asyncpg
import jwt
import re
import sqlalchemy.exc as sql_exc

__all__ = ["router", "CurrentUser", "ActiveUser"]


router = APIRouter(prefix="/user")
TAG = "User Management"


class LoginInfo(BaseModel):
	username: Optional[str] = None
	email: EmailStr
	password: str


ALGORITHM = "RS256"

if (ui_settings.JWT_PUBLIC_KEY_FILE is not None) and (ui_settings.JWT_PRIVATE_KEY_FILE is not None):
	with open(ui_settings.JWT_PRIVATE_KEY_FILE, 'rb') as f:
		PRIVATE_KEY = f.read()

	with open(ui_settings.JWT_PUBLIC_KEY_FILE, 'rb') as f:
		PUBLIC_KEY = f.read()
else:
	from cryptography.hazmat.primitives.asymmetric import rsa
	from logging import getLogger
	getLogger("exsclaim.api").warning(f"Could not load secrets for JWT from private={ui_settings.JWT_PRIVATE_KEY_FILE} and public={ui_settings.JWT_PUBLIC_KEY_FILE}, so temporary secrets are being generated instead.")
	PRIVATE_KEY = rsa.generate_private_key(public_exponent=65_537, key_size=4_096)
	PUBLIC_KEY = PRIVATE_KEY.public_key()


ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

DOMAIN_REGEX = re.compile("https?://")


def get_cookie_domain() -> str:
	return DOMAIN_REGEX.sub("", ui_settings.DOMAIN)


def get_api_cookie_domain() -> str:
	return DOMAIN_REGEX.sub("", ui_settings.PUBLIC_API_URL)


async def get_guest_user() -> User:
	async with get_db_session() as session:
		results = await session.execute(select(User).where(User.id == get_guest_uuid()))
		return results.scalar()
	raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not find guest user.")


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


async def _extract_access_token(token: Optional[str]) -> User | HTTPException:
	if token is None:
		return None

	try:
		payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
	except jwt.InvalidTokenError as e:
		return HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail=f"Could not validate credentials: {e}",
			headers={"WWW-Authenticate": "Bearer"},
		)
	except jwt.ExpiredSignatureError as e:
		return HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail=f"Credentials are expired.",
			headers={"WWW-Authenticate": "Bearer"},
		)

	user_id = payload.get("sub")
	if user_id is None:
		return HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Cannot refresh credentials when no credentials are given.",
			headers={"WWW-Authenticate": "Bearer"},
		)

	user_id = UUID(user_id)
	async with get_db_session() as session:
		user = await session.execute(select(User).where(User.id == user_id))
		user = user.scalar()

	return user


bearer_regex = re.compile("Bearer (.+)")


async def get_current_user_from_authorization_header(request: Request) -> User:
	auth = request.headers.get("Authorization", "")
	match = bearer_regex.search(auth)
	if match is None:
		return await get_guest_user()

	user = await _extract_access_token(match.group(1))
	if isinstance(user, User):
		return user

	return await get_guest_user()


async def get_current_user_from_cookie(request: Request) -> User:
	cookie = request.cookies.get("access_token")

	if cookie is None:
		return await get_guest_user()

	user = await _extract_access_token(cookie)
	if isinstance(user, User):
		return user

	return await get_guest_user()


AccessTokenHeader = Annotated[Optional[str], Depends(OAuth2PasswordBearer(tokenUrl="token"))]
AccessTokenCookie = Annotated[str, Depends(APIKeyCookie(name="access_token", auto_error=False))]


async def get_active_user_from_authorization_header(token: AccessTokenHeader) -> User:
	user = await _extract_access_token(token)
	if isinstance(user, HTTPException):
		raise user

	elif user is None:
		raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Credentials were not given.",
		                    headers={"WWW-Authenticate": "Bearer"},)

	return user


async def get_active_user_from_cookie(request: Request, cookie: AccessTokenCookie) -> User:
	user = await _extract_access_token(cookie)
	if isinstance(user, HTTPException):
		raise user

	elif user is None:
		raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials",
		                    headers={"WWW-Cookie": "Bearer"},)

	return user


CurrentUser = Annotated[User, Depends(get_current_user_from_cookie)]
ActiveUser = Annotated[User, Depends(get_active_user_from_cookie)]


async def add_user_jti(user: User, jti: UUID):
	async with get_db_session() as session:
		await session.execute(text("INSERT INTO users.jtis VALUES(:user_id, :jti)"), dict(user_id=user.id, jti=jti))
		await session.commit()


async def remove_user_jti(user: User, jti: UUID):
	async with get_db_session() as session:
		await session.execute(text("DELETE FROM users.jtis WHERE id = :user_id AND jti = :jti"), dict(user_id=user.id, jti=jti))
		await session.commit()

	del user.jti


async def user_has_jti(user: User, jti: UUID) -> bool:
	async with get_db_session() as session:
		results = await session.execute(text("SELECT EXISTS (SELECT 1 FROM users.jtis WHERE id = :user_id AND jti = :jti)"), dict(user_id=user.id, jti=jti))
		return results.scalar()


async def create_tokens_for_authorization_header(user: User) -> dict[str, str]:
	new_jti = uuid4()
	await add_user_jti(user, new_jti)

	access_token = create_access_token(user)
	refresh_token = create_refresh_token(user, new_jti)

	return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


async def create_access_token_for_cookie(user: User, response: Response) -> Response:
	access_token = create_access_token(user)

	response.set_cookie(
		key="access_token",
		value=access_token,
		httponly=True,
		secure=True,
		domain=get_cookie_domain(),
		samesite="lax",
		max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
		path="/"
	)

	response.headers["X-EXSCLAIM-Access-Minutes"] = str(ACCESS_TOKEN_EXPIRE_MINUTES)
	return response


async def create_refresh_token_for_cookie(user: User, response: Response, include_refresh: bool = True) -> Response:
	new_jti = uuid4()
	await add_user_jti(user, new_jti)
	refresh_token = create_refresh_token(user, new_jti)

	response.set_cookie(
		key="refresh_token",
		value=refresh_token,
		httponly=True,
		secure=True,
		domain=get_api_cookie_domain(),
		samesite="strict",
		max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86_400, # 86,400 seconds in a day
		path=router.prefix + "/refresh"
	)

	response.headers["X-EXSCLAIM-Refresh-Days"] = str(REFRESH_TOKEN_EXPIRE_DAYS)
	return response


def is_valid_username(username: str) -> bool:
	# TODO: Check for profanity before allowing the username
	return True


@router.post("/create_user", tags=[TAG])
async def create_user(request: Request, info: LoginInfo):
	session: AsyncSession = request.state.session

	email = info.email.strip().lower()
	username = info.username.strip()
	password = info.password.strip()

	results = await session.execute(select(User).where(User.email == email))
	existing_user: Optional[User] = results.scalar_one_or_none()
	if existing_user:
		return Response("Account with email already exists.", status_code=status.HTTP_409_CONFLICT, media_type="text/plain")

	if not is_valid_username(username):
		return JSONResponse({"detail": "Username not valid.", "requested_username": username}, status_code=status.HTTP_400_BAD_REQUEST)

	salt = User.generate_salt()
	password_hash = cryptographic_hash(password, salt=salt)

	user = User(name=username, email=email, salt=salt, password_hash=password_hash)

	session.add(user)
	await session.commit()

	response = JSONResponse({"detail": f"Account created for {email}."}, status_code=status.HTTP_201_CREATED)
	response = await create_access_token_for_cookie(user, response)
	response = await create_refresh_token_for_cookie(user, response)
	return response


async def get_user_from_login(info: LoginInfo) -> User | Response:
	email = info.email.strip().lower()
	password = info.password.strip()

	async with get_db_session() as session:
		results = await session.execute(select(User).where(User.email == email))
		actual_user: Optional[User] = results.scalar_one_or_none()

	if not actual_user:
		return Response(content="Invalid email/password.", status_code=status.HTTP_401_UNAUTHORIZED, media_type="text/plain")

	if not actual_user.verify_password(password):
		return Response(content="Invalid email/password.", status_code=status.HTTP_401_UNAUTHORIZED, media_type="text/plain")

	return actual_user


@router.post("/login", tags=[TAG])
async def login_user(request: Request, info: LoginInfo) -> Response:
	actual_user = await get_user_from_login(info)
	if isinstance(actual_user, Response):
		return actual_user

	referer = request.headers.get("Referer")
	response = JSONResponse({"status": "Logged in successfully!"}, status_code=status.HTTP_200_OK)

	if referer is not None:
		response.headers["Location"] = referer

	response = await create_access_token_for_cookie(actual_user, response)
	response = await create_refresh_token_for_cookie(actual_user, response)
	return response


@router.api_route("/login-orcid", methods=["GET", "HEAD"], tags=[TAG], include_in_schema=False)
async def login_with_orcid(request: Request, code: str): # TODO: Create a way for users to merge there email account with their ORCID
	logger = request.state.logger
	async with AsyncClient() as client:
		headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
		data = {
			"client_id": orcid_settings.CLIENT_ID,
			"client_secret": orcid_settings.CLIENT_SECRET,
			"grant_type": "authorization_code",
			"code": code,
			"redirect_uri": f"{ui_settings.PUBLIC_API_URL}/user/login-orcid"
		}

		response = await client.post(f"{orcid_settings.URL}/oauth/token", headers=headers, data=data)

		if response.status_code != 200:
			logger.error(f"Login failed with status code {response.status_code}: {response.text}")
			return JSONResponse({**response.json(), "status_code": response.status_code}, status_code=500)

		json = response.json()

	session: AsyncSession = request.state.session
	results = await session.execute(select(User).where(User.orcid == json["orcid"]))
	actual_user: Optional[User] = results.scalar_one_or_none()
	if actual_user is None:
		# Create user
		actual_user = User(name=json["name"], orcid=json["orcid"])
		session.add(actual_user)
		await session.commit()

	response = RedirectResponse(ui_settings.DASHBOARD_URL)
	response = await create_access_token_for_cookie(actual_user, response)
	response = await create_refresh_token_for_cookie(actual_user, response)
	return response


@router.post("/refresh", tags=[TAG])
async def refresh(request: Request, refresh_token: str = Cookie()):
	try:
		payload = jwt.decode(refresh_token, PUBLIC_KEY, algorithms=[ALGORITHM])
	except jwt.ExpiredSignatureError:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is expired.")
	except jwt.InvalidTokenError:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

	if payload.get("type") != "refresh":
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token.")

	user_id = payload.get("sub")
	if user_id is None:
		return HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Cannot refresh credentials when no credentials are given.",
			headers={"WWW-Authenticate": "Bearer"},
		)

	user_id = UUID(user_id)
	async with get_db_session() as session:
		user = await session.execute(select(User).where(User.id == user_id))
		user = user.scalar()

	if user is None:
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User not found.")

	if not await user_has_jti(user, payload["jti"]):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"JTI does not match: {payload['jti']}.")

	response = JSONResponse({"status": "New access token provided."}, status_code=status.HTTP_202_ACCEPTED)
	response = await create_access_token_for_cookie(user, response)
	return response


@router.api_route("/logout", methods=["GET", "HEAD"], tags=[TAG])
async def logout_user(request: Request, user: ActiveUser) -> Response:
	await remove_user_jti(user, user.jti)

	headers = {"Location": referer} if (referer := request.headers.get("Referer")) else dict()
	response = Response("User logged out successfully.", status_code=status.HTTP_200_OK, media_type="text/plain",
						headers=headers)
	response.delete_cookie(key="access_token", domain=get_cookie_domain())
	response.delete_cookie(key="refresh_token", domain=get_api_cookie_domain())
	return response


@router.post("/logout_all", tags=[TAG])
async def logout_all_instances(request: Request, user: ActiveUser) -> Response:
	async with get_db_session() as session:
		await session.execute(text("DELETE FROM users.jtis WHERE id = :user_id"), dict(user_id=user.id))
		await session.commit()

	del user.id
	response = JSONResponse(dict(detail=
							 f"All logged in versions of this user can no longer create new access tokens, so they will be logged out within the next {ACCESS_TOKEN_EXPIRE_MINUTES} minutes."),
						status_code=status.HTTP_200_OK)
	response.delete_cookie(key="refresh_token", domain=get_api_cookie_domain())
	return response


async def send_reset_request_email(request: Request, session: AsyncSession, email: EmailStr) -> Response:
	token = ... # TODO: Generate the token for resetting passwords
	reset_obj = PasswordReset(email=email, token=token)
	session.add(reset_obj)
	await session.commit()
	reset_link: str = request.url_for("reset_password", token=reset_obj.token, email=email) # TODO: Test if this generates the correct link

	subject = "Password Reset | EXSCLAIM" # TODO: Make the reset email look prettier when there's a chance
	email_content = ("<!DOCTYPE html>"
					 "<html lang=\"en\">"
					 "<head>"
					 "<title>EXSCLAIM Password Reset</title>"
					 "</head>"
					 "<body>"
					 "<h3>Password Reset</h3>"
					 "<p>Hi,</p>"
					 "<p>We got a request to reset your EXSCLAIM password.</p>"
					 f"<a href=\"{reset_link}\"><button>Reset password</button></a>"
					 "<p>If you did not request a password reset, please ignore this email.</p>"
					 "<p><small>If the button above does not appear, please use the link below in your browser's address bar:</small></p>"
					 f"<p><small><a href=\"{reset_link}\">{reset_link}</a></small></p>"
					 "This link will expire after 1 hour."
					 "</body>"
					 "</html>")

	# TODO: Send the email

	return Response(f"Unfortunately, we do not have email capabilities set up for this system, so password resets are unavailable at this time.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, media_type="text/plain")


@router.post("/reset_password", tags=[TAG])
async def reset_password(request: Request, token: str = None, email: EmailStr = None) -> Response:
	if email is None:
		return Response("No email provided.", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, media_type="text/plain")

	db = request.state.session
	email = email.strip().lower()

	if token is None:
		# Email the user a URL to get to the reset page.
		return await send_reset_request_email(request, db, email)

	results = await db.execute(select(PasswordReset).where(PasswordReset.token == token))
	reset_obj: PasswordReset = results.scalar_one_or_none()

	if (reset_obj is None) or (reset_obj.email != email) or (dt.now(tz.utc) - reset_obj.created > td(hours=1)):
		return Response("The email/token pair was invalid.", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, media_type="text/plain")

	return HTMLResponse(f"", status_code=status.HTTP_202_ACCEPTED) # TODO: Create the password reset form, and have a hidden field with some token for security when the form is posted.


@router.get("/name", include_in_schema=False)
async def get_username(request: Request, user: CurrentUser) -> JSONResponse:
	session: AsyncSession = request.state.session

	not_logged_in = {"username": "Not Logged In."}
	if user is None or user.id == get_guest_uuid():
		return JSONResponse(not_logged_in, status_code=status.HTTP_202_ACCEPTED)

	return JSONResponse({"username": user.name}, status_code=status.HTTP_200_OK)


@router.patch("/name", tags=[TAG])
async def update_username(request: Request, user: ActiveUser, username: str = Body(...)) -> JSONResponse:
	if not is_valid_username(username):
		return JSONResponse({"detail": "Username not valid.", "requested_username": username}, status_code=status.HTTP_400_BAD_REQUEST)

	old_username = user.name

	try:
		async with get_db_session() as session:
			await session.execute(update(User).where(User.id == user.id).values(name=username))
			await session.commit()
	except sql_exc.SQLAlchemyError as e:
		await session.rollback()
		request.state.logger.error(f"An error stopped user {user.id} from updating their username to: \"{username}\"", exc_info=e)
		return JSONResponse({
			"detail": "Could not successfully update username.",
			"old_username": old_username,
			"new_username": username,
		}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

	return JSONResponse({
		"detail": "Successfully updated username.",
		"old_username": old_username,
		"new_username": username,
	}, status_code=status.HTTP_200_OK)


@router.api_route("/remaining_access", methods=["GET", "HEAD"], include_in_schema=False)
async def check_access_token_remaining_time(request: Request, token: AccessTokenCookie) -> User:
	if token is None:
		return JSONResponse(dict(detail="Not logged in."), status_code=status.HTTP_400_BAD_REQUEST)

	try:
		payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
	except jwt.InvalidTokenError as e:
		return JSONResponse({"detail": f"Invalid token given: {e}."}, status_code=status.HTTP_401_UNAUTHORIZED)
	except jwt.ExpiredSignatureError as e:
		return JSONResponse({"detail": "Token has already expired."}, status_code=status.HTTP_406_NOT_ACCEPTABLE)

	expiration = payload.get("exp")
	if expiration is None:
		return JSONResponse({"detail": "Expiration is somehow missing from the token."}, status_code=status.HTTP_401_UNAUTHORIZED)

	expiration = dt.fromtimestamp(expiration, tz=tz.utc)
	diff = expiration - dt.now(tz=tz.utc)
	seconds = diff.total_seconds()

	response = {
		"detail": f"Access token remains valid for another {seconds} seconds.",
		"remaining": seconds,
	}
	return JSONResponse(response, status_code=status.HTTP_200_OK)


@router.delete("/remove_user", tags=[TAG])
async def delete_user(request: Request, user: ActiveUser) -> JSONResponse:
	async with get_db_session() as session:
		try:
			await session.execute(delete(User).where(User.id == user.id))
			await session.commit()
		except sql_exc.SQLAlchemyError as e:
			await session.rollback()
			request.state.logger.exception(f"Could not successfully delete user {user.id}.", exc_info=e)
			return JSONResponse({"detail": "An error occurred while trying to delete user."}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

	return JSONResponse(dict(detail="Successfully deleted user from database.", user=user.name, id=str(user.id)),
						status_code=status.HTTP_200_OK)


@router.api_route("/get_jwt_public_key", methods=["GET", "HEAD"], tags=[TAG])
async def get_public_key(request: Request):
	return PlainTextResponse(PUBLIC_KEY, status_code=status.HTTP_200_OK)


@router.post("/merge_accounts", tags=[TAG], description="Merges an ORCID account with an account created using email and password")
async def merge_accounts(request: Request, info: LoginInfo, orcid_user: ActiveUser) -> JSONResponse:
	if orcid_user.orcid is None:
		return JSONResponse({"detail": "You must be logged in as your ORCID account, not your account with your email and password."}, status_code=status.HTTP_409_CONFLICT)

	email_user = await get_user_from_login(info)
	if isinstance(email_user, Response):
		return email_user

	if email_user.id == orcid_user.id:
		return JSONResponse(dict(detail=f"User with email {email_user.email} and ORCID {orcid_user.orcid} are the same account, so they can't be merged."), status_code=status.HTTP_400_BAD_REQUEST)

	older_created_at = orcid_user.created if orcid_user.created < email_user.created else email_user.created
	email_params = dict(email_user=email_user.id)
	try:
		async with get_db_session() as session:
			# Move the owner ID for all runs from the orcid account where it was originally the email account
			response = await session.execute(text("UPDATE results.results SET user_id = :orcid_user WHERE user_id = :email_user"),
								  dict(orcid_user=orcid_user.id, email_user=email_user.id))

			# Delete any JTIs for the email account
			response = await session.execute(text("DELETE FROM users.jtis WHERE id = :email_user"), email_params)

			# Move all of the information from the email user to the orcid user, keeping the creation timestamp as whichever account was created first
			response = await session.execute(text("""UPDATE users.users
										  SET
											  salt=:salt,
											  password_hash=:password_hash,
											  created=:created
										  WHERE id = :orcid_user"""),
								  dict(
									  salt=email_user.salt,
									  password_hash=email_user.password_hash,
									  created=older_created_at,
									  orcid_user=orcid_user.id,
								  ))

			# Delete the email account
			response = await session.execute(text("DELETE FROM users.users WHERE id = :email_user"), email_params)

			# Add the email to the ORCID account (Couldn't do this before because emails have to be unique)
			response = await session.execute(text("""UPDATE users.users SET email=:email WHERE id = :orcid_user"""),
					  dict(
						  email=email_user.email,
						  orcid_user=orcid_user.id,
					  ))

			await session.commit()
	except (sql_exc.SQLAlchemyError, asyncpg.exceptions.PostgresError) as e:
		await session.rollback()
		request.state.logger.exception(f"Could not merge users ({email_user.email}) [{email_user.id}] with ORCID ({orcid_user.orcid}) [{orcid_user.id}]", exc_info=e)
		return JSONResponse(dict(detail="A database error occurred that stopped the accounts from merging. Please try again later."),
							status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

	return JSONResponse(dict(
		detail=f"Merged account with email {email_user.email} and ORCID {orcid_user.orcid}.",
		orcid_user_id=str(orcid_user.id),
		email_user_id=str(email_user.id),
		new_id=str(orcid_user.id)
	), status_code=status.HTTP_200_OK)
