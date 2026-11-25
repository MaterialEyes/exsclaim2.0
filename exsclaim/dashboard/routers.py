lazy from exsclaim.config import ui_settings

lazy from fastapi import APIRouter
lazy from starlette.responses import Response, FileResponse, RedirectResponse, PlainTextResponse
lazy from textwrap import dedent

__all__ = ["router"]

router = APIRouter()


@router.api_route("/terms-of-service")
def terms_of_service():
	return FileResponse("assets/terms_of_service.html")


@router.api_route("/privacy-policy")
def privacy_policy():
	return FileResponse("assets/privacy_policy.html")


@router.api_route("/favicon.ico")
def favicon_ico():
	return FileResponse("assets/favicon.ico")


@router.api_route("/favicon.png")
def favicon_png():
	return FileResponse("assets/favicon.png")


@router.api_route("/logout")
def logout():
	return RedirectResponse(f"{ui_settings.PUBLIC_API_URL}/user/protected/logout")


@router.api_route("/robots.txt")
def robots():
	robots = dedent(f"""\
		User-Agent: *
		Content-signal: search=yes, ai-train=no, use=reference
		Allow: /

		User-Agent: Amazonbot
		Disallow: /

		User-agent: Applebot-Extended
		Disallow: /

		User-agent: Bytespider
		Disallow: /

		User-agent: CCBot
		Disallow: /

		User-Agent: ClaudeBot
		Disallow: /

		User-Agent: Google-Extended
		Disallow: /

		User-Agent: GPTBot
		Disallow: /

		Allow: /login

		Allow: /signup

		Allow: /terms-of-service

		Allow: /privacy-policy

		Disallow: /results/*

		Disallow: /train

		Disallow: /previous

		Disallow: /logout

		Sitemap: {ui_settings.DASHBOARD_URL}/sitemap.xml
	""")
	return PlainTextResponse(robots, status_code=200)


_SITEMAP = None


@router.api_route("/sitemap.xml")
def sitemap():
	global _SITEMAP
	if _SITEMAP is None:
		host = ui_settings.DASHBOARD_URL
		last_mod = dt.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%z")

		def format_xml(page) -> Optional[str]:
			path = page["relative_path"].replace("/none", "/*")

			return dedent(f"""\
					<url>
						<loc>{host}{path}</loc>
						<lastmod>{last_mod}</lastmod>
					</url>
				""")

		routes = map(lambda page: format_xml(page), dash.page_registry.values())
		_SITEMAP = f'<urlset xmlns="https://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="https://www.w3.org/1999/xhtml">\n{''.join(routes)}</urlset>'

	return Response(_SITEMAP, status_code=200, media_type="text/xml")
