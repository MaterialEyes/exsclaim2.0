"""Functions for downloading from Google Drive

Adapted from `this StackOverflow <https://stackoverflow.com/questions/38511444/>`_
"""
from aiohttp import ClientSession, ClientResponse
from bs4 import BeautifulSoup
from os import PathLike


__all__ = ["download_file_from_google_drive", "get_confirm_token", "save_response_content"]


async def download_file_from_google_drive(file_id:str, destination:PathLike[str]):
	URL = "https://drive.usercontent.google.com/download"
	async with ClientSession() as session:
		params = dict(id=file_id, export="download", confirm="t")
		async with session.get(URL, params=params) as response:
			token = await get_confirm_token(response)
			if token:
				params |= token
				response2 = session.get(URL, params=params)
				response = response2
			await save_response_content(response, destination)


async def get_confirm_token(response:ClientResponse) -> dict | None:
	for header, value in response.headers.items():
		if header == "Content-Type":
			if value == "application/octet-stream":
				return None
			if value.startswith("text/html"):
				break
	else:
		return None
	text = await response.text()

	# Need to press the Download anyway button
	soup = BeautifulSoup(text, "html.parser")
	form = soup.select_one("form#download-form")
	return {_input["name"]: _input["value"] for _input in form.find_all("input", attrs={"type": "hidden"})}


async def save_response_content(response:ClientResponse, destination:PathLike[str]):
	CHUNK_SIZE = 32_768
	with open(destination, "wb") as f:
		async for chunk in response.content.iter_chunked(CHUNK_SIZE):
			if chunk:  # filter out keep-alive new chunks
				f.write(chunk)
