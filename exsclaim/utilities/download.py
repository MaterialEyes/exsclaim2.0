"""Functions for downloading from Google Drive

Adapted from `this StackOverflow <https://stackoverflow.com/questions/38511444/>`_
"""
from bs4 import BeautifulSoup
from os import PathLike
from typing import Optional

import httpx

__all__ = ["download_file_from_google_drive", "get_confirm_token", "save_response_content"]


async def download_file_from_google_drive(file_id: str, destination: PathLike[str]):
	url = "https://drive.usercontent.google.com/download"
	async with httpx.AsyncClient() as client:
		params = dict(id=file_id, export="download", confirm="t")
		response = await client.get(url, params=params)
		token = await get_confirm_token(response)
		if token:
			params |= token
			response = await client.get(url, params=params)
		await save_response_content(response, destination)


async def get_confirm_token(response: httpx.Response) -> Optional[dict]:
	for header, value in response.headers.items():
		if header == "Content-Type":
			if value == "application/octet-stream":
				return None
			if value.startswith("text/html"):
				break
	else:
		return None

	# Need to press the Download anyway button
	soup = BeautifulSoup(response.text, "html.parser")
	form = soup.select_one("form#download-form")
	return {_input["name"]: _input["value"] for _input in form.find_all("input", attrs={"type": "hidden"})}


async def save_response_content(response: httpx.Response, destination: PathLike[str]):
	CHUNK_SIZE = 2_048
	with open(destination, "wb") as f:
		async for chunk in response.aiter_bytes(CHUNK_SIZE):
			if chunk:  # filter out keep-alive new chunks
				f.write(chunk)
