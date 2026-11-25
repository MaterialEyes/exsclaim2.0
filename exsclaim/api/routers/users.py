from exsclaim.config import ui_settings
lazy from exsclaim.config import orcid_settings
lazy from exsclaim.db import get_db_session, cryptographic_hash
lazy from exsclaim.utilities.email import _EMAIL_AVAILABLE

lazy from ..models import User, PasswordReset, get_guest_uuid, ExsclaimJSONResponse as JSONResponse
lazy from ..dependencies.users import LoginInfo, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, ActiveUser, \
	CurrentUser, CurrentUserId, ActiveUserId, create_access_token, create_refresh_token, extract_refresh_token, \
	RefreshTokenCookie
lazy from ..dependencies.email_verification import send_verification_email, verify_email, send_password_reset_email

lazy from datetime import datetime as dt, timezone as tz, timedelta as td
lazy from fastapi import APIRouter, BackgroundTasks, Body, Cookie, HTTPException, status
lazy from starlette.requests import Request
lazy from starlette.responses import Response, HTMLResponse, RedirectResponse
lazy from sqlmodel import select
lazy from typing import Optional
lazy from uuid import uuid4, UUID

lazy import asyncpg
lazy import html
lazy import httpx2
import pydantic
lazy import sqlalchemy as sa
lazy import sqlalchemy.exc as sql_exc

__all__ = ["router"]


router = APIRouter(prefix="/user")
TAG = "User Management"


def get_cookie_domain() -> str:
	return ui_settings.DOMAIN.domain


def get_api_cookie_domain() -> str:
	return ui_settings.PUBLIC_API_URL.domain


async def add_user_jti(user: User | UUID, jti: UUID):
	if isinstance(user, User):
		user_id = user.id
	else:
		user_id = user

	async with get_db_session() as session:
		await session.execute(sa.text("INSERT INTO users.jtis VALUES(:user_id, :jti)"), dict(user_id=user_id, jti=jti))
		await session.commit()


async def remove_user_jti(user: User | UUID, jti: UUID):
	if isinstance(user, User):
		user_id = user.id
	else:
		user_id = user

	async with get_db_session() as session:
		await session.execute(sa.text("DELETE FROM users.jtis WHERE id = :user_id AND jti = :jti"), dict(user_id=user_id, jti=jti))
		await session.commit()


async def user_has_jti(user: User, jti: UUID) -> bool:
	async with get_db_session() as session:
		results = await session.execute(sa.text("SELECT EXISTS (SELECT 1 FROM users.jtis WHERE id = :user_id AND jti = :jti)"), dict(user_id=user.id, jti=jti))
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
		httponly=False,
		secure=True,
		domain=get_cookie_domain(),
		samesite="lax",
		max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
		path="/"
	)

	response.headers["X-EXSCLAIM-Access-Minutes"] = str(ACCESS_TOKEN_EXPIRE_MINUTES)
	return response


async def create_refresh_token_for_cookie(user: User, response: Response) -> Response:
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
		path=f"{router.prefix}/protected"
	)

	response.headers["X-EXSCLAIM-Refresh-Days"] = str(REFRESH_TOKEN_EXPIRE_DAYS)
	return response


def is_valid_username(username: str) -> bool:
	# TODO: Check for profanity before allowing the username
	return True


@router.api_route("/cookie/{path}", methods=["GET", "POST"])
async def redirect_old_path_get(path: str) -> Response:
	return RedirectResponse(f"/protected/{path}", status_code=301)


@router.post("/create_user", tags=[TAG])
async def old_signup_path():
	return RedirectResponse(router.prefix + "/signup", status.HTTP_308_PERMANENT_REDIRECT)


