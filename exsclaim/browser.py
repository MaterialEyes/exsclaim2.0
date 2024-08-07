from playwright.sync_api import sync_playwright, Browser, Page
from typing import Callable, Any


__all__ = ["ExsclaimBrowser"]


class ExsclaimBrowser(object):
	def __init__(self, browser:Browser=None, set_extra_headers:bool=True, **kwargs):
		...

	def __del__(self):
		self.close_browser()

	def close_browser(self):
		...

	def temporary_browser(self, function:Callable[[Page, Any], Any], set_extra_headers=True, **kwargs):
		with sync_playwright() as playwright:
			browser = playwright.chromium.launch(headless=True, chromium_sandbox=False)

			page = browser.new_page()
			if set_extra_headers:
				self.set_extra_page_headers(page)

			values = function(page, browser=browser, **kwargs)
			page.close()
			browser.close()
		return values

	@staticmethod
	def set_extra_page_headers(page:Page):
		page.set_extra_http_headers({
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
			"Accept-Encoding": "gzip, deflate, br, zstd",
			"Accept-Language": "en-US,en;q=0.5",
			"Cache-Control": "max-age=0",
			"Priority": "u=0, i",
			"Sec-Ch-Ua": '"Brave";v="125", "Chromium";v="125", "Not.A / Brand";v="24"',
			"Sec-Ch-Ua-Mobile": "?0",
			"Sec-Ch-Ua-Platform": "Linux",
			"Sec-Fetch-Dest": "document",
			"Sec-Fetch-Mode": "navigate",
			"Sec-Fetch-Site": "none",
			"Sec-Fetch-User": "?1",
			"Sec-Gpc": "1",
			"Upgrade-Insecure-Requests": "1",
			"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
		})
