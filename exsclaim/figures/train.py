from collections import defaultdict
from json import load
from os import PathLike
from pathlib import Path
from PIL import Image
from re import compile, IGNORECASE
from httpx import AsyncClient
from sklearn.model_selection import train_test_split
from tempfile import TemporaryDirectory
from textwrap import dedent
from torch.cuda import is_available as cuda_available
from typing import Iterable, Literal
from ultralytics import YOLO

import cv2
# import wandb


Point = tuple[int | float, int | float]
Polygon = dict[str, str]
Model = str | Path


def coordinates_from_geometry(geometry: list[dict[str, int | float]]) -> tuple[Point, Point]:
	def get_high_low(coord: Literal["x", "y"]):
		values = set(map(lambda value: value[coord], geometry))
		return min(values), max(values)

	x1, x2 = get_high_low("x")
	y1, y2 = get_high_low("y")

	return (x1, y1), (x2, y2)


def polygon_to_bbox(polygon: Iterable[Polygon]):
	(x_min, y_min), (x_max, y_max) = coordinates_from_geometry(polygon)

	x_center = (x_min + x_min) / 2
	y_center = (y_min + y_min) / 2

	width = x_max - x_min
	height = y_max - y_min

	return x_center, y_center, width, height


def is_point_in_polygon(point: Point, polygon: Polygon) -> bool:
	x, y = point
	inside = False
	n = len(polygon)
	px1, py1 = polygon[0]["x"], polygon[0]["y"]

	for i in range(n+1):
		px2, py2 = polygon[i % n]["x"], polygon[i % n]["y"]

		if min(py1, py2) < y <= max(py1, py2) and x <= max(px1, px2):
			if py1 != py2:
				x_inters = (y - py1) * (px2 - px1) / (py2 - py1) + px1
			if py1 == px2 or x <= x_inters:
				inside = not inside

		px1, py1 = px2, py2
	return inside


def create_class_id_mapping(subfigure_labels: set[str], priority_labels: Iterable[str]) -> dict[str, int]:
	"""Function to create class ID mapping with priority for specific labels"""
	standard_labels_regex = compile(r"\W", IGNORECASE)
	# standard_labels = {"a": 0 "b": 1 "c": 2 "d": 3 "e": 4 "f": 5 "g": 6 "h": 7, "i": 8}
	standard_labels = {chr(char + ord("A")): char for char in range(9)}

	class_id_mapping = {}
	current_id = 0

	for label in priority_labels:
		label = standard_labels_regex.sub("", label).upper()
		if label in subfigure_labels and label not in class_id_mapping:
			class_id_mapping[label] = standard_labels[label]
			current_id += 1

	return class_id_mapping


async def process_data(image_path):
	with Image.open(image_path) as image:
		if image.format == "GIF":
			image.save(image_path, format="PNG")


async def process_data_split(data_split: Iterable[dict], split_name: str, images_path: Path, detect_path: Path, classify_path: Path,
							 class_id_mapping: dict[str, int], keep_existing_files: bool = True):
	session = AsyncClient()
	classifications = defaultdict(int)

	for entry in data_split:
		image_url = entry["Labeled Data"]
		image_id = entry["External ID"].split(".")[0]
		image_path = images_path / split_name / f"{image_id}.png"

		if not image_path.exists() or not keep_existing_files:
			response = await session.get(image_url)

			if response.status_code >= 400:
				print(response.text)
				continue

			with open(image_path, 'wb') as file:
				file.write(response.content)

			await process_data(image_path)

		image = cv2.imread(str(image_path))
		image_height, image_width, _ = image.shape

		detect_file_path = detect_path / split_name / f"{image_id}.txt"
		with open(detect_file_path, 'w') as detect_file:
			for annotation in entry["Label"].get("Master Image", ()):
				x_center, y_center, width, height = polygon_to_bbox(annotation["geometry"])
				(ix1, iy1), (ix2, iy2) = coordinates_from_geometry(annotation["geometry"])

				x_center /= image_width
				y_center /= image_height
				width /= image_width
				height /= image_height
				classification = annotation.get("classification", "Subfigure").lower().replace(" ", "_")

				# Find corresponding subfigure label
				for sub in entry["Label"].get("Subfigure Label", []):
					if len(sub["geometry"]) >= 4:
						(x1, y1), (x2, y2) = coordinates_from_geometry(sub["geometry"])
						label_center = (
							(x1 + x2) / 2,
							(y1 + y2) / 2,
						)

						if is_point_in_polygon(label_center, annotation["geometry"]):
							subfigure_label: str = sub["text"].strip("()")
							class_id = class_id_mapping.get(subfigure_label)
							if class_id is None:
								continue

							img_path = classify_path / split_name / classification
							img_path.mkdir(parents=True, exist_ok=True)
							img_num = classifications[classification]
							try:
								cv2.imwrite(str(img_path / f"{img_num}.png"), image[iy1:iy2, ix1:ix2])
							except cv2.error as e:
								print(f"Error saving {classification} image for {image_id}: {e}")
							classifications[classification] += 1

							detect_file.write(f"{class_id} {x_center} {y_center} {width} {height}\n")
							print(f'Processed {image_id}: Class ID: {class_id}, Classification Code: {classification}, BBox: {x_center}, {y_center}, {width}, {height}')
							break