@router.post("/signup", tags=[TAG])
async def create_user(info: LoginInfo, background_tasks: BackgroundTasks):
	if not ui_settings.ALLOW_LOGIN_WITH_EMAIL:
		raise HTTPException(
			status.HTTP_403_FORBIDDEN,
			detail="EXSCLAIM currently does not allow users to create accounts using email/password. Please use a different method."
		)

	email = info.email.strip().lower()
	username = info.username.strip()
	password = info.password.strip()

	async with get_db_session() as session:
		results = await session.execute(select(User).where(User.email == email))
		existing_user: Optional[User] = results.scalar_one_or_none()

	if existing_user:
		raise HTTPException(status.HTTP_409_CONFLICT, "Account with email already exists.")

	if not is_valid_username(username):
		return JSONResponse(
			{"detail": "Username not valid.", "requested_username": username},
			status_code=status.HTTP_400_BAD_REQUEST
		)

	salt = User.generate_salt()
	password_hash = cryptographic_hash(password, salt=salt)

	username = html.escape(username)
	user = User(name=username, email=email, salt=salt, password_hash=password_hash, email_verified=False)

	async with get_db_session(expire_on_commit=False) as session:
		session.add(user)
		await session.commit()

	if _EMAIL_AVAILABLE:
		background_tasks.add_task(send_verification_email, email, user.id)

	response = JSONResponse({"detail": f"Account created for {email}."}, status_code=status.HTTP_201_CREATED)
	response = await create_access_token_for_cookie(user, response)
	response = await create_refresh_token_for_cookie(user, response)
	return response


@router.get("/validate")
async def validate_email(code: str):
	await verify_email(code)
	return JSONResponse({"detail": "Email verified."}, status_code=status.HTTP_200_OK)


async def get_user_from_login(info: LoginInfo) -> User:
	email = info.email.strip().lower()
	password = info.password.strip()

	async with get_db_session() as session:
		results = await session.execute(select(User).where(User.email == email))
		user: Optional[User] = results.scalar_one_or_none()

	if user is None or not user.verify_password(password):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid email/password.",
			headers={"WWW-Authenticate": "Bearer"},
		)

	return user


@router.post("/login", tags=[TAG])
async def login_user(request: Request, info: LoginInfo) -> Response:
	if not ui_settings.ALLOW_LOGIN_WITH_EMAIL:
		raise HTTPException(
			status.HTTP_403_FORBIDDEN,
			detail="EXSCLAIM currently does not allow users to login to accounts using email/password. Please use a different method."
		)

	actual_user = await get_user_from_login(info)
	response = JSONResponse(
		{"status": "Logged in successfully!", "user": actual_user.name},
		status_code=status.HTTP_200_OK
	)

	referer = request.headers.get("Referer")
	if referer is not None:
		response.headers["Location"] = referer

	response = await create_access_token_for_cookie(actual_user, response)
	response = await create_refresh_token_for_cookie(actual_user, response)
	return response


@router.api_route("/login-orcid", methods=["GET", "HEAD"], tags=[TAG], include_in_schema=False)
async def login_with_orcid(request: Request, code: str):
	async with httpx2.AsyncClient() as client:
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
			logger = request.state.logger
			logger.error(f"Login failed with status code {response.status_code}: {response.text}")
			return JSONResponse({**response.json(), "status_code": response.status_code}, status_code=500)

		json = response.json()

	async with get_db_session() as session:
		results = await session.execute(select(User).where(User.orcid == json["orcid"]))
		actual_user: Optional[User] = results.scalar_one_or_none()
		if actual_user is None:
			# Create user
			actual_user = User(name=json["name"], orcid=json["orcid"], email_verified=None)
			session.add(actual_user)
			await session.commit()

		response = RedirectResponse(ui_settings.DASHBOARD_URL)
		response = await create_access_token_for_cookie(actual_user, response)
		response = await create_refresh_token_for_cookie(actual_user, response)
		return response


@router.post("/protected/refresh", tags=[TAG])
async def refresh(refresh_token: str = Cookie()):
	payload = extract_refresh_token(refresh_token)

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


@router.api_route("/protected/logout", methods=["GET", "HEAD"], tags=[TAG])
async def logout_user(request: Request, user_id: ActiveUserId, cookie: RefreshTokenCookie) -> Response:
	payload = extract_refresh_token(cookie)
	await remove_user_jti(user_id, payload["jti"])

	headers = {"Location": referer} if (referer := request.headers.get("Referer")) else dict()
	response = Response("User logged out successfully.", status_code=status.HTTP_200_OK, media_type="text/plain",
						headers=headers)
	response.delete_cookie(key="access_token", domain=get_cookie_domain())
	response.delete_cookie(key="refresh_token", domain=get_api_cookie_domain())
	return response


