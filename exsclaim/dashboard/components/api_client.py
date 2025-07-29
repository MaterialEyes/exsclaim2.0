from exsclaim.api import Status
from httpx import AsyncClient
from typing import Any


__all__ = ["fetch_status", "fetch_articles", "fetch_figures", "fetch_subfigures"]


async def fetch_status(client:AsyncClient, base_url: str, result_id: str) -> Status:
	"""Fetch the status of a result from the API."""
	try:
		response = await client.get(f"{base_url}/status/{result_id}")
		if response.is_success:
			data = response.json()
			match data["status"]:
				case "Finished.":
					return Status.FINISHED
				case "Killed.":
					return Status.KILLED
			return Status.RUNNING

		return Status.ERROR
	except Exception as e:
		print(f"Error fetching status: `{e.__class__.__name__}` `{e}`.")
		return Status.ERROR


async def fetch_articles(client:AsyncClient, base_url: str, result_id: str) -> list[dict[str, Any]]:
	"""Fetch articles from the API."""
	try:
		response = await client.get(f"{base_url}/results/v1/{result_id}/articles")
		if response.status_code == 200:
			return response.json()
		return []
	except Exception as e:
		print(f"Error fetching articles: {e}")
		return []


async def fetch_figures(client:AsyncClient, base_url: str, result_id: str, page: int = 1) -> list[dict[str, Any]]:
	"""Fetch figures from the API."""
	try:
		response = await client.get(f"{base_url}/results/v1/{result_id}/figures/?page={page}")
		if response.status_code == 200:
			return response.json()
		return []
	except Exception as e:
		print(f"Error fetching figures: {e}")
		return []


async def fetch_subfigures(client:AsyncClient, base_url: str, result_id: str, page: int = 1) -> list[dict[str, Any]]:
	"""Fetch subfigures from the API."""
	try:
		response = await client.get(f"{base_url}/results/v1/{result_id}/subfigures/?page={page}")
		if response.status_code == 200:
			return response.json()
		return []
	except Exception as e:
		print(f"Error fetching subfigures: {e}")
		return []
