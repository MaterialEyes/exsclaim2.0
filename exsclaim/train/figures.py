from .ds_features import image_features, classification_labels

from collections import defaultdict
from datetime import datetime as dt
from datasets import load_dataset, Dataset, IterableDataset
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from tqdm import tqdm
from typing import Iterable, Literal, Optional
from ultralytics import YOLO, settings

import cv2
import logging
import os
import mlflow
import re
import shutil
import torch


Point = tuple[int | float, int | float]
Polygon = dict[str, str]
ModelPath = str | Path


def polygon_to_bbox(x_min: int | float, y_min: int | float, x_max: int | float, y_max: int | float):
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


def is_point_in_box(point: Point, geometry: dict[str, int]) -> bool:
	x0, y0, x1, y1 = geometry["x0"], geometry["y0"], geometry["x1"], geometry["y1"]
	return x0 <= point[0] <= x1 and y0 <= point[1] <= y1


def create_class_id_mapping(subfigure_labels: set[str], priority_labels: Iterable[str], num_standard_labels: int = 13) -> dict[str, int]:
	"""Function to create class ID mapping with priority for specific labels"""
	standard_labels_regex = re.compile(r"\W", re.IGNORECASE)
	# standard_labels = {"a": 0 "b": 1 "c": 2 "d": 3 "e": 4 "f": 5 "g": 6 "h": 7, "i": 8}
	standard_labels = {chr(char + ord("A")): char for char in range(num_standard_labels)}

	class_id_mapping = dict()
	current_id = 0

	for label in priority_labels:
		label = standard_labels_regex.sub("", label).upper()
		if label in subfigure_labels and label not in class_id_mapping:
			class_id_mapping[label] = standard_labels[label]
			current_id += 1

	return class_id_mapping


def get_classification(annotation: dict) -> str:
	classification = annotation.get("classification", "Unclear")
	# classification_labels.str2int(classification.lower().replace(" ", "_"))
	if isinstance(classification, int):
		classification = classification_labels.int2str(classification)

	return classification


def process_data_split(data_split: Dataset | IterableDataset, split_name: Literal["train", "val"],
							 images_path: Path, detect_path: Path, labels_path: Path, classify_path: Path,
							 class_id_mapping: dict[str, int], logger: logging.Logger, keep_existing_files: bool = True):
	"""

	:param datasets.Dataset | datasets.IterableDataset data_split: The dataset object (streamed or cached) holding the EXSCLAIM training data.
	:param str split_name: If this is the training or validation (val) split
	:param pathlib.Path images_path: The directory where individual subfigures are stored.
	:param pathlib.Path detect_path: The directory where the coordinates for the subfigures are stored.
	:param pathlib.Path labels_path: The directory where the coordinates for the subfigure labels are stored.
	:param pathlib.Path classify_path: The directory where the subfigure classification type goes.
	:param dict[str, int] class_id_mapping: The dictionary containing the mapping from label to ID number.
	:param logging.Logger logger: The logger object to use for logging.
	:param bool keep_existing_files: If the existing files are kept.
	"""
	classifications = defaultdict(int)

	pbar = tqdm(data_split, desc=f"Processing {split_name}")
	for entry in pbar:
		image_id = entry["ID"].split(".")[0]
		image_path = images_path / split_name / f"{image_id}.png"
		info = entry["Info"]

		image = entry["Image"]
		image.save(image_path, format="PNG")

		image_height, image_width = image.height, image.width

		detect_file_path = detect_path / split_name / f"{image_id}.txt"
		label_file_path = labels_path / split_name / f"{image_id}.txt"

		with open(detect_file_path, 'w') as detect_file, open(label_file_path, 'w') as label_file:
			master_images = info.get("Master Image", ()) or ()
			for annotation in master_images:
				geometry = annotation["geometry"]
				ix1, iy1, ix2, iy2 = geometry["x0"], geometry["y0"], geometry["x1"], geometry["y1"]
				x_center, y_center, width, height = polygon_to_bbox(ix1, iy1, ix2, iy2)

				x_center /= image_width
				y_center /= image_height
				width /= image_width
				height /= image_height
				classification = get_classification(annotation)

				# Find corresponding subfigure label
				labels = info.get("Subfigure Label", ()) or ()
				for sub in labels:
					if len(sub["geometry"]) >= 4 and all(sub["geometry"].values()):
						x1, y1, x2, y2 = sub["geometry"]["x0"], sub["geometry"]["y0"], sub["geometry"]["x1"], sub["geometry"]["y1"]
						*label_center, label_width, label_height = polygon_to_bbox(x1, y1, x2, y2)

						label_center = (
							(x1 + x2) / 2,
							(y1 + y2) / 2,
						)

						if is_point_in_box(label_center, annotation["geometry"]):
							subfigure_label: str = sub["text"].strip("()")
							class_id = class_id_mapping.get(subfigure_label.upper())
							if class_id is None:
								continue

							img_path = classify_path / split_name / classification
							img_path.mkdir(parents=True, exist_ok=True)
							img_num = classifications[classification]
							try:
								image.crop((ix1, iy1, ix2, iy2)).save(img_path / f"{img_num}.png") # image[iy1:iy2, ix1:ix2]
							except cv2.error as e:
								pbar.write(f"Error saving {classification} image for {image_id}: {e}")
								logger.exception(f"Error saving {classification} image for {image_id}.", exc_info=True)
							classifications[classification] += 1

							detect_file.write(f"{class_id} {x_center} {y_center} {width} {height}\n")
							label_file.write(f"{class_id} {label_center[0] / image_width} {label_center[1] / image_height} {label_width / image_width} {label_height / image_height}\n")

							message = f"Processed {image_id}: Class ID: {class_id}, Classification Code: {classification}, BBox: {x_center}, {y_center}, {width}, {height}"
							pbar.write(message)
							logger.debug(message)
							break