@router.post("/logout_all", tags=[TAG])
async def logout_all_instances(user_id: ActiveUserId) -> Response:
	async with get_db_session() as session:
		await session.execute(sa.text("DELETE FROM users.jtis WHERE id = :user_id"), dict(user_id=user_id))
		await session.commit()

	response = JSONResponse(dict(detail=
							 f"All logged in versions of this user can no longer create new access tokens, so they will be logged out within the next {ACCESS_TOKEN_EXPIRE_MINUTES} minutes."),
						status_code=status.HTTP_200_OK)
	response.delete_cookie(key="refresh_token", domain=get_api_cookie_domain())
	return response


class ResetRequest(pydantic.BaseModel):
	email: pydantic.EmailStr


@router.post("/send_reset", tags=[TAG])
async def send_reset_request_email(request: Request, body: ResetRequest, background_tasks: BackgroundTasks) -> Response:
	now = dt.now(tz.utc)
	email = body.email
	async with get_db_session() as session:
		results = await session.execute(
			sa.text("SELECT id FROM users.users WHERE email = :email"),
			dict(email=email)
		)
		user_id = results.scalar_one_or_none()
		if user_id is not None:
			background_tasks.add_task(send_password_reset_email, request, email, user_id, now)

	return JSONResponse(
		{"detail": "If an account with this email exists, it will receive the password reset email."},
		status_code=status.HTTP_200_OK
	)


@router.get("/reset_password", tags=[TAG], include_in_schema=False)
async def reset_password(request: Request, code: str) -> Response:
	# async with get_db_session() as db:
	# 	if token is None:
	# 		# Email the user a URL to get to the reset page.
	# 		return await send_reset_request_email(request, db, email)
	#
	# 	results = await db.execute(select(PasswordReset).where(PasswordReset.token == token))
	# 	reset_obj: PasswordReset = results.scalar_one_or_none()
	#
	# if (reset_obj is None) or (reset_obj.email != email) or (dt.now(tz.utc) - reset_obj.created > td(hours=1)):
	# 	return Response("The email/token pair was invalid.", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, media_type="text/plain")
	#
	# response = HTMLResponse(
	# 	"",
	# 	status_code=status.HTTP_202_ACCEPTED,
	# 	headers={"Referrer-Policy": "no-referrer"},
	# )
	#
	# # other_response = await logout_all_instances(...)
	# # other_response
	#
	# # await send_email() # TODO: Send an email to the email on file that the password was reset
	#
	# return response
	raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail="The password reset logic is not fully set up.")


@router.get("/id", tags=[TAG])
async def get_user_id(user_id: CurrentUserId) -> JSONResponse:
	not_logged_in = {"id": "Not Logged In."}
	if user_id == get_guest_uuid():
		return JSONResponse(not_logged_in, status_code=status.HTTP_202_ACCEPTED)
	return JSONResponse({"id": str(user_id)}, status_code=status.HTTP_200_OK)


@router.get("/name", tags=[TAG])
async def get_username(user: CurrentUser) -> JSONResponse:
	not_logged_in = {"username": "Not Logged In."}
	if user is None or user.id == get_guest_uuid():
		return JSONResponse(not_logged_in, status_code=status.HTTP_202_ACCEPTED)

	return JSONResponse({"username": user.name}, status_code=status.HTTP_200_OK)


@router.patch("/name", tags=[TAG])
async def update_username(request: Request, user: ActiveUser, username: str = Body(...)) -> JSONResponse:
	if not is_valid_username(username):
		return JSONResponse(
			{"detail": "Username not valid.", "requested_username": username},
			status_code=status.HTTP_400_BAD_REQUEST
		)

	old_username = user.name
	username = html.escape(username)

	try:
		async with get_db_session() as session:
			await session.execute(sa.update(User).where(User.id == user.id).values(name=username))
			await session.commit()
	except sql_exc.SQLAlchemyError as e:
		await session.rollback()
		request.state.logger.error(
			f"An error stopped user {user.id} from updating their username to: \"{username}\"",
			exc_info=e
		)
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


