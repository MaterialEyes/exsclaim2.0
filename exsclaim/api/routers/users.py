from ...config import ui_settings, orcid_settings
from ..models import User, Sessions, PasswordReset, Results, cryptographic_hash, generate_salt, get_guest_uuid
from datetime import datetime as dt, timezone as tz, timedelta as td
from fastapi import APIRouter, Form, status
from fastapi.responses import ORJSONResponse
from httpx import AsyncClient
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, text
from typing import Annotated, Optional
from uuid import uuid5, UUID

__all__ = ["router", "get_user_from_session"]

router = APIRouter()
TAG = "User Management"


async def get_user_from_session(session: AsyncSession, session_key: str | bytes) -> Optional[Sessions | bool]:
	"""
	Gets the user attached to a session key.
	:param sqlalchemy.ext.asyncio.AsyncSession session: The database session being used to query the database.
	:param str | bytes session_key: The session key that was sent from the user's cookie.
	:returns: exsclaim.api.models.Sessions object if the cookie was found, False if the cookie has expired, None if no cookie was found in the database matching what was sent.
	"""
	results = await session.execute(select(Sessions).where(Sessions.key == session_key))
	session_obj = results.scalar_one_or_none()

	if not session_obj:
		return None

	session_obj: Sessions = session_obj

	if (expiration := session_obj.expiration) is not None:
		if dt.now(tz.utc) >= expiration:
			await session.delete(session_obj)
			await session.commit()
			return False

	return session_obj


def get_cookie_domain(request: Request) -> str:
	"""
	Gets the domain that the cookies should serve on. Assuming that the API is on the api. subdomain of the UI, this will remove it allowing the cookie to be used with the API.
	:param starlette.requests.Request request: The request object to get the domain from.
	:returns: The domain name that the cookies should serve.
	:rtype: str
	"""
	return request.url.hostname.replace("api.", "")


async def create_cookie(request: Request, response: Response, db_session: AsyncSession, user: User) -> Response:
	"""

	Args:
		request:
		response:
		db_session:
		user:

	Returns:

	"""
	salt = generate_salt(32)
	name = cryptographic_hash(str(user.id), salt=salt)
	session_id = uuid5(get_guest_uuid(), name)

	session_id_str = str(session_id)
	session = Sessions(user=user.id, key=session_id_str, salt=salt)

	db_session.add(session)
	await db_session.commit()
	response.set_cookie(
		key="session_id",
		value=session_id_str,
		# httponly=True,
		domain=get_cookie_domain(request),
		secure=True,
		samesite="strict",
		expires=session.expiration,
	)
	return response


@router.post("/create_user", tags=[TAG])
async def create_user(request: Request, username: Annotated[str, Form()], email: Annotated[EmailStr, Form()], password: Annotated[str, Form()]):
	session: AsyncSession = request.state.session

	email = email.strip().lower()
	results = await session.execute(select(User).where(User.email == email))
	existing_user: Optional[User] = results.scalar_one_or_none()
	if existing_user:
		return Response("Account with email already exists.", status_code=status.HTTP_409_CONFLICT, media_type="text/plain")

	salt = User.generate_salt()
	password_hash = cryptographic_hash(password, salt=salt)

	user = User(name=username, email=email, salt=salt, password_hash=password_hash)

	session.add(user)
	await session.commit()
	response = Response(f"Account created for {email}.", status_code=status.HTTP_201_CREATED, media_type="text/plain")
	return await create_cookie(request, response, session, user)


@router.post("/login", tags=[TAG])
async def login_user(request: Request, email: Annotated[EmailStr, Form()], password: Annotated[str, Form()]) -> Response:
	db_session: AsyncSession = request.state.session
	results = await db_session.execute(select(User).where(User.email == email.strip().lower()))
	actual_user: Optional[User] = results.scalar_one_or_none()

	if not actual_user:
		return Response(content="Invalid email/password.", status_code=status.HTTP_401_UNAUTHORIZED, media_type="text/plain")

	actual_user = actual_user

	if not actual_user.verify_password(password):
		return Response(content="Invalid email/password.", status_code=status.HTTP_401_UNAUTHORIZED, media_type="text/plain")

	response = Response(status_code=status.HTTP_200_OK, media_type="text/plain", headers={"Location": request.headers["Referer"]})
	return await create_cookie(request, response, db_session, actual_user)


