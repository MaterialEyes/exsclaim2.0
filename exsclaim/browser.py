from asyncio import create_task, get_running_loop
from playwright.sync_api import sync_playwright, Browser as SyncBrowser, Page as SyncPage
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from typing import Callable, Any


__all__ = ["ExsclaimBrowser"]


class ExsclaimBrowser(object):
	__playwright = None
	__browser = None
	__browser_context = None
	__instances = set()

	def __init__(self, **kwargs):
		self.__instances.add(self)

	def __del__(self):
		self.__instances.remove(self)

	async def __aenter__(self):
		if self.__playwright is None:
			await self.__initialize_browser()
		return self

	async def __aexit__(self, *args, **kwargs):
		if len(self.__instances) == 1:
			await self.__close_browser()

	async def __initialize_browser(self):
		self.__playwright = await async_playwright().start()
		self.__browser = await self.__playwright.chromium.launch(headless=True)
		self.__browser_context = await self.__browser.new_context()

	async def __close_browser(self):
		await self.__browser_context.close()
		await self.__browser.close()
		await self.__playwright.stop()

	async def new_context(self, **kwargs) -> BrowserContext:
		return await self.__browser.new_context(**kwargs)

	async def new_page(self, context:BrowserContext=None, set_extra_headers:bool=True) -> Page:
		context = context or self.__browser_context

		page = await context.new_page()
		if set_extra_headers:
			await self.set_extra_page_headers(page)
		return page

	@staticmethod
	async def set_extra_page_headers(page:Page):
		await page.set_extra_http_headers({
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