@router.delete("/protected/remove_user", tags=[TAG])
async def delete_user(request: Request, user: ActiveUser, refresh_token: RefreshTokenCookie) -> JSONResponse:
	extract_refresh_token(refresh_token)
	async with get_db_session() as session:
		try:
			await session.execute(sa.delete(User).where(User.id == user.id))
			await session.commit()
		except sql_exc.SQLAlchemyError as e:
			await session.rollback()
			request.state.logger.exception(f"Could not successfully delete user {user.id}.", exc_info=e)
			return JSONResponse(
				{"detail": "An error occurred while trying to delete user."},
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
			)

	return JSONResponse(dict(detail="Successfully deleted user from database.", user=user.name, id=str(user.id)),
						status_code=status.HTTP_200_OK)


# @router.api_route("/get_jwt_public_key", methods=["GET", "HEAD"], tags=[TAG])
# async def get_public_key(request: Request):
# 	return PlainTextResponse(PUBLIC_KEY, status_code=status.HTTP_200_OK)


@router.post("/merge_accounts", tags=[TAG],
			 description="Merges an ORCID account with an account created using email and password")
async def merge_accounts(request: Request, info: LoginInfo, orcid_user: ActiveUser) -> Response:
	if orcid_user.orcid is None:
		return JSONResponse({"detail": "You must be logged in as your ORCID account, not your account with your email and password."}, status_code=status.HTTP_409_CONFLICT)

	email_user = await get_user_from_login(info)
	if email_user.id == orcid_user.id:
		return JSONResponse(dict(detail=f"User with email {email_user.email} and ORCID {orcid_user.orcid} are the same account, so they can't be merged."), status_code=status.HTTP_400_BAD_REQUEST)

	older_created_at = orcid_user.created if orcid_user.created < email_user.created else email_user.created
	email_params = dict(email_user=email_user.id)
	try:
		async with get_db_session() as session:
			# Move the owner ID for all runs from the orcid account where it was originally the email account
			await session.execute(sa.text("UPDATE results.runs SET user_id = :orcid_user WHERE user_id = :email_user"),
								  dict(orcid_user=orcid_user.id, email_user=email_user.id))

			# Delete any JTIs for the email account
			await session.execute(sa.text("DELETE FROM users.jtis WHERE id = :email_user"), email_params)

			# Move all of the information from the email user to the orcid user, keeping the creation timestamp as whichever account was created first
			await session.execute(sa.text("""UPDATE users.users
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
			await session.execute(sa.text("DELETE FROM users.users WHERE id = :email_user"), email_params)

			# Add the email to the ORCID account (Couldn't do this before because emails have to be unique)
			await session.execute(sa.text("""UPDATE users.users SET email=:email WHERE id = :orcid_user"""),
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


@router.get("/articles", tags=[TAG],
			description="Returns a list of articles authored by the current user (if they have an ORCID id attached).")
async def get_articles(user: CurrentUser) -> JSONResponse:
	if user.id == get_guest_uuid():
		return JSONResponse({"detail": "Not logged in."}, status_code=status.HTTP_401_UNAUTHORIZED)

	if user.orcid is None:
		return JSONResponse(
			{"detail": "You must have an ORCID id attached to this account to see which articles attached to this user have been viewed."},
			status_code=status.HTTP_412_PRECONDITION_FAILED
		)

	async with get_db_session() as session:
		results = await session.execute(
			sa.text("SELECT title, url FROM results.article WHERE id IN (SELECT article_id FROM results.article_authors WHERE author_id = (SELECT id FROM results.authors WHERE orcid = :orcid));"),
			dict(orcid=user.orcid)
		)
		articles = dict(results.scalars().all())
		return JSONResponse(articles, status_code=status.HTTP_200_OK)
