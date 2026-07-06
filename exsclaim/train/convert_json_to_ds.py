from .ds_features import *

import datasets
import huggingface_hub as hf

from datetime import datetime as dt, timezone as tz
from httpx import Client
from orjson import loads
from pathlib import Path
from PIL import Image
from re import match
from typing import Any, Collection


__all__ = ["convert_json_to_ds", "append_to_hub"]


def get_journal_from_url(image_url) -> str:
	if match("^https?://media.springernature.com", image_url):
		return "Nature"

	print(f"Unknown image url: {image_url}")
	return ""


def convert_json_to_ds(exsclaim_jsons: Collection[Path | dict[str, Any]]) -> tuple[datasets.Dataset, datasets.Dataset]:
	images, captions = [], []
	client = Client()

	for exsclaim_json in exsclaim_jsons:
		if isinstance(exsclaim_json, Path):
			created_at = dt.fromtimestamp(exsclaim_json.stat().st_mtime, tz=tz.utc)
			exsclaim_json: dict[str, Any] = loads(exsclaim_json.read_text())
		else:
			created_at = dt.now(tz=tz.utc)

		for _id, image in exsclaim_json.items():
			journal = get_journal_from_url(image["url"])
			url = image["article_url"]
			subcaptions = sorted([dict(Label=subimage["label"], Text=subimage["subcaption"]) for subimage in image["subfigures"]],
								 key=lambda k: k.get("Label", "").upper())

			master_images = [dict(classification=subimage["classification"], geometry=dict(x0=subimage["x0"], y0=subimage["y0"], x1=subimage["x1"], y1=subimage["y1"]))
							 for subimage in image["subfigures"]]
			subfigure_label = [dict(text=subimage["label"], geometry=dict(x0=subimage["label_x0"], y0=subimage["label_y0"], x1=subimage["label_x1"], y1=subimage["label_y1"]))
							   for subimage in image["subfigures"]]
			# TODO: Run this with these lines uncommented to make sure nothing crashes
			scale_bar_labels = [dict(text=scalebar["label"]["text"], geometry=scalebar["label"]["geometry"]) for subimage in image["subfigures"] for scalebar in subimage["scale_bars"]]
			scale_bar_lines = [dict(geometry=scalebar["geometry"]) for subimage in image["subfigures"] for scalebar in subimage["scale_bars"]]
			# scale_bar_labels = []
			# scale_bar_lines = []

			with client.stream("GET", image["url"]) as response:
				if response.is_error:
					print(f"Could not get image from {image['url']}: {response.text}")

				image_obj = Image.open(response)

			info: dict[str, Any] = {
				"Master Image": master_images,
				"Subfigure Label": subfigure_label,
				"Scale Bar Label": scale_bar_labels,
				"Scale Bar Line": scale_bar_lines,
			}

			images.append({
				"Journal": journal,
				"ID": _id,
				"Url": url,
				"Image": image_obj,
				"Info": info,
				"Created At": created_at
			})
			captions.append({
				"Journal": journal,
				"ID": _id,
				"Url": url,
				"Caption": image["caption"],
				"Subcaptions": subcaptions,
				"Created At": created_at
			})

	image_ds = datasets.Dataset.from_list(images, features=image_features)
	caption_ds = datasets.Dataset.from_list(captions, features=caption_features)

	return image_ds, caption_ds


def append_to_hub(repo_id: str, dataset: datasets.Dataset, prioritize_old_data: bool = False, **kwargs) -> datasets.Dataset:
	api = hf.HfApi()

	try:
		api.dataset_info(repo_id)
		repo_exists = True
	except hf.errors.RepositoryNotFoundError:
		repo_exists = False

	if not repo_exists:
		dataset.push_to_hub(repo_id, **kwargs)
		return dataset

	original_dataset = datasets.load_dataset(repo_id, features=dataset.features)
	original_dataset = original_dataset.cast_column("Created At", image_features["Created At"])

	if isinstance(original_dataset, datasets.DatasetDict):
		shape = original_dataset.shape
		if len(shape) == 1:
			original_dataset = original_dataset[tuple(shape.keys())[0]]
		else:
			original_dataset = original_dataset[tuple(shape.keys())[0]] # TODO: Figure out what to do when there are multiple splits

	old_ids = set(original_dataset["ID"])
	new_ids = set(dataset["ID"])

	intersection = old_ids.intersection(new_ids)
	if len(intersection) > 0:
		if prioritize_old_data:
			dataset = dataset.filter(lambda row: row["ID"] not in intersection)
		else:
			original_dataset = original_dataset.filter(lambda row: row["ID"] not in intersection)

	combined = datasets.concatenate_datasets([original_dataset, dataset])
	combined.push_to_hub(repo_id, **kwargs)
	return combined