async def get_model(base_model: Model, save_path: Model, default_model_file:str) -> tuple[Model, Model]:
	if base_model is None:
		base_model = Path(__file__).parent / "checkpoints" / default_model_file

		if not base_model.is_file():
			from ..utilities import download_model_checkpoint
			await download_model_checkpoint(base_model)

	if save_path is None:
		from datetime import datetime as dt
		if isinstance(base_model, Path):
			save_path = base_model.with_stem(f"{base_model.stem}_{dt.now().isoformat()}")
		else:
			save_path = f"{base_model}_{dt.now().isoformat()}.pt"

	return base_model, save_path


async def train_model(json_file_path:str | PathLike[str], detection_input_model: Model = None,
					  classification_input_model: Model = None, detection_save_path: Model = None,
					  classifier_save_path: Model = None, detector_name: str = "exsclaim_subfigure_detection",
					  classifier_name: str = "exsclaim_subfigure_classification", test_size=1_164, random_state: int = 42,
					  dataset_dir: str | PathLike[str] = None,
					  project: str = "exsclaim_finetuning"):
	with open(json_file_path, 'r') as f:
		data = load(f)

	detection_input_model, detection_save_path = await get_model(detection_input_model, detection_save_path, "yolov11_finetuned_augmentation_best.pt")
	classification_input_model, classifier_save_path = await get_model(classification_input_model, classifier_save_path, "yolov11_classification.pt")

	# Extract all unique subfigure labels
	subfigure_labels = set(
		subfigure["text"].strip("()")
		for entry in data
		for subfigure in entry["Label"].get("Subfigure Label", [])
	)

	priority_labels = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]

	class_id_mapping = create_class_id_mapping(subfigure_labels, priority_labels)
	print(f"Class ID Mapping: {class_id_mapping}")

	# Split data into train and test sets
	train, test = train_test_split(data, test_size=test_size, random_state=random_state)

	dataset_dir = dataset_dir or TemporaryDirectory()
	dataset_path = Path(dataset_dir).resolve()
	data_yaml = dataset_path / "data.yaml"

	with open(data_yaml, 'w') as f:
		f.write(dedent(f"""\
			train: {dataset_path / "images" / "train"}
			val: {dataset_path / "images" / "val"}
			nc: 9
			names: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i']
		"""))

	images_path = dataset_path / "images"
	detect_path = dataset_path / "labels"
	classify_path = dataset_path / "classify"

	for split in ("train", "val"):
		(images_path / split).mkdir(parents=True, exist_ok=True)
		(detect_path / split).mkdir(parents=True, exist_ok=True)
		(classify_path / split).mkdir(parents=True, exist_ok=True)

	# # Process the data splits
	await process_data_split(train, "train", images_path, detect_path, classify_path, class_id_mapping)
	await process_data_split(test, "val",  images_path, detect_path, classify_path, class_id_mapping)

	# Save class ID mapping to a file
	with open(dataset_path / "labels" / "class_id_mapping.txt", 'w') as mapping_file:
		for label, class_id in class_id_mapping.items():
			mapping_file.write(f"{label}: {class_id}\n")

	print("Conversion complete!")

	train_kwargs = dict(
		# device="cpu", # https://docs.ultralytics.com/modes/train/#resuming-interrupted-trainings
		device=0 if cuda_available() else "cpu",
		# https://docs.ultralytics.com/modes/train/#resuming-interrupted-trainings
		epochs=150,
		imgsz=608,
		project=project,
		seed=random_state,
	)

	model = YOLO(detection_input_model)
	model.train(data=data_yaml, name=detector_name, **train_kwargs)
	model.save(detection_save_path)

	classify = YOLO(classification_input_model)
	classify.train(data=str(classify_path), name=classifier_name, **train_kwargs)
	classify.save(classifier_save_path)

	# wandb.init(wandb_project)
	# wandb.log_model(model_path)
	# wandb.finish()

	if isinstance(dataset_dir, TemporaryDirectory):
		dataset_dir.cleanup()