@router.get("/login-orcid", tags=[TAG], include_in_schema=False)
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
			return ORJSONResponse({**response.json(), "status_code": response.status_code}, status_code=500)

		json = response.json()

	session: AsyncSession = request.state.session
	results = await session.execute(select(User).where(User.orcid == json["orcid"]))
	actual_user: Optional[User] = results.scalar_one_or_none()
	response = Response(headers={"Location": ui_settings.DASHBOARD_URL}, status_code=308)
	if actual_user is None:
		# Create user
		actual_user = User(name=json["name"], orcid=json["orcid"])
		session.add(actual_user)
		await session.commit()

	return await create_cookie(request, response, session, actual_user)


@router.get("/logout", tags=[TAG])
async def logout_user(request: Request) -> Response:
	db_session: AsyncSession = request.state.session
	session_id = request.cookies.get("session_id")
	if not session_id:
		return Response("No user logged in to begin with.", status_code=status.HTTP_202_ACCEPTED, media_type="text/plain")

	session = await get_user_from_session(db_session, session_id)
	await db_session.delete(session)
	await db_session.commit()

	headers = {"Location": referer} if (referer := request.headers.get("Referer")) else dict()
	response = Response("User logged out successfully.", status_code=status.HTTP_200_OK, media_type="text/plain",
						headers=headers)
	response.delete_cookie(key="session_id", domain=get_cookie_domain(request))
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


@router.get("/get_username", include_in_schema=False)
async def get_username(request: Request) -> ORJSONResponse:
	user_id = request.state.user_id
	session: AsyncSession = request.state.session

	if user_id is None:
		return ORJSONResponse({"username": "Not Logged In."}, status_code=status.HTTP_403_FORBIDDEN)
	elif user_id == get_guest_uuid():
		return ORJSONResponse({"username": "Not Logged In."}, status_code=status.HTTP_202_ACCEPTED)

	result = await session.execute(text("SELECT name FROM users.users WHERE id = :id;"), params=dict(id=user_id))
	result = result.fetchone()
	if not result:
		return ORJSONResponse({"username": "Logged in, but could not find username."}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
	return ORJSONResponse({"username": result[0]}, status_code=status.HTTP_200_OK)


@router.get("/previous_runs", tags=[TAG])
async def previous_runs(request: Request) -> ORJSONResponse:
	session: AsyncSession = request.state.session

	results = await session.execute(text("""WITH
                                                s AS (SELECT run_id, COUNT(run_id) AS num_figures FROM results.subfigure GROUP BY run_id),
                                                a AS (SELECT run_id, COUNT(run_id) AS num_articles FROM results.article GROUP BY run_id)
                                            SELECT
                                                r.id, r.status, r.search_query->>'name' AS name, r.search_query->'query'->'search_field_1'->'term' AS term,
                                                r.start_time, r.end_time, COALESCE(r.end_time, NOW()) - r.start_time AS run_time, r.search_query->>'maximum_scraped' AS max_articles,
                                                a.num_articles, s.num_figures
                                            FROM results.results r
                                                     LEFT JOIN s ON r.id = s.run_id
                                                     LEFT JOIN a ON r.id = a.run_id
                                            WHERE r.user_id = :user_id
                                            ORDER BY r.start_time DESC"""), params=dict(user_id=request.state.user_id))
	runs = results.fetchall()

	output = [None] * len(runs)
	keys = ["id", "status", "name", "term", "start_time", "end_time", "run_time", "max_articles", "num_articles", "num_figures"]
	for i, run in enumerate(runs):
		run = dict(zip(keys, run))
		run["id"] = UUID(str(run["id"]))
		run["run_time"] = run["run_time"].total_seconds()
		output[i] = run

	return ORJSONResponse(output, status_code=status.HTTP_200_OK)