async def get_model(base_model: Optional[ModelPath], save_path: Optional[ModelPath], default_model_file: str) -> tuple[ModelPath, ModelPath]:
	if base_model is None:
		base_model = Path(__file__).parent.parent / "figures" / "checkpoints" / default_model_file

		if not base_model.is_file():
			from ..utilities import download_model_checkpoint
			await download_model_checkpoint(base_model)

	if save_path is None:
		if isinstance(base_model, Path):
			save_path = base_model.with_stem(f"{base_model.stem}_{dt.now().isoformat()}")
		else:
			save_path = f"{base_model}_{dt.now().isoformat()}.pt"

	return base_model, save_path


def create_training_logger() -> logging.Logger:
	from exsclaim.config import settings as config

	logger = logging.getLogger("exsclaim.training")
	stream_handler = logging.StreamHandler()
	stream_handler.setLevel(logging.INFO)
	logger.addHandler(stream_handler)

	log_directory = config.LOGS_PATH / "train"
	log_directory.mkdir(parents=True, exist_ok=True)

	file_handler = logging.FileHandler(log_directory / f"training-{dt.now().isoformat()}.log")
	file_handler.setLevel(logging.DEBUG)
	logger.addHandler(file_handler)

	return logger


async def train_model(figures_input_model: Optional[ModelPath] = None, labels_input_model: Optional[ModelPath] = None,
					  classification_input_model: Optional[ModelPath] = None, figures_save_path: Optional[ModelPath] = None,
					  labels_save_path: Optional[ModelPath] = None, classification_save_path: Optional[ModelPath] = None,
					  detector_name: str = "exsclaim_subfigure_detection", labels_name: str = "exsclaim_label_detection",
					  classifier_name: str = "exsclaim_subfigure_classification",
					  test_size=.1, random_state: int = 42, dataset_dir: str | os.PathLike[str] | None = None,
					  project: str = "exsclaim_finetuning", data_repo: str = "lwashington3/EXSCLAIM-figure-separator",
					  revision: Optional[str] = None, use_mlflow: bool = False, logger: Optional[logging.Logger] = None):
	logger = logger or create_training_logger()

	if use_mlflow:
		settings.update({"mlflow": True})
		logger.info("Added MLFlow tracking.")

	data = load_dataset(data_repo, features=image_features, revision=revision)
	logger.info(f"Loaded dataset from {data_repo}")

	if revision is None:
		from huggingface_hub import scan_cache_dir
		hf_cache_info = scan_cache_dir()

		for repo in hf_cache_info.repos:
			if repo.repo_id != data_repo:
				continue

			latest_revision = sorted(repo.revisions, key=lambda r: r.last_modified, reverse=True)[0]
			revision = latest_revision.commit_hash
			break

	figures_input_model, figures_save_path = await get_model(figures_input_model, figures_save_path, "yolov11_subfigure.pt")
	labels_input_model, labels_save_path = await get_model(labels_input_model, labels_save_path, "yolov11_label.pt")
	classification_input_model, classification_save_path = await get_model(classification_input_model, classification_save_path, "yolov11_classification.pt")

	# Extract all unique subfigure labels
	subfigure_labels = set()
	for i, entry in enumerate(data["train"]):
		info = entry["Info"]["Subfigure Label"]
		if info is None:
			continue
		for row in info:
			subfigure_labels.add(row["text"].strip("()"))

	priority_labels = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]

	class_id_mapping = create_class_id_mapping(subfigure_labels, priority_labels)
	logger.info(f"Class ID Mapping: {class_id_mapping}")

	# Split data into train and val sets
	if len(data.num_columns) == 1:
		import numpy as np

		num_rows = len(data["train"])
		if isinstance(test_size, float):
			test_size = int(test_size * num_rows)
		logger.info(f"Train size: {num_rows - test_size:,}\tTest size: {test_size:,}")
		train, val = torch.utils.data.random_split(data["train"], [num_rows - test_size, test_size],
												   generator=torch.Generator().manual_seed(random_state))

		source = f"https://huggingface.co/datasets/{data_repo}" + (f"/tree/{revision}" if revision is not None else "")
		train_ds = mlflow.data.from_numpy(np.asarray(train), source=source)
		val_ds = mlflow.data.from_numpy(np.asarray(val), source=source)

	else:
		train = data["train"]
		val = data["val"]

		train_ds = mlflow.data.from_huggingface(train, path=data_repo, revision=revision)
		val_ds = mlflow.data.from_huggingface(val, path=data_repo, revision=revision)

	dataset_dir = dataset_dir or TemporaryDirectory()
	dataset_path = Path(dataset_dir).resolve()

	subfigures_path = dataset_path / "subfigures"
	figures_yaml = subfigures_path / "data.yaml"
	subfigure_coords = subfigures_path / "labels"
	subfigure_coords.mkdir(parents=True, exist_ok=True)

	subfig_labels_path = dataset_path / "subfig_labels"
	labels_yaml = subfig_labels_path / "data.yaml"
	label_coords = subfig_labels_path / "labels"
	label_coords.mkdir(parents=True, exist_ok=True)

	images_path = dataset_path / "images"
	classify_path = dataset_path / "classify"

	for split in ("train", "val"):
		(images_path / split).mkdir(parents=True, exist_ok=True)
		(subfigure_coords / split).mkdir(parents=True, exist_ok=True)
		(label_coords / split).mkdir(parents=True, exist_ok=True)
		(classify_path / split).mkdir(parents=True, exist_ok=True)

	# Process the data splits
	process_data_split(train, "train", images_path, subfigure_coords, label_coords, classify_path, class_id_mapping, logger)
	process_data_split(val, "val", images_path, subfigure_coords, label_coords, classify_path, class_id_mapping, logger)

	class_id_mapping_names = repr(list(class_id_mapping.keys()))
	for path, yaml in zip((subfigures_path, subfig_labels_path), (figures_yaml, labels_yaml)):
		path.mkdir(parents=True, exist_ok=True)
		target_path = path / "images"

		shutil.copytree(images_path, target_path, copy_function=os.symlink)

		with open(yaml, 'w') as f:
			f.write(dedent(f"""\
				path: {path}
				train: images/train
				val: images/val
				nc: {len(class_id_mapping)}
				names: {class_id_mapping_names}
			"""))

	# Save class ID mapping to a file
	for path in (subfigures_path, subfig_labels_path):
		with open(path / "class_id_mapping.txt", 'w') as mapping_file:
			for label, class_id in class_id_mapping.items():
				mapping_file.write(f"{label}: {class_id}\n")

	logger.info("Conversion complete!")

	train_kwargs = dict(
		batch=1,
		device="cuda" if torch.cuda.is_available() else "cpu",	# https://docs.ultralytics.com/modes/train/#resuming-interrupted-trainings
		epochs=25,
		imgsz=608,
		project=project,
		seed=random_state,
		# workers=1,
		patience=3
	)

	with mlflow.start_run(run_name="Subfigure Bounding Box Model") as run:
		mlflow.set_tag("model", "bounding_box")
		mlflow.set_tag("yolo_version", "YOLOv11")
		mlflow.log_input(train_ds, context="training")
		mlflow.log_input(val_ds, context="validation")

		model = YOLO(figures_input_model)
		model.train(data=figures_yaml, name=detector_name, **train_kwargs)
		model.save(figures_save_path)

		mlflow.log_artifact(figures_save_path)

	logger.info("Started training the subfigure label bounding box model.")
	with mlflow.start_run(run_name="Subfigure Label Bounding Box Model") as run:
		mlflow.set_tag("model", "label_box")
		mlflow.set_tag("yolo_version", "YOLOv11")
		mlflow.log_input(train_ds, context="training")
		mlflow.log_input(val_ds, context="validation")

		model = YOLO(labels_input_model)
		model.train(data=labels_yaml, name=labels_name, **train_kwargs)
		model.save(labels_save_path)

		mlflow.log_artifact(labels_save_path)

	logger.info("Started training the classifier model.")
	with mlflow.start_run(run_name="Classifier") as run:
		mlflow.set_tag("model", "classifier")
		mlflow.set_tag("yolo_version", "YOLOv11")
		mlflow.log_input(train_ds, context="training")
		mlflow.log_input(val_ds, context="validation")

		classify = YOLO(classification_input_model)
		classify.train(data=str(classify_path), name=classifier_name, **train_kwargs)
		classify.save(classification_save_path)

		mlflow.log_artifact(classification_save_path)

	if isinstance(dataset_dir, TemporaryDirectory):
		dataset_dir.cleanup()
